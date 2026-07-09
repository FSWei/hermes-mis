"""MIS (Memory-Index-Skill) — Memory Engine v2 for Hermes.

Program-level memory management:
  - MEMORY.md: active layer (short indexes, always in context)
  - memory-archive skill: archive layer (auto-archived entries)
  - Write validation, auto-archival, cross-layer search, access tracking
  - Per-session state for gateway concurrency safety
  - All hard constraints at code level, not prompt level

Architecture:
  MISMemoryStore subclasses the native MemoryStore from tools.memory_tool.
  MISProvider implements the MemoryProvider ABC with all available hooks.
  Tool schema extends the native memory tool with search/promote/status/archive.

Installation:
  hermes plugins install FSWei/hermes-mis
  hermes plugins enable mis
  hermes memory provider mis
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defensive import of MemoryStore
# ---------------------------------------------------------------------------

try:
    from tools.memory_tool import MemoryStore, ENTRY_DELIMITER, MEMORY_SCHEMA
except ImportError:
    raise RuntimeError(
        "MIS plugin requires Hermes's MemoryStore (tools.memory_tool). "
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
# MIS Policy Engine (unchanged core, enhanced edge cases)
# ---------------------------------------------------------------------------

_INDEX_LINE_RE = re.compile(
    r'^\s*§\s*.+\S\s*[：:]?\s*(?:详见|see)\s+(?:skill|gbrain\s+page)\s+\S+',
    re.IGNORECASE,
)

_DEFAULT_MAX_MEMORY_ENTRY_LENGTH = 150

_PERSONAL_PATTERNS = [
    re.compile(r'(?:偏好|prefer)', re.I),
    re.compile(r'(?:用户名?|user\s*name)\s*[：:]', re.I),
    re.compile(r'(?:操作系统|OS)\s*[：:]', re.I),
]

_REFERENCE_CONTENT_PATTERNS = [
    (re.compile(r'(?:^|\n)\s*[-•·]\s+', re.M), "bullet list"),
    (re.compile(r'(?:^|\n)\s*\d+[.)、]\s+', re.M), "numbered list"),
    (re.compile(r'→|=>|：.*→'), "arrow/chain notation"),
    (re.compile(r'(?:步骤|step)\s*\d', re.I), "step-by-step"),
    (re.compile(r'(?:首先|然后|接着|最后|其次)'), "sequential flow"),
    (re.compile(r'(?:第[一二三四五六七八九十]+步)'), "numbered steps"),
    (re.compile(r'\|.*\|.*\|'), "table structure"),
    (re.compile(r'(?:详见|参考|see)\s+(?!skill\s|gbrain\s+page)'), "references non-skill"),
]

_DOMAIN_DETAIL_PATTERNS = [
    (re.compile(r'(?:服务器|server)\s*(?:IP)?\s*[：:]?\s*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', re.I), "server IP"),
    (re.compile(r'(?:技术栈|tech\s*stack)\s*[：:]', re.I), "tech stack"),
    (re.compile(r'(?:架构|architecture)\s*[：:]\\s*\\S', re.I), "architecture"),
    (re.compile(r'(?:数据库|database|DB)\s*[：:]\\s*\\S', re.I), "database"),
    (re.compile(r'(?:部署|deploy)\s*[：:]\\s*\\S', re.I), "deployment"),
    (re.compile(r'(?:API|端点|endpoint)\s*[：:]\\s*\\S', re.I), "API endpoint"),
    (re.compile(r'(?:端口|port)\s*[：:]?\s*\d{2,5}', re.I), "port number"),
    (re.compile(r'(?:密码|password|token|secret|api.?key)\s*[：:]\\s*\\S', re.I), "credential"),
    (re.compile(r'(?:表结构|schema|字段|column)\s*[：:]', re.I), "database schema"),
    (re.compile(r'(?:路由|route)\s*[：:]\\s*/\\S', re.I), "API route"),
    (re.compile(r'(?:组件|component)\s*[：:]\\s*\\S{10,}', re.I), "component details"),
    (re.compile(r'(?:脚本|口播|文案|剧本|解说词)[^：:\n]*[：:]', re.I), "content creation"),
    (re.compile(r'(?:封面|排版|设计风格|配色|色调)[^：:\n]*[：:]', re.I), "design spec"),
    (re.compile(r'(?:视频|剪辑|字幕|配音|特效)[^：:\n]*[：:]', re.I), "video production"),
    (re.compile(r'(?:推广|营销|获客|转化|漏斗)[^：:\n]*[：:]', re.I), "marketing"),
    (re.compile(r'(?:简历|resume|工作经历|教育背景)[^：:\n]*[：:]', re.I), "resume"),
]

_PROJECT_DETAIL_PATTERNS = _DOMAIN_DETAIL_PATTERNS


def _get_max_entry_length() -> int:
    try:
        from hermes_cli.config import load_config
        config = load_config() or {}
        mem_cfg = config.get("memory", {}) or {}
        return int(mem_cfg.get("max_entry_length", _DEFAULT_MAX_MEMORY_ENTRY_LENGTH))
    except Exception:
        return _DEFAULT_MAX_MEMORY_ENTRY_LENGTH


def _check_reference_structure(content: str) -> Optional[str]:
    for pattern, label in _REFERENCE_CONTENT_PATTERNS:
        if pattern.search(content):
            return label
    return None


def _check_mis_policy(content: str, store=None) -> Optional[str]:
    """Validate content against MIS policy. Enhanced v2 with gray zone."""
    content = content.strip()
    if not content:
        return None

    # Index line format → always allowed (check dead refs separately)
    if _INDEX_LINE_RE.match(content):
        dead = _find_dead_references(content)
        if dead:
            return (
                f"[MIS] References non-existent skill(s): {', '.join(dead)}.\n"
                f"Create the skill first, or remove the reference."
            )
        return None

    # Short entries (<50 chars) → always allowed
    is_short = len(content) < 50
    if is_short:
        return None

    # Check for reference structure
    struct_label = _check_reference_structure(content)
    if struct_label:
        if len(content) <= 50 and 'list' not in struct_label:
            pass
        else:
            return (
                f"[MIS] Structured content ({struct_label}) belongs in a Skill.\n"
                f"Shorten to one line, or: skill_manage(action='create', ...)\n"
                f"Preview: {content[:80]}{'...' if len(content) > 80 else ''}"
            )

    # Multi-point heuristic
    segments = re.split(r'[、，,；;]\s*', content)
    detail_segments = [s for s in segments if len(s) > 2]
    if len(detail_segments) >= 3 and len(content) > 100:
        return (
            f"[MIS] {len(detail_segments)} detail points in {len(content)} chars.\n"
            f"Shorten to one line, or create a Skill."
        )

    # Domain-specific detail signals
    violations = []
    for pattern, label in _PROJECT_DETAIL_PATTERNS:
        if pattern.search(content):
            violations.append(label)
    if violations and len(content) > 100:
        return (
            f"[MIS] Contains project details ({', '.join(violations[:3])}).\n"
            f"Store in a Skill, not Memory."
        )

    # Length check — v2: gray zone 150-200 is allowed with suggestion
    max_len = _get_max_entry_length()
    if len(content) > 200:
        return (
            f"[MIS] Too long ({len(content)} chars > 200).\n"
            f"Options: shorten to ≤150, create a Skill, or it will auto-archive."
        )
    if len(content) > max_len:
        struct = _check_reference_structure(content)
        if struct:
            return (
                f"[MIS] Long ({len(content)} chars) + structured ({struct}).\n"
                f"Create a Skill instead."
            )
        # Gray zone 150-200: allowed, no rejection

    return None


def _find_dead_references(content: str) -> List[str]:
    """Check if referenced skills exist."""
    try:
        skills_dir = get_hermes_home() / "skills"
        dead = []
        for match in re.finditer(r'(?:详见|see)\s+skill\s+[`]?([\w-]+)', content, re.I):
            skill_name = match.group(1)
            if not (skills_dir / skill_name).exists():
                dead.append(skill_name)
        return dead
    except Exception:
        return []


def scan_memory_violations(entries: List[str]) -> List[Dict[str, str]]:
    violations = []
    max_len = _get_max_entry_length()
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        if _INDEX_LINE_RE.match(entry):
            continue
        found = False
        for pattern, label in _PROJECT_DETAIL_PATTERNS:
            if pattern.search(entry):
                violations.append({"entry": entry[:120], "reason": label})
                found = True
                break
        if found:
            continue
        if len(entry) > 200:
            violations.append({"entry": entry[:120], "reason": f"too long ({len(entry)} chars)"})
            continue
        struct_label = _check_reference_structure(entry)
        if struct_label:
            violations.append({"entry": entry[:120], "reason": struct_label})
    return violations


# ---------------------------------------------------------------------------
# Priority Classification (NEW)
# ---------------------------------------------------------------------------

_P0_KEYWORDS = {"偏好", "讨厌", "隐私极强", "用户期望", "称呼不要", "绝不"}
_P3_KEYWORDS = {"告警缓存", "已加入备份", "临时", "Cron jobs"}

_ARCHIVE_DIR_NAME = "memory-archive"


def _classify_priority(entry: str) -> str:
    """Pattern-based priority classification. Pure code, no LLM."""
    entry = entry.strip()
    if any(kw in entry for kw in _P0_KEYWORDS):
        return "P0"
    if any(kw in entry for kw in _P3_KEYWORDS):
        return "P3"
    if _INDEX_LINE_RE.match(entry):
        return "P2"
    return "P1"


def _priority_rank(entry: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}[_classify_priority(entry)]


def _extract_keywords(entry: str) -> List[str]:
    """Extract meaningful keywords from a memory entry for access tracking."""
    # Remove § prefix and common format words
    cleaned = re.sub(r'^§\s*', '', entry)
    cleaned = re.sub(r'(?:详见|see|skill|gbrain|page|references?/)', '', cleaned, flags=re.I)
    cleaned = re.sub(r'[：:、，,`"\'\(\)]', ' ', cleaned)
    # Split and filter
    words = [w.strip() for w in cleaned.split() if len(w.strip()) > 2]
    return words[:10]  # limit to avoid noise


# ---------------------------------------------------------------------------
# Per-Session State Management (NEW — concurrency safe)
# ---------------------------------------------------------------------------

class _SessionState:
    """Per-session mutable state for gateway concurrency safety."""
    __slots__ = (
        "pending_write_failure", "access_log", "potential_memory",
        "current_turn", "eviction_warning_sent", "session_id",
    )

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self.pending_write_failure: Optional[Dict] = None
        self.access_log: Dict[str, Dict] = {}  # entry → {last_seen, count}
        self.potential_memory: Optional[Dict] = None
        self.current_turn: int = 0
        self.eviction_warning_sent: bool = False


# ---------------------------------------------------------------------------
# Archive Management (NEW)
# ---------------------------------------------------------------------------

class _ArchiveManager:
    """Manages the memory-archive skill (Layer 2)."""

    def __init__(self):
        self._archive_dir: Optional[Path] = None
        self._archive_file: Optional[Path] = None

    @property
    def archive_dir(self) -> Path:
        if self._archive_dir is None:
            self._archive_dir = get_hermes_home() / "skills" / _ARCHIVE_DIR_NAME
        return self._archive_dir

    @property
    def archive_file(self) -> Path:
        if self._archive_file is None:
            self._archive_file = self.archive_dir / "references" / "archived-entries.md"
        return self._archive_file

    def exists(self) -> bool:
        return self.archive_dir.exists() and self.archive_file.exists()

    def ensure_structure(self):
        """Create archive skill structure if it doesn't exist."""
        if self.exists():
            return
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        (self.archive_dir / "references").mkdir(exist_ok=True)

        skill_md = (
            "---\n"
            "name: memory-archive\n"
            "description: >\n"
            "  Deprecated memory entries auto-archived by MIS.\n"
            "  Use memory(action='search', keyword='...') to find entries.\n"
            "  Use memory(action='promote', old_text='...') to restore.\n"
            "tags: [memory, archive, mis]\n"
            "---\n\n"
            "# Memory Archive\n\n"
            "> Auto-managed by MIS plugin. Do not edit directly.\n\n"
            "## Operations\n\n"
            "- `memory(action='search', keyword='xxx')` — search both layers\n"
            "- `memory(action='promote', old_text='xxx')` — restore to MEMORY.md\n"
            "- `memory(action='status')` — view memory stats\n"
            "- `memory(action='archive', old_text='xxx')` — manually archive\n\n"
            "## Content\n\n"
            "See `references/archived-entries.md`\n"
        )
        (self.archive_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        self.archive_file.write_text(
            "# Archived Memory Entries\n\n", encoding="utf-8"
        )

    def append_entry(self, entry: str) -> bool:
        """Append an entry to the archive file with timestamp."""
        try:
            self.ensure_structure()
            existing = self.archive_file.read_text(encoding="utf-8") if self.archive_file.exists() else ""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_entry = f"\n[{timestamp}] {entry}\n"
            self.archive_file.write_text(existing + new_entry, encoding="utf-8")

            # Check size limit (500KB)
            self._check_size()
            return True
        except Exception as e:
            logger.error("MIS: archive append failed: %s", e)
            return False

    def read_entries(self) -> List[str]:
        """Read all entries from the archive file."""
        try:
            if not self.archive_file.exists():
                return []
            content = self.archive_file.read_text(encoding="utf-8")
            entries = []
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith(">"):
                    entries.append(line)
            return entries
        except Exception:
            return []

    def remove_entry(self, entry: str) -> bool:
        """Remove a specific entry from the archive."""
        try:
            if not self.archive_file.exists():
                return False
            content = self.archive_file.read_text(encoding="utf-8")
            # Find and remove the line containing the entry
            lines = content.split("\n")
            new_lines = []
            removed = False
            for line in lines:
                if not removed and entry.strip() in line and line.strip().startswith("["):
                    removed = True
                    continue
                new_lines.append(line)
            if removed:
                self.archive_file.write_text("\n".join(new_lines), encoding="utf-8")
            return removed
        except Exception:
            return False

    def count_entries(self) -> int:
        """Count entries in archive."""
        return len(self.read_entries())

    def get_topics(self, max_topics: int = 8) -> str:
        """Get compact topic list for display."""
        entries = self.read_entries()
        topics = []
        for entry in entries:
            # Extract topic from entry (after timestamp)
            topic = re.sub(r'^\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\]\s*', '', entry)
            topic = re.sub(r'^§\s*', '', topic)
            topic = re.sub(r'[：:].*$', '', topic).strip()[:20]
            if topic and topic not in topics:
                topics.append(topic)
            if len(topics) >= max_topics:
                break
        result = "、".join(topics)
        if len(entries) > max_topics:
            result += f" 等{len(entries)}项"
        return result

    def get_file_size(self) -> int:
        """Get archive file size in bytes."""
        if self.archive_file.exists():
            return self.archive_file.stat().st_size
        return 0

    def _check_size(self):
        """Compress old entries if archive exceeds 500KB."""
        if not self.archive_file.exists():
            return
        size = self.archive_file.stat().st_size
        if size <= 500 * 1024:
            return
        try:
            content = self.archive_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            # Keep header + entries from last 30 days
            cutoff = datetime.now().strftime("%Y-%m-%d")
            header_lines = []
            recent_lines = []
            old_count = 0
            in_header = True
            for line in lines:
                if in_header and (line.startswith("[") and re.match(r'\[\d{4}-', line)):
                    in_header = False
                if in_header:
                    header_lines.append(line)
                    continue
                # Check if entry is recent (within 30 days)
                date_match = re.match(r'\[(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    entry_date = date_match.group(1)
                    days_old = (datetime.now() - datetime.strptime(entry_date, "%Y-%m-%d")).days
                    if days_old <= 30:
                        recent_lines.append(line)
                    else:
                        old_count += 1
                else:
                    recent_lines.append(line)

            if old_count > 0:
                summary = f"\n[{cutoff}] [{old_count} older entries compressed]\n"
                new_content = "\n".join(header_lines) + summary + "\n".join(recent_lines)
                self.archive_file.write_text(new_content, encoding="utf-8")
                logger.info("MIS: compressed %d old archive entries", old_count)
        except Exception as e:
            logger.error("MIS: archive compression failed: %s", e)


# ---------------------------------------------------------------------------
# User Archive Manager (Layer 2 for user profile)
# ---------------------------------------------------------------------------

class _UserArchiveManager:
    """Manages the user-archive skill (Layer 2 for user profile entries)."""

    def __init__(self):
        self._archive_dir: Optional[Path] = None
        self._archive_file: Optional[Path] = None

    @property
    def archive_dir(self) -> Path:
        if self._archive_dir is None:
            self._archive_dir = get_hermes_home() / "skills" / "user-archive"
        return self._archive_dir

    @property
    def archive_file(self) -> Path:
        if self._archive_file is None:
            self._archive_file = self.archive_dir / "references" / "user-entries.md"
        return self._archive_file

    def exists(self) -> bool:
        return self.archive_dir.exists() and self.archive_file.exists()

    def ensure_structure(self):
        if self.exists():
            return
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        (self.archive_dir / "references").mkdir(exist_ok=True)
        skill_md = (
            "---\n"
            "name: user-archive\n"
            "description: >\n"
            "  Deprecated user profile entries auto-archived by MIS.\n"
            "  Weekly cron classifies entries into fsw-identity skill.\n"
            "  Entries older than 30 days auto-sink to deep-archive.\n"
            "tags: [memory, archive, mis, user]\n"
            "---\n\n"
            "# User Archive\n\n"
            "> Auto-managed by MIS plugin. Do not edit directly.\n\n"
            "## Content\n\n"
            "See `references/user-entries.md`\n"
        )
        (self.archive_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        self.archive_file.write_text(
            "# Archived User Profile Entries\n\n", encoding="utf-8"
        )

    def append_entry(self, entry: str) -> bool:
        try:
            self.ensure_structure()
            existing = self.archive_file.read_text(encoding="utf-8") if self.archive_file.exists() else ""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_entry = f"\n[{timestamp}] {entry}\n"
            self.archive_file.write_text(existing + new_entry, encoding="utf-8")
            return True
        except Exception as e:
            logger.error("MIS: user-archive append failed: %s", e)
            return False

    def read_entries(self) -> List[str]:
        try:
            if not self.archive_file.exists():
                return []
            content = self.archive_file.read_text(encoding="utf-8")
            entries = []
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith(">"):
                    entries.append(line)
            return entries
        except Exception:
            return []

    def remove_entry(self, entry: str) -> bool:
        try:
            if not self.archive_file.exists():
                return False
            content = self.archive_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            new_lines = []
            removed = False
            for line in lines:
                if not removed and entry.strip() in line and line.strip().startswith("["):
                    removed = True
                    continue
                new_lines.append(line)
            if removed:
                self.archive_file.write_text("\n".join(new_lines), encoding="utf-8")
            return removed
        except Exception:
            return False

    def count_entries(self) -> int:
        return len(self.read_entries())

    def _check_size(self):
        """Compress old entries if user-archive exceeds 500KB."""
        if not self.archive_file.exists():
            return
        size = self.archive_file.stat().st_size
        if size <= 500 * 1024:
            return
        try:
            content = self.archive_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            cutoff = datetime.now().strftime("%Y-%m-%d")
            header_lines = []
            recent_lines = []
            old_count = 0
            in_header = True
            for line in lines:
                if in_header and (line.startswith("[") and re.match(r'\[\d{4}-', line)):
                    in_header = False
                if in_header:
                    header_lines.append(line)
                    continue
                date_match = re.match(r'\[(\d{4}-\d{2}-\d{2})', line)
                if date_match:
                    entry_date = date_match.group(1)
                    days_old = (datetime.now() - datetime.strptime(entry_date, "%Y-%m-%d")).days
                    if days_old <= 30:
                        recent_lines.append(line)
                    else:
                        old_count += 1
                else:
                    recent_lines.append(line)
            if old_count > 0:
                summary = f"\n[{cutoff}] [{old_count} older entries compressed]\n"
                new_content = "\n".join(header_lines) + summary + "\n".join(recent_lines)
                self.archive_file.write_text(new_content, encoding="utf-8")
                logger.info("MIS: compressed %d old user-archive entries", old_count)
        except Exception as e:
            logger.error("MIS: user-archive compression failed: %s", e)


# ---------------------------------------------------------------------------

class _DeepArchiveManager:
    """Manages the deep-archive skill (Layer 3 — permanent storage).
    
    Entries that LLM has classified go to their target skill.
    Entries that don't match any skill sink here after 30 days.
    This file is write-once, never modified, never re-distilled.
    """

    def __init__(self):
        self._archive_dir: Optional[Path] = None
        self._archive_file: Optional[Path] = None

    @property
    def archive_dir(self) -> Path:
        if self._archive_dir is None:
            self._archive_dir = get_hermes_home() / "skills" / "deep-archive"
        return self._archive_dir

    @property
    def archive_file(self) -> Path:
        if self._archive_file is None:
            self._archive_file = self.archive_dir / "references" / "archived-entries.md"
        return self._archive_file

    def exists(self) -> bool:
        return self.archive_dir.exists() and self.archive_file.exists()

    def ensure_structure(self):
        if self.exists():
            return
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        (self.archive_dir / "references").mkdir(exist_ok=True)
        skill_md = (
            "---\n"
            "name: deep-archive\n"
            "description: >\n"
            "  Permanent archive for memory/user entries.\n"
            "  Write-once storage. Never re-processed, never re-distilled.\n"
            "tags: [memory, archive, mis, permanent]\n"
            "---\n\n"
            "# Deep Archive (Permanent)\n\n"
            "> Auto-managed by MIS plugin. Write-once, never modified.\n\n"
            "## Content\n\n"
            "See `references/archived-entries.md`\n"
        )
        (self.archive_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        self.archive_file.write_text(
            "# Deep Archive — Permanent Storage\n\n", encoding="utf-8"
        )

    def append_entry(self, entry: str, source: str = "memory") -> bool:
        """Append entry permanently. source: 'memory' or 'user'."""
        try:
            self.ensure_structure()
            existing = self.archive_file.read_text(encoding="utf-8") if self.archive_file.exists() else ""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_entry = f"\n[{timestamp}] [{source}] {entry}\n"
            self.archive_file.write_text(existing + new_entry, encoding="utf-8")
            return True
        except Exception as e:
            logger.error("MIS: deep-archive append failed: %s", e)
            return False

    def read_entries(self) -> List[str]:
        try:
            if not self.archive_file.exists():
                return []
            content = self.archive_file.read_text(encoding="utf-8")
            entries = []
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith(">"):
                    entries.append(line)
            return entries
        except Exception:
            return []

    def count_entries(self) -> int:
        return len(self.read_entries())


# ---------------------------------------------------------------------------
# MIS MemoryStore (enhanced)
# ---------------------------------------------------------------------------

class MISMemoryStore(MemoryStore):
    """MemoryStore subclass with MIS policy enforcement."""

    def add(self, target: str, content: str) -> Dict[str, Any]:
        if target in ("memory", "user"):
            violation = _check_mis_policy(content, self)
            if violation:
                return {"success": False, "error": violation}
        return super().add(target, content)

    def replace(self, target: str, old_text: str, new_content: str) -> Dict[str, Any]:
        if target in ("memory", "user"):
            violation = _check_mis_policy(new_content, self)
            if violation:
                return {"success": False, "error": violation}
        return super().replace(target, old_text, new_content)

    def apply_batch(self, target: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        if target in ("memory", "user"):
            for i, op in enumerate(operations):
                op = op or {}
                act = op.get("action")
                content = op.get("content", "")
                if act in {"add", "replace"} and content:
                    violation = _check_mis_policy(content, self)
                    if violation:
                        return {
                            "success": False,
                            "error": f"Operation {i + 1} ({act}): {violation}",
                        }
        return super().apply_batch(target, operations)


# ---------------------------------------------------------------------------
# Enhanced Tool Schema
# ---------------------------------------------------------------------------

MIS_MEMORY_SCHEMA = {
    "name": "mis",
    "description": (
        "MIS (Memory-Index-Skill) management tool.\n\n"
        "ACTIONS:\n"
        "- check: validate content before writing to memory/user\n"
        "- search: keyword search across active + archive layers\n"
        "- promote: restore an archived entry to MEMORY.md\n"
        "- status: show memory usage and archive stats\n"
        "- archive: manually archive an active entry\n\n"
        "WORKFLOW for writing:\n"
        "1. Call mis(action='check', content='...', target='memory')\n"
        "2. If pass → memory(action='add', content='...')\n"
        "3. If fail → shorten to ≤150 chars or create a Skill"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check", "search", "promote", "status", "archive"],
                "description": "check: validate. search: cross-layer search. promote: restore from archive. status: stats. archive: manual archive.",
            },
            "content": {
                "type": "string",
                "description": "Content to validate (for 'check' action).",
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "'memory' for notes, 'user' for user profile.",
            },
            "keyword": {
                "type": "string",
                "description": "Search keyword (for 'search' action).",
            },
            "old_text": {
                "type": "string",
                "description": "Substring to match (for 'promote' and 'archive' actions).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# MIS MemoryProvider — v2 Engine
# ---------------------------------------------------------------------------

class MISProvider(MemoryProvider):
    """MIS MemoryProvider v2 — full memory lifecycle management.

    Extends the built-in memory system with:
    - Write validation (format, length, structure, dead references)
    - Auto-archival on overflow (transparent to agent)
    - Cross-layer search (active + archive)
    - Archive promotion (restore archived entries)
    - Per-session state (gateway concurrency safe)
    - Access tracking (for stale detection)
    - Session lifecycle hooks (maintenance, migration)
    """

    def __init__(self):
        self._store: Optional[MISMemoryStore] = None
        self._session_id: str = ""
        self._session_states: Dict[str, _SessionState] = {}
        self._state_lock = threading.Lock()
        self._archive = _ArchiveManager()
        self._user_archive = _UserArchiveManager()
        self._deep_archive = _DeepArchiveManager()
        self._violations_cache: List[Dict[str, str]] = []

    # -- State management ---------------------------------------------------

    def _get_state(self, session_id: str = "") -> _SessionState:
        sid = session_id or self._session_id or "_default"
        with self._state_lock:
            if sid not in self._session_states:
                self._session_states[sid] = _SessionState(sid)
            return self._session_states[sid]

    def _cleanup_session(self, session_id: str):
        with self._state_lock:
            self._session_states.pop(session_id, None)

    # -- Core lifecycle -----------------------------------------------------

    @property
    def name(self) -> str:
        return "mis"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
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

        # Scan existing violations
        self._scan_and_cache_violations()

        logger.info(
            "MIS v2 initialized (memory=%d/%d chars, archive=%d entries, violations=%d)",
            self._store._char_count("memory"), memory_char_limit,
            self._archive.count_entries(),
            len(self._violations_cache),
        )

    def shutdown(self) -> None:
        pass

    # -- System prompt injection --------------------------------------------

    def system_prompt_block(self) -> str:
        state = self._get_state()
        max_len = _get_max_entry_length()
        parts = []

        # 1. Strategy (compact, ~50 tokens)
        parts.append(
            f"MEMORY STRATEGY: MIS (Memory-Index-Skill)\n"
            f"- Memory/User stores SHORT indexes only (max {max_len} chars)\n"
            f"- Format: §name：see skill xxx\n"
            f"- Overflow → auto-archived (not lost)\n"
            f"- ⚠️ BEFORE writing: call mis(action='check', content=..., target=...) to validate\n"
            f"- Tools: mis (check/search/promote/status/archive), memory (write)"
        )

        # 2. Pending write failure warning
        pending = state.pending_write_failure
        if pending:
            turns_ago = state.current_turn - pending.get("turn", 0)
            pending_target = pending.get("target", "memory")
            parts.append(
                f"\n⚠️ [MIS] Unsaved {pending_target} write from {turns_ago} turns ago:\n"
                f"  \"{pending['content'][:80]}\"\n"
                f"  It will be auto-archived at session end."
            )

        # 3. Archive summary (memory + user + deep)
        archive_count = self._archive.count_entries()
        user_archive_count = self._user_archive.count_entries()
        deep_count = self._deep_archive.count_entries()
        archive_parts = []
        if archive_count > 0:
            topics = self._archive.get_topics(max_topics=4)
            archive_parts.append(f"memory: {archive_count} ({topics})")
        if user_archive_count > 0:
            archive_parts.append(f"user: {user_archive_count}")
        if deep_count > 0:
            archive_parts.append(f"deep: {deep_count}")
        if archive_parts:
            parts.append(
                f"\n📦 [Archive] {'; '.join(archive_parts)}\n"
                f"  memory(action='search', keyword='...') to find"
            )

        # 4. Capacity warnings
        if self._store:
            mem_ratio = self._store._char_count("memory") / self._store._char_limit("memory")
            user_ratio = self._store._char_count("user") / self._store._char_limit("user")
            if mem_ratio > 0.85:
                parts.append(f"\n⚡ [MIS] Memory at {mem_ratio:.0%}")
            if user_ratio > 0.85:
                parts.append(f"\n⚡ [MIS] User at {user_ratio:.0%}")

        return "\n".join(parts)

    # -- Prefetch (before each API call) ------------------------------------

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        state = self._get_state(session_id)
        state.current_turn += 1

        # 1. Access tracking
        self._track_access(query, state)

        # 2. Capacity check + auto-evict
        self._check_capacity(state)

        # 3. Potential memory hint
        parts = []
        pot = state.potential_memory
        if pot and pot.get("turn") == state.current_turn - 1:
            parts.append(f"💡 [MIS] Worth remembering: \"{pot['content'][:80]}\"")
            state.potential_memory = None

        # 4. Violation scan
        violations = self._scan_and_cache_violations()
        if violations:
            for v in violations[:3]:
                parts.append(f"[MIS Alert] {v['entry']}... → {v['reason']}")

        return "\n".join(parts)

    # -- Per-turn hooks -----------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        pass  # turn counting is done in prefetch

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        """Scan conversation for memory-worthy content (no LLM, pattern-based)."""
        session_id = kwargs.get("session_id", "")
        state = self._get_state(session_id)

        _MEMORY_WORTHY_PATTERNS = [
            re.compile(r'(?:我|用户)(?:喜欢|讨厌|偏好|习惯|不(?:喜欢|要))', re.I),
            re.compile(r'(?:记住|记一下|帮我记|备忘)', re.I),
            re.compile(r'(?:密码|token|key|端口|IP)\s*[：:]\s*\S+', re.I),
            re.compile(r'(?:以后|以后都|每次|总是|不要)(?:用|做|走|按)', re.I),
        ]
        for pattern in _MEMORY_WORTHY_PATTERNS:
            if pattern.search(user_content):
                state.potential_memory = {
                    "content": user_content[:200],
                    "turn": state.current_turn,
                }
                break

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Extract key info before context compression."""
        keywords = ["记住", "记一下", "帮我记", "§", "preference", "remember", "prefer"]
        extracted = []
        for msg in messages[-20:]:
            content = msg.get("content", "")
            if isinstance(content, str) and any(kw in content for kw in keywords):
                extracted.append(content[:150])

        if extracted:
            return (
                "[MIS Pre-Compress] Unsaved memory-worthy content:\n"
                + "\n".join(f"  - {e[:100]}" for e in extracted[-5:])
            )
        return ""

    # -- Memory write hook --------------------------------------------------

    def on_memory_write(self, action: str, target: str, content: str,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        if target in ("memory", "user") and action in {"add", "replace"}:
            violation = _check_mis_policy(content, self._store)
            if violation:
                logger.warning("MIS violation in on_memory_write (%s/%s): %s", target, action, violation[:200])

    # -- Session lifecycle hooks --------------------------------------------

    def on_session_switch(self, new_session_id: str, *, reset: bool = False,
                          parent_session_id: str = "", **kwargs) -> None:
        """Handle /new, /reset, /resume — migrate pending writes, clean state."""
        # Migrate pending writes from old session
        old_id = parent_session_id or self._session_id
        if old_id:
            old_state = self._get_state(old_id)
            pending = old_state.pending_write_failure
            if pending and pending.get("content"):
                pending_target = pending.get("target", "memory")
                archive_mgr = self._user_archive if pending_target == "user" else self._archive
                archived = archive_mgr.append_entry(pending["content"])
                if archived:
                    self._leave_archive_reference(pending["content"], pending_target)
                    logger.info("MIS: migrated pending %s write to archive on session switch", pending_target)
                old_state.pending_write_failure = None

            # Cleanup old session state
            if reset:
                self._cleanup_session(old_id)

        self._session_id = new_session_id

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Force-archive pending writes + maintenance scan."""
        state = self._get_state()

        # 1. Force-archive pending writes
        pending = state.pending_write_failure
        if pending and pending.get("content"):
            pending_target = pending.get("target", "memory")
            archive_mgr = self._user_archive if pending_target == "user" else self._archive
            archived = archive_mgr.append_entry(pending["content"])
            if archived:
                self._leave_archive_reference(pending["content"], pending_target)
                logger.info("MIS: force-archived pending %s write at session end", pending_target)
            state.pending_write_failure = None

        # 2. Maintenance scan (log only, no auto-action)
        stale = self._find_stale_entries(days=14)
        dead = self._find_dead_references_all()
        if stale or dead:
            logger.info("MIS: session end — %d stale, %d dead refs", len(stale), len(dead))

        # 3. Cleanup session state
        self._cleanup_session(self._session_id)

    def on_delegation(self, task: str, result: str, *,
                      child_session_id: str = "", **kwargs) -> None:
        pass  # Track delegation memory if needed in future

    # -- Tool schemas -------------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [MIS_MEMORY_SCHEMA]

    # -- Tool call dispatch -------------------------------------------------

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        # mis tool: multi-action (check/search/promote/status/archive)
        if tool_name == "mis":
            action = args.get("action", "")
            session_id = kwargs.get("session_id", "")
            state = self._get_state(session_id)
            if action == "check":
                return self._handle_mis_check(args)
            elif action == "search":
                return self._handle_search(args)
            elif action == "promote":
                return self._handle_promote(args, state)
            elif action == "status":
                return self._handle_status(state)
            elif action == "archive":
                return self._handle_archive(args)
            return json.dumps({"success": False, "error": f"Unknown mis action: {action}"})

        # Legacy: if somehow called with old tool name, handle memory actions
        action = args.get("action", "")
        session_id = kwargs.get("session_id", "")
        state = self._get_state(session_id)

        # New operations
        if action == "search":
            return self._handle_search(args)
        elif action == "promote":
            return self._handle_promote(args, state)
        elif action == "status":
            return self._handle_status(state)
        elif action == "archive":
            return self._handle_archive(args)

        # Enhanced existing operations
        if action == "add":
            return self._handle_add_enhanced(args, state)
        elif action == "replace":
            return self._handle_replace(args)
        elif action == "remove":
            return self._handle_remove(args)
        elif action == "":
            # No action — check if operations batch
            operations = args.get("operations")
            if operations:
                target = args.get("target", "memory")
                result = self._store.apply_batch(target, operations)
                return json.dumps(result, ensure_ascii=False)
            return json.dumps({"success": False, "error": "action required"})

        return json.dumps({"success": False, "error": f"Unknown action: {action}"})

    # -- Tool handlers ------------------------------------------------------

    def _handle_mis_check(self, args: Dict) -> str:
        """Validate content against MIS policy. No write, pure check."""
        content = args.get("content", "").strip()
        target = args.get("target", "memory")
        if not content:
            return json.dumps({"success": False, "error": "content required"}, ensure_ascii=False)

        violation = _check_mis_policy(content, self._store)
        if violation:
            return json.dumps({
                "success": False,
                "blocked": True,
                "reason": violation,
                "hint": "Shorten to ≤150 chars, or create a Skill with skill_manage(action='create').",
            }, ensure_ascii=False)

        return json.dumps({
            "success": True,
            "blocked": False,
            "chars": len(content),
            "message": f"PASS ({len(content)} chars). Safe to write with memory(action='add').",
        }, ensure_ascii=False)

    def _handle_add_enhanced(self, args: Dict, state: _SessionState) -> str:
        """Enhanced add: overflow auto-archived instead of error."""
        content = args.get("content", "").strip()
        target = args.get("target", "memory")
        operations = args.get("operations")

        # Batch path
        if operations:
            if not isinstance(operations, list):
                return json.dumps({"success": False, "error": "operations must be a list"})
            result = self._store.apply_batch(target, operations)
            return json.dumps(result, ensure_ascii=False)

        if not content:
            return json.dumps({"success": False, "error": "content required for add"})

        # Policy check (both memory and user)
        violation = _check_mis_policy(content, self._store)
        if violation:
            return json.dumps({"success": False, "error": violation}, ensure_ascii=False)

        # Try write
        result = self._store.add(target, content)

        # Success
        if result.get("success"):
            state.pending_write_failure = None
            return json.dumps(result, ensure_ascii=False)

        # Capacity overflow → auto-archive (memory or user)
        if "limit" in str(result.get("error", "")):
            archive_mgr = self._user_archive if target == "user" else self._archive
            archived = archive_mgr.append_entry(content)
            if archived:
                self._leave_archive_reference(content, target)
                state.pending_write_failure = None
                layer_name = "user-archive" if target == "user" else "memory-archive"
                return json.dumps({
                    "success": True,
                    "archived": True,
                    "message": f"[MIS] Entry auto-archived ({target} full). "
                               f"Use memory(action='search') to find it.",
                }, ensure_ascii=False)

            # Archive also failed → persist failure state
            state.pending_write_failure = {
                "content": content[:300],
                "error": "archive_failed",
                "turn": state.current_turn,
                "target": target,
            }
            return json.dumps({
                "success": False,
                "error": f"Both {target} and archive write failed. "
                         "Data preserved in conversation history. "
                         "Will be auto-archived at session end.",
            }, ensure_ascii=False)

        return json.dumps(result, ensure_ascii=False)

    def _handle_replace(self, args: Dict) -> str:
        old_text = args.get("old_text", "")
        content = args.get("content", "")
        target = args.get("target", "memory")

        if not old_text:
            return self._missing_old_text_error(target, "replace")
        if not content:
            return json.dumps({"success": False, "error": "content required for replace"})

        result = self._store.replace(target, old_text, content)
        return json.dumps(result, ensure_ascii=False)

    def _handle_remove(self, args: Dict) -> str:
        old_text = args.get("old_text", "")
        target = args.get("target", "memory")

        if not old_text:
            return self._missing_old_text_error(target, "remove")

        result = self._store.remove(target, old_text)
        return json.dumps(result, ensure_ascii=False)

    def _handle_search(self, args: Dict) -> str:
        """Cross-layer search: MEMORY.md + USER.md + memory-archive + user-archive."""
        keyword = args.get("keyword", "").strip()
        if not keyword:
            return json.dumps({"success": False, "error": "keyword required"})

        results = []
        keyword_lower = keyword.lower()

        # Search active memory
        for entry in self._store._entries_for("memory"):
            if keyword_lower in entry.lower():
                results.append({"layer": "active", "target": "memory", "entry": entry})

        # Search active user
        for entry in self._store._entries_for("user"):
            if keyword_lower in entry.lower():
                results.append({"layer": "active", "target": "user", "entry": entry})

        # Search memory-archive
        for entry in self._archive.read_entries():
            if keyword_lower in entry.lower():
                results.append({"layer": "archive", "target": "memory", "entry": entry})

        # Search user-archive
        for entry in self._user_archive.read_entries():
            if keyword_lower in entry.lower():
                results.append({"layer": "archive", "target": "user", "entry": entry})

        return json.dumps({
            "success": True,
            "keyword": keyword,
            "matches": len(results),
            "results": results[:20],
        }, ensure_ascii=False)

    def _handle_promote(self, args: Dict, state: _SessionState) -> str:
        """Restore archived entry to MEMORY.md. Anti-loop: evict first, then write."""
        old_text = args.get("old_text", "").strip()
        if not old_text:
            return json.dumps({"success": False, "error": "old_text required"})

        # Search archive
        archive_entries = self._archive.read_entries()
        matched = [e for e in archive_entries if old_text.lower() in e.lower()]
        if not matched:
            return json.dumps({"success": False, "error": f"No match in archive for: {old_text}"})

        entry = matched[0]
        # Strip timestamp prefix
        clean = re.sub(r'^\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\]\s*', '', entry).strip()

        # Check if already exists
        for existing in self._store._entries_for("memory"):
            if clean.lower() in existing.lower() or existing.lower() in clean.lower():
                return json.dumps({"success": False, "error": "Already exists in MEMORY.md"})

        # Evict first if needed (anti-loop: use _force_evict, not _handle_add)
        current = self._store._char_count("memory")
        limit = self._store._char_limit("memory")
        if current + len(clean) > limit * 0.93:
            evicted = self._force_evict_for_space(len(clean))
            if not evicted:
                return json.dumps({
                    "success": False,
                    "error": "Cannot make room (all entries are P0)"
                })

        # Direct write (bypass add enhancement to avoid re-archive loop)
        result = self._store.add("memory", clean)
        if result.get("success"):
            self._archive.remove_entry(entry)
            return json.dumps({
                "success": True,
                "promoted": clean[:80],
            }, ensure_ascii=False)

        return json.dumps(result, ensure_ascii=False)

    def _handle_status(self, state: _SessionState) -> str:
        active_mem = self._store._entries_for("memory")
        active_mem_chars = self._store._char_count("memory")
        active_mem_limit = self._store._char_limit("memory")
        active_user = self._store._entries_for("user")
        active_user_chars = self._store._char_count("user")
        active_user_limit = self._store._char_limit("user")
        archive_count = self._archive.count_entries()
        archive_size = self._archive.get_file_size()
        user_archive_count = self._user_archive.count_entries()
        deep_count = self._deep_archive.count_entries()

        return json.dumps({
            "success": True,
            "memory": {
                "entries": len(active_mem),
                "chars": active_mem_chars,
                "limit": active_mem_limit,
                "usage_pct": round(active_mem_chars / active_mem_limit * 100, 1) if active_mem_limit else 0,
            },
            "user": {
                "entries": len(active_user),
                "chars": active_user_chars,
                "limit": active_user_limit,
                "usage_pct": round(active_user_chars / active_user_limit * 100, 1) if active_user_limit else 0,
            },
            "archive": {
                "memory_entries": archive_count,
                "user_entries": user_archive_count,
                "size_kb": round(archive_size / 1024, 1),
            },
            "deep_archive": {
                "entries": deep_count,
            },
            "pending_write_failure": state.pending_write_failure is not None,
        }, ensure_ascii=False)

    def _handle_archive(self, args: Dict) -> str:
        """Manually archive an active entry."""
        old_text = args.get("old_text", "").strip()
        target = args.get("target", "memory")
        if not old_text:
            return json.dumps({"success": False, "error": "old_text required"})

        entries = self._store._entries_for(target)
        matched = [e for e in entries if old_text.lower() in e.lower()]
        if not matched:
            return json.dumps({"success": False, "error": f"No match for: {old_text}"})

        entry = matched[0]
        if _classify_priority(entry) == "P0":
            return json.dumps({
                "success": False,
                "error": "P0 entries (core preferences) cannot be archived"
            })

        archive_mgr = self._user_archive if target == "user" else self._archive
        self._store.remove(target, entry)
        archive_mgr.append_entry(entry)
        self._leave_archive_reference(entry, target)
        return json.dumps({"success": True, "archived": entry[:80]}, ensure_ascii=False)

    # -- Internal helpers ---------------------------------------------------

    def _track_access(self, query: str, state: _SessionState):
        """Keyword-based access tracking."""
        query_lower = query.lower()
        for entry in self._store._entries_for("memory"):
            keywords = _extract_keywords(entry)
            if any(kw.lower() in query_lower for kw in keywords if len(kw) > 2):
                state.access_log[entry] = {
                    "last_seen": datetime.now().isoformat(),
                    "count": state.access_log.get(entry, {}).get("count", 0) + 1,
                }

    def _check_capacity(self, state: _SessionState):
        """Auto-evict when memory or user exceeds 95%."""
        for target in ("memory", "user"):
            ratio = self._store._char_count(target) / self._store._char_limit(target)
            if ratio > 0.95:
                self._auto_evict(state, target=target, target_ratio=0.85)

    def _auto_evict(self, state: _SessionState, target: str = "memory", target_ratio: float = 0.85):
        """Evict low-priority entries to archive."""
        entries = self._store._entries_for(target)
        ranked = sorted(entries, key=lambda e: (
            _priority_rank(e),
            self._get_last_accessed_rank(e, state),
        ))

        target_chars = int(self._store._char_limit(target) * target_ratio)
        archive_mgr = self._user_archive if target == "user" else self._archive
        for entry in ranked:
            if _classify_priority(entry) == "P0":
                break
            if self._store._char_count(target) <= target_chars:
                break
            self._store.remove(target, entry)
            archive_mgr.append_entry(entry)
            logger.info("MIS: auto-evicted %s entry (%d chars)", target, len(entry))

    def _force_evict_for_space(self, needed_chars: int) -> bool:
        """Precisely evict entries to make room (for promote)."""
        entries = self._store._entries_for("memory")
        ranked = sorted(entries, key=lambda e: _priority_rank(e))

        freed = 0
        for entry in ranked:
            if _classify_priority(entry) == "P0":
                return False
            if freed >= needed_chars:
                return True
            freed += len(entry)
            self._store.remove("memory", entry)
            self._archive.append_entry(entry)

        return freed >= needed_chars

    def _get_last_accessed_rank(self, entry: str, state: _SessionState) -> int:
        """Return negative timestamp for sorting (most recent first)."""
        log = state.access_log.get(entry)
        if log:
            return -int(log.get("count", 0))
        return 0

    def _leave_archive_reference(self, entry: str, target: str = "memory"):
        """Leave a reference line in active layer after archiving."""
        topic = re.sub(r'^§\s*', '', entry)
        topic = re.sub(r'[：:].*$', '', topic).strip()[:25]
        ref_line = f"§[归档] {topic}：详见 {'user' if target == 'user' else ''}memory-archive"
        current = self._store._char_count(target)
        limit = self._store._char_limit(target)
        if current + len(ref_line) < limit * 0.93:
            self._store.add(target, ref_line)

    def _find_stale_entries(self, days: int = 14) -> List[str]:
        """Find entries not accessed in N days (session-local tracking)."""
        state = self._get_state()
        stale = []
        now = datetime.now()
        for entry in self._store._entries_for("memory"):
            if _classify_priority(entry) == "P0":
                continue
            log = state.access_log.get(entry)
            if not log:
                # Not accessed this session — check if entry is old
                continue
            try:
                last = datetime.fromisoformat(log["last_seen"])
                if (now - last).days >= days:
                    stale.append(entry[:60])
            except (ValueError, KeyError):
                pass
        return stale

    def _find_dead_references_all(self) -> List[str]:
        """Scan all entries for dead skill references."""
        dead = []
        for entry in self._store._entries_for("memory"):
            refs = _find_dead_references(entry)
            if refs:
                dead.extend(refs)
        return dead

    def _scan_and_cache_violations(self) -> List[Dict[str, str]]:
        try:
            entries = self._store._entries_for("memory")
            self._violations_cache = scan_memory_violations(entries)
        except Exception as e:
            logger.debug("MIS violation scan failed: %s", e)
            self._violations_cache = []
        return self._violations_cache

    def _missing_old_text_error(self, target: str, action: str) -> str:
        entries = self._store._entries_for(target)
        current = self._store._char_count(target)
        limit = self._store._char_limit(target)
        return json.dumps({
            "success": False,
            "error": (
                f"'{action}' needs old_text — a short unique substring of the entry "
                f"to {action}. None was provided."
            ),
            "current_entries": entries,
            "usage": f"{current:,}/{limit:,}",
        }, ensure_ascii=False)

    # -- Migration (one-time) -----------------------------------------------

    def migrate_v1(self) -> Dict[str, Any]:
        """One-time migration: clean MEMORY.md + establish archive. With rollback."""
        backup_path = self._backup_memory()

        try:
            entries = self._store._entries_for("memory")
            active = []
            archived = []
            deleted = []

            for entry in entries:
                priority = _classify_priority(entry)
                dead = _find_dead_references(entry)

                if priority == "P3":
                    deleted.append(entry)
                elif dead and priority != "P0":
                    archived.append(entry)
                elif priority == "P2":
                    archived.append(entry)
                else:
                    active.append(entry)

            # Deduplicate
            seen = set()
            deduped = []
            for entry in active:
                key = re.sub(r'\s+', ' ', entry.strip().lower())
                if key not in seen:
                    seen.add(key)
                    deduped.append(entry)
            active = deduped

            # Write new MEMORY.md
            self._store._set_entries("memory", active)

            # Archive
            for entry in archived:
                self._archive.append_entry(entry)

            return {
                "success": True,
                "active": len(active),
                "archived": len(archived),
                "deleted": len(deleted),
                "backup": str(backup_path),
                "total_chars": self._store._char_count("memory"),
            }
        except Exception as e:
            # Rollback
            self._restore_from_backup(backup_path)
            logger.error("MIS: migration failed, rolled back: %s", e)
            return {"success": False, "error": str(e), "rolled_back": True}

    def _backup_memory(self) -> Path:
        src = self._store._path_for("memory")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = src.parent / f"MEMORY.md.bak.{ts}"
        if src.exists():
            shutil.copy2(src, bak)
        return bak

    def _restore_from_backup(self, backup_path: Path):
        if backup_path.exists():
            target = self._store._path_for("memory")
            shutil.copy2(backup_path, target)
            self._store.load_from_disk()


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------
