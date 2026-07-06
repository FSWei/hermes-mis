"""MIS (Memory-Index-Skill) — MemoryProvider plugin for Hermes.

Program-level enforcement of the MIS memory strategy:
  - Memory stores INDEXES ONLY (§name: see skill xxx)
  - Skills store full project details
  - Writes that violate policy are rejected at code level, not prompt level

Architecture:
  MISMemoryStore subclasses the native MemoryStore from tools.memory_tool.
  All storage logic (persistence, § delimiter, dedup, drift detection, file
  locking, threat scanning) is inherited unchanged. MIS only adds validation
  at add() and replace() entry points.

Installation:
  hermes plugins install FSWei/hermes-mis
  hermes plugins enable mis
  hermes memory provider mis
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defensive import of MemoryStore — if Hermes restructures, fail loud.
# ---------------------------------------------------------------------------

try:
    from tools.memory_tool import MemoryStore, ENTRY_DELIMITER, MEMORY_SCHEMA
except ImportError:
    raise RuntimeError(
        "MIS plugin requires Hermes's MemoryStore (tools.memory_tool). "
        "This version of Hermes may have restructured its memory system. "
        "Update the MIS plugin or switch to the built-in memory provider: "
        "hermes memory provider builtin"
    )

try:
    from hermes_constants import get_hermes_home
except ImportError:
    from pathlib import Path
    import os
    def get_hermes_home() -> Path:
        return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))

# ---------------------------------------------------------------------------
# MIS Policy Engine
# ---------------------------------------------------------------------------

# Index line format: §name：see skill xxx (Chinese or English colon)
_INDEX_LINE_RE = re.compile(
    r'^\s*§\s*.+\S\s*[：:]\s*(?:详见|see)\s+skill\s+\S+',
    re.IGNORECASE,
)

# Project detail signal patterns — if content matches any of these,
# it belongs in a Skill, not in Memory.
_PROJECT_DETAIL_PATTERNS = [
    (re.compile(r'(?:服务器|server)\s*(?:IP)?\s*[：:]?\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', re.I),
     "server IP address"),
    (re.compile(r'(?:技术栈|tech\s*stack)\s*[：:]', re.I),
     "tech stack details"),
    (re.compile(r'(?:架构|architecture)\s*[：:]\s*\S', re.I),
     "architecture details"),
    (re.compile(r'(?:数据库|database|DB)\s*[：:]\s*\S', re.I),
     "database details"),
    (re.compile(r'(?:部署|deploy)\s*[：:]\s*\S', re.I),
     "deployment details"),
    (re.compile(r'(?:API|端点|endpoint)\s*[：:]\s*\S', re.I),
     "API endpoint"),
    (re.compile(r'(?:端口|port)\s*[：:]?\s*\d{2,5}', re.I),
     "port number"),
    (re.compile(r'(?:密码|password|token|secret|api.?key)\s*[：:]\s*\S', re.I),
     "credential/secret"),
    (re.compile(r'(?:表结构|schema|字段|column)\s*[：:]', re.I),
     "database schema"),
    (re.compile(r'(?:路由|route)\s*[：:]\s*/\S', re.I),
     "API route"),
    (re.compile(r'(?:组件|component)\s*[：:]\s*\S{10,}', re.I),
     "component details"),
]

# Content that's clearly personal/environment info — always allowed
_PERSONAL_PATTERNS = [
    re.compile(r'(?:偏好|prefer)', re.I),
    re.compile(r'(?:用户名?|user\s*name)\s*[：:]', re.I),
    re.compile(r'(?:操作系统|OS)\s*[：:]', re.I),
]


def _extract_skill_hint(content: str) -> str:
    """Extract a suggested skill name from blocked content.
    
    Tries to find a project/domain name from common patterns.
    Returns a lowercase hyphenated name, or empty string if nothing found.
    """
    import re as _re
    # Try to find a domain name: xxx.com/xxx.cn/xxx.io
    domain = _re.search(r'(\w+(?:-\w+)*)\.(?:com|cn|io|xyz|org|net)', content)
    if domain:
        return domain.group(1).lower()
    # Try to find a project name after common keywords
    for kw in [r'项目[：:]\s*(\S+)', r'project[：:]\s*(\S+)', r'(?:服务|service)[：:]\s*(\S+)']:
        m = _re.search(kw, content, _re.I)
        if m:
            return m.group(1).lower().replace(' ', '-')
    # Try first line, first word
    first_line = content.split('\n')[0].strip()
    words = first_line.split()
    if words and len(words[0]) > 2:
        return words[0].lower().replace(' ', '-')
    return ''


def _check_mis_policy(content: str) -> Optional[str]:
    """Validate content against MIS policy.
    
    Returns None if content is allowed.
    Returns an error message string if content violates policy.
    """
    content = content.strip()
    if not content:
        return None

    # Index line format → always allowed
    if _INDEX_LINE_RE.match(content):
        return None

    # Check for project detail signals
    violations = []
    for pattern, label in _PROJECT_DETAIL_PATTERNS:
        if pattern.search(content):
            violations.append(label)

    if violations:
        # Extract a suggested skill name from the content
        skill_hint = _extract_skill_hint(content)
        skill_param = f", name='{skill_hint}'" if skill_hint else ""
        
        return (
            f"[MIS Policy] Blocked: content contains project details ({', '.join(violations)}).\n\n"
            f"ACTION REQUIRED — do this now, in this turn:\n"
            f"  Step1: skill_manage(action='create'{skill_param}, content=<the blocked content>)\n"
            f"  Step2: memory(action='add', target='memory', content='§{skill_hint or '项目名'}：详见 skill {skill_hint or 'skill-name'}。')\n\n"
            f"Original content preserved below — pass it to skill_manage:\n"
            f"---\n{content}\n---"
        )

    return None


def scan_memory_violations(entries: List[str]) -> List[Dict[str, str]]:
    """Scan all memory entries and return violations.
    
    Returns a list of dicts with 'entry' and 'reason' keys.
    """
    violations = []
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        # Index lines are fine
        if _INDEX_LINE_RE.match(entry):
            continue
        # Check for project detail signals
        for pattern, label in _PROJECT_DETAIL_PATTERNS:
            if pattern.search(entry):
                violations.append({
                    "entry": entry[:120] + ("..." if len(entry) > 120 else ""),
                    "reason": label,
                })
                break  # one violation per entry is enough
    return violations


# ---------------------------------------------------------------------------
# MIS MemoryStore — inherits ALL native behavior, adds policy validation
# ---------------------------------------------------------------------------

class MISMemoryStore(MemoryStore):
    """MemoryStore subclass with MIS policy enforcement.
    
    All storage operations (persistence, § delimiter, dedup, drift detection,
    file locking, threat scanning, char limits) are inherited from the native
    MemoryStore. MIS only adds write-time validation at add() and replace().
    """

    def add(self, target: str, content: str) -> Dict[str, Any]:
        """Add entry with MIS policy check."""
        if target == "memory":
            violation = _check_mis_policy(content)
            if violation:
                return {"success": False, "error": violation}
        return super().add(target, content)

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        """Replace entry with MIS policy check on new content."""
        if target == "memory":
            violation = _check_mis_policy(new_content)
            if violation:
                return {"success": False, "error": violation}
        return super().replace(target, old_text, new_content)

    def apply_batch(self, target: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch operations with MIS policy check on all add/replace content."""
        if target == "memory":
            for i, op in enumerate(operations):
                op = op or {}
                act = op.get("action")
                content = op.get("content", "")
                if act in {"add", "replace"} and content:
                    violation = _check_mis_policy(content)
                    if violation:
                        return {
                            "success": False,
                            "error": f"Operation {i + 1} ({act}): {violation}",
                        }
        return super().apply_batch(target, operations)


