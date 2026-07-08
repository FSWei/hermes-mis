# Hermes MIS v2 (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**Two-layer memory management engine for Hermes Agent. Active layer + archive layer with auto-archival, cross-layer search, access tracking, and write-failure recovery.**

[中文文档](README.zh-CN.md)

---

## 🎯 What is MIS v2?

MIS is a Hermes MemoryProvider plugin that replaces the default flat memory system with a managed two-layer architecture:

### Layer 1: Active (MEMORY.md)
- Always injected into system prompt (~2,200 chars)
- Short index lines only: `§project：see skill xxx`
- Write validation at code level (format, length, structure, dead references)

### Layer 2: Archive (memory-archive skill)
- Auto-created on first eviction
- Entries with timestamps, searchable via `memory(action='search')`
- Restorable via `memory(action='promote')`
- 50KB soft limit with automatic compression

**Key difference from prompt-based approaches:** All constraints enforced at code level, not prompt level.

---

## ✨ v2 Features

| Feature | Description |
|---------|-------------|
| **Auto-archival** | Overflow entries archived transparently (no error) |
| **Cross-layer search** | `memory(action='search', keyword='...')` searches both layers |
| **Archive promotion** | `memory(action='promote', old_text='...')` restores archived entries |
| **Status dashboard** | `memory(action='status')` shows usage stats |
| **Manual archive** | `memory(action='archive', old_text='...')` manually archive entries |
| **Write-failure recovery** | 4-level fallback chain, data never lost |
| **Access tracking** | Keyword-based, per-session, no LLM calls |
| **Priority eviction** | P0 (core) → P1 (env) → P2 (project) → P3 (temp) |
| **Dead reference detection** | Detects references to non-existent skills |
| **Concurrency safe** | Per-session state for gateway multi-session |
| **Pre-compress save** | Extracts key info before context compression |
| **Fact detection** | Scans conversation for memory-worthy content |

---

## 🚀 Quick Install

```bash
# One command
hermes plugins install FSWei/hermes-mis

# Enable
hermes plugins enable mis
hermes memory provider mis
```

Or manual install:

```bash
# Copy plugin files
mkdir -p ~/.hermes/plugins/memory/mis
cp plugin/__init__.py ~/.hermes/plugins/memory/mis/
cp plugin/plugin.yaml ~/.hermes/plugins/memory/mis/

# Enable
hermes plugins enable mis
hermes memory provider mis
```

---

## 📖 Usage

### Standard Operations (backward compatible)

```python
# Add index line
memory(action='add', target='memory', content='§project：详见 skill my-project')

# Replace entry
memory(action='replace', target='memory', old_text='old content', content='new content')

# Remove entry
memory(action='remove', target='memory', old_text='content to remove')
```

### New v2 Operations

```python
# Search across both layers
memory(action='search', keyword='distillyourself')
# → {"matches": 3, "results": [{"layer": "active", "entry": "..."}, {"layer": "archive", "entry": "..."}]}

# Restore archived entry
memory(action='promote', old_text='distillyourself')
# → {"success": true, "promoted": "§distillyourself.cn：详见 skill distillyourself"}

# View memory status
memory(action='status')
# → {"active": {"entries": 12, "chars": 1008, "limit": 2200, "usage_pct": 45.8}, "archive": {"entries": 14, "size_kb": 1.7}}

# Manually archive an entry
memory(action='archive', old_text='old project')
# → {"success": true, "archived": "§old project：详见 skill xxx"}
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: ACTIVE (MEMORY.md)                        │
│  • Always in system prompt                          │
│  • 2,200 char hard limit                            │
│  • Write validation (code-level)                    │
│  • Priority: P0 (never evict) → P3 (evict first)   │
├─────────────────────────────────────────────────────┤
│  Layer 2: ARCHIVE (memory-archive skill)            │
│  • Created automatically on first eviction          │
│  • Timestamped entries, searchable                  │
│  • 50KB soft limit with compression                 │
│  • Summary injected via system_prompt_block()       │
└─────────────────────────────────────────────────────┘
```

### MemoryProvider Hooks Used

| Hook | Purpose |
|------|---------|
| `system_prompt_block()` | Inject strategy + archive summary + warnings |
| `prefetch(query)` | Access tracking + capacity check + fact hints |
| `sync_turn(user, asst)` | Conversation fact detection |
| `on_pre_compress(msgs)` | Save key info before compression |
| `on_session_end(msgs)` | Force-archive pending writes + maintenance |
| `on_session_switch()` | Migrate pending writes on /new |
| `handle_tool_call()` | Enhanced add + search/promote/status/archive |

---

## 🔒 Policy Enforcement

### Write Validation (code-level, not prompt)

```
< 50 chars   → Always allowed (preferences)
50-150 chars → Allowed if no structure
150-200 chars → Allowed with suggestion (gray zone)
> 200 chars  → Rejected
Structured content (lists, tables, steps) → Rejected
Dead skill references → Rejected
Domain details (IPs, passwords, schemas) → Rejected
```

### Priority Classification (pattern-based, no LLM)

```
P0: 偏好, 讨厌, 隐私极强, 用户期望  → Never evicted
P1: 环境, 认证, 基础设施            → Evict last
P2: §xxx：详见 skill xxx            → Evict when needed
P3: 临时, 告警缓存, 已加入备份       → Evict first
```

### Auto-Eviction

When memory exceeds 95%:
1. Sort entries by priority (P3 first) + access time (oldest first)
2. Evict to archive until 85% utilization
3. Leave reference line in MEMORY.md: `§[归档] topic：详见 memory-archive`

### Write-Failure Recovery (4-level)

```
Level 1: Overflow → auto-archive (transparent)
Level 2: Archive fails → persist failure state + system prompt warning
Level 3: /new → migrate pending writes to archive
Level 4: session end → force-archive (data never lost)
```

---

## 📊 Token Impact

| Component | Condition | Tokens |
|-----------|-----------|--------|
| system_prompt_block (strategy) | Always | ~50 |
| system_prompt_block (archive summary) | When archive exists | 0-50 |
| system_prompt_block (warnings) | When issues exist | 0-40 |
| **Normal operation** | | **~50/turn** |
| **With archive + warnings** | | **~140/turn** |

---

## 🤝 Contributing

```bash
git clone https://github.com/FSWei/hermes-mis.git
cd hermes-mis
# Edit plugin/__init__.py
# Test: hermes -p test-profile chat -q "test memory"
```

## 📄 License

MIT
