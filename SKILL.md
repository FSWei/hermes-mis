---
name: hermes-mis
description: "Hermes MIS v3 — Three-layer memory engine with code-level enforcement. Active → Archive → Deep Archive. mis_check tool for pre-write validation."
triggers:
  - 记忆扩展
  - memory扩展
  - memory index skill
  - MIS
  - hermes-mis
  - memory优化
  - memory policy
  - mis_check
---

# Hermes MIS v3 (Memory-Index-Skill)

**Three-layer memory management engine for Hermes Agent with code-level enforcement.**

## Architecture

```
Layer 1: Active (MEMORY.md / USER.md)
  → mis_check validates before every write
  → Overflow auto-archived (transparent)
         ↓
Layer 2: Archive (memory-archive / user-archive)
  → Weekly LLM classification cron
         ↓
Layer 3: Deep Archive (permanent, write-once, never re-processed)
```

## Installation

```bash
hermes plugins install FSWei/hermes-mis
hermes plugins enable mis
hermes memory provider mis
```

Config (`~/.hermes/config.yaml`):
```yaml
memory:
  provider: mis
  memory_char_limit: 2200
  user_char_limit: 1375
```

Verify: `hermes memory status` → should show `Provider: mis ← active`

## mis_check Tool

MIS registers a `mis_check` tool (not `memory` — avoids core tool name conflict).

**Workflow:**
1. Call `mis_check(content="...", target="memory")` to validate
2. If PASS → proceed with `memory(action='add', ...)`
3. If FAIL → shorten to ≤150 chars or create a Skill

This is enforced via `system_prompt_block` which injects the instruction every turn.

## Policy Rules

| Content | Action |
|---------|--------|
| `§name：see skill xxx` (index line) | ✅ Always allowed |
| Short entries (<50 chars) | ✅ Always allowed |
| Structured content (lists, steps, tables) | ❌ Blocked |
| Project details (IP, ports, tech stack, API) | ❌ Blocked |
| Over 200 chars | ❌ Blocked |
| 150-200 chars (no structure) | ⚠️ Allowed (gray zone) |

Both `target="memory"` and `target="user"` are validated.

## Cron Script

Install the weekly classification script:

```bash
cp scripts/archive-classify.py ~/.hermes/profiles/<profile>/scripts/
```

Create a weekly cron job (via agent or CLI):
- Schedule: `0 3 * * 1` (Monday 03:00)
- Script: `scripts/archive-classify.py`
- The script outputs archive entries + skill index as JSON
- The agent classifies entries into skills or deep-archive
- Entries older than 30 days auto-sink to deep-archive

## Tools

| Tool | Description |
|------|-------------|
| `mis_check(content, target)` | Validate content before writing |
| `memory(action='add')` | Write (native tool, MIS hooks scan for violations) |
| `memory(action='search', keyword)` | Cross-layer search (4 layers) |

## Key Constants

- Memory limit: 2,200 chars
- User limit: 1,375 chars
- Max entry length: 150 chars
- Archive auto-sink: 30 days
- Archive size limit: 500KB

## Pitfalls

### 1. Core Tool Name Conflict
Hermes gateway rejects memory providers that register tools with core names (`memory`, `terminal`, etc). MIS uses `mis_check` instead. The `allow_tool_override` config only affects CLI, not runtime.

### 2. One Provider at a Time
`memory.provider: mis` replaces the native memory store entirely.

### 3. Plugin Directory
Profile-scoped: `~/.hermes/profiles/<profile>/plugins/mis/`

### 4. Archive Dedup
`append_entry()` has no dedup. If migration runs twice, entries duplicate. Fix manually or add dedup logic.

## Uninstall

```bash
hermes plugins remove mis
# Edit config.yaml: remove memory.provider or set to builtin
```

## Links

- GitHub: https://github.com/FSWei/hermes-mis
- Issues: https://github.com/FSWei/hermes-mis/issues