# ---------------------------------------------------------------------------
# Tool schema — identical to native memory tool
# ---------------------------------------------------------------------------

# Re-export the native schema so the tool is wire-compatible.
# We add MIS-specific guidance to the description.
MIS_MEMORY_SCHEMA = {
    "name": "memory",
    "description": (
        "Save durable facts to persistent memory that survive across sessions. Memory is "
        "injected into every future turn, so keep entries compact and high-signal.\n\n"
        "MIS POLICY (enforced at code level):\n"
        "- Memory stores INDEXES ONLY. Format: §项目名：详见 skill xxx\n"
        "- Project details (tech stack, IPs, ports, API endpoints) belong in Skills.\n"
        "- Use skill_manage(action='create') to store project details.\n"
        "- User preferences and environment info are allowed in memory.\n\n"
        "HOW: make ALL your changes in ONE call via an 'operations' array (each item: "
        "{action, content?, old_text?}). The batch applies atomically and the char limit is "
        "checked only on the FINAL result — so a single call can remove/replace stale entries "
        "to free room AND add new ones, even when an add alone would overflow. The response "
        "reports current/limit chars and confirms completion; one batch call finishes the "
        "update, so don't repeat it. Use the bare action/content/old_text fields only for a "
        "single lone change.\n\n"
        "WHEN: save proactively when the user states a preference, correction, or personal "
        "detail, or you learn a stable fact about their environment, conventions, or workflow. "
        "Priority: user preferences & corrections > environment facts > procedures. The best "
        "memory stops the user repeating themselves.\n\n"
        "IF FULL: an add is rejected with the current entries shown. Reissue as ONE batch that "
        "removes or shortens enough stale entries and adds the new one together.\n\n"
        "TARGETS: 'user' = who the user is (name, role, preferences, style). 'memory' = your "
        "notes (environment, conventions, tool quirks, lessons).\n\n"
        "SKIP: trivial/obvious info, easily re-discovered facts, raw data dumps, task progress, "
        "completed-work logs, temporary TODO state (use session_search for those). Reusable "
        "procedures belong in a skill, not memory."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove"],
                "description": "The action to perform (single-op shape). Omit when using 'operations'."
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "Which memory store: 'memory' for personal notes, 'user' for user profile."
            },
            "content": {
                "type": "string",
                "description": "The entry content. Required for 'add' and 'replace' (single-op shape)."
            },
            "old_text": {
                "type": "string",
                "description": "REQUIRED for 'replace' and 'remove' (single-op shape): a short unique substring identifying the existing entry to modify. Omit only for 'add'."
            },
            "operations": {
                "type": "array",
                "description": (
                    "Batch shape: a list of operations applied atomically in one call "
                    "against the final char budget. Preferred when making multiple changes "
                    "or consolidating to make room. Each item is {action, content?, old_text?}."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["add", "replace", "remove"]},
                        "content": {"type": "string", "description": "Entry content for add/replace."},
                        "old_text": {"type": "string", "description": "Substring identifying the entry for replace/remove."},
                    },
                    "required": ["action"],
                },
            },
        },
        "required": ["target"],
    },
}


# ---------------------------------------------------------------------------
# MemoryProvider implementation
# ---------------------------------------------------------------------------

class MISProvider(MemoryProvider):
    """MIS MemoryProvider — program-level memory policy enforcement.
    
    Replaces the built-in memory tool with a version that validates all
    writes against MIS policy before persisting.
    """

    @property
    def name(self) -> str:
        return "mis"

    def is_available(self) -> bool:
        """Always available — no external dependencies."""
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize the MIS memory store from disk."""
        try:
            from hermes_cli.config import load_config
            config = load_config() or {}
            mem_cfg = config.get("memory", {}) or {}
            memory_char_limit = int(mem_cfg.get("memory_char_limit", 2200))
            user_char_limit = int(mem_cfg.get("user_char_limit", 1375))
        except Exception:
            memory_char_limit = 2200
            user_char_limit = 1375

        self._store = MISMemoryStore(
            memory_char_limit=memory_char_limit,
            user_char_limit=user_char_limit,
        )
        self._store.load_from_disk()
        self._session_id = session_id
        self._violations_cache: List[Dict[str, str]] = []
        
        # Scan on init
        self._scan_and_cache_violations()
        
        logger.info(
            "MIS provider initialized (memory=%d/%d chars, user=%d/%d chars, violations=%d)",
            self._store._char_count("memory"), memory_char_limit,
            self._store._char_count("user"), user_char_limit,
            len(self._violations_cache),
        )

    def system_prompt_block(self) -> str:
        """Inject MIS policy awareness into system prompt."""
        return (
            "MEMORY STRATEGY: MIS (Memory-Index-Skill)\n"
            "- Memory stores INDEXES ONLY. Format: §项目名：详见 skill xxx\n"
            "- Skills store full project details (tech stack, architecture, APIs, etc.)\n"
            "- User preferences and environment info are allowed in memory.\n"
            "- Before writing project details to memory, create a Skill first.\n"
            "- This policy is enforced at code level — violating writes are rejected.\n"
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Scan memory for MIS violations each turn.
        
        Returns a warning string if violations are found, empty string otherwise.
        This ensures the LLM sees violations every turn until they're fixed.
        """
        self._scan_and_cache_violations()
        
        if not self._violations_cache:
            return ""

        # Build a compact warning
        lines = [
            f"[MIS Alert] {len(self._violations_cache)} entry/entries in MEMORY.md "
            f"violate MIS policy (should be in Skills, not Memory):"
        ]
        for v in self._violations_cache[:5]:  # show max 5
            lines.append(f"  - [{v['reason']}] {v['entry']}")
        if len(self._violations_cache) > 5:
            lines.append(f"  ... and {len(self._violations_cache) - 5} more")
        lines.append(
            "Action required: migrate these entries to Skills using "
            "skill_manage(action='create') and replace them with index lines "
            "using memory(action='replace')."
        )
        return "\n".join(lines)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return the memory tool schema (identical to native, with MIS guidance)."""
        return [MIS_MEMORY_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Dispatch memory tool calls to MISMemoryStore."""
        action = args.get("action", "")
        target = args.get("target", "memory")
        content = args.get("content")
        old_text = args.get("old_text")
        operations = args.get("operations")

        if target not in {"memory", "user"}:
            return json.dumps(
                {"success": False, "error": f"Invalid target '{target}'. Use 'memory' or 'user'."},
                ensure_ascii=False,
            )

        # Batch path
        if operations:
            if not isinstance(operations, list):
                return json.dumps(
                    {"success": False, "error": "operations must be a list."},
                    ensure_ascii=False,
                )
            result = self._store.apply_batch(target, operations)
            return json.dumps(result, ensure_ascii=False)

        # Single-op path
        if action == "add":
            if not content:
                return json.dumps(
                    {"success": False, "error": "Content is required for 'add' action."},
                    ensure_ascii=False,
                )
            result = self._store.add(target, content)

        elif action == "replace":
            if not old_text:
                return self._missing_old_text_error(target, "replace")
            if not content:
                return json.dumps(
                    {"success": False, "error": "content is required for 'replace' action."},
                    ensure_ascii=False,
                )
            result = self._store.replace(target, old_text, content)

        elif action == "remove":
            if not old_text:
                return self._missing_old_text_error(target, "remove")
            result = self._store.remove(target, old_text)

        else:
            return json.dumps(
                {"success": False, "error": f"Unknown action '{action}'. Use: add, replace, remove"},
                ensure_ascii=False,
            )

        return json.dumps(result, ensure_ascii=False)

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Hook called after native memory writes (for observability)."""
        if target == "memory" and action in {"add", "replace"}:
            violation = _check_mis_policy(content)
            if violation:
                logger.warning(
                    "MIS violation in on_memory_write hook (action=%s): %s",
                    action, violation[:200],
                )

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Rescan violations at session end."""
        self._scan_and_cache_violations()
        if self._violations_cache:
            logger.info(
                "MIS: session ended with %d unresolved violation(s)",
                len(self._violations_cache),
            )

    def shutdown(self) -> None:
        """Clean shutdown."""
        pass

    # -- Internal helpers --

    def _scan_and_cache_violations(self) -> None:
        """Scan current memory entries for violations and cache results."""
        try:
            entries = self._store._entries_for("memory")
            self._violations_cache = scan_memory_violations(entries)
        except Exception as e:
            logger.debug("MIS violation scan failed: %s", e)
            self._violations_cache = []

    def _missing_old_text_error(self, target: str, action: str) -> str:
        """Error for replace/remove without old_text."""
        entries = self._store._entries_for(target)
        current = self._store._char_count(target)
        limit = self._store._char_limit(target)
        return json.dumps(
            {
                "success": False,
                "error": (
                    f"'{action}' needs old_text — a short unique substring of the entry "
                    f"to {action}. None was provided. Reissue the {action} with old_text "
                    f"set to part of one of the current_entries below."
                ),
                "current_entries": entries,
                "usage": f"{current:,}/{limit:,}",
            },
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Plugin registration — Hermes discovers this via MemoryProvider subclass
# ---------------------------------------------------------------------------
