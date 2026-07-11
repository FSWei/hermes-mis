# Hermes MIS v4 (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**Two-layer memory management engine for Hermes Agent with real-time write interception, violation resolution, and auto-skill routing.**

[中文文档](README.zh-CN.md)

---

## 🎯 What is MIS?

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

## ✨ v4 Features (NEW)

### 🔴 Real-Time Write Interception
**v3 Problem:** `memory` tool bypassed MIS entirely — wrote directly to native MemoryStore, MIS only saw violations in post-write audit logs.

**v4 Fix:** Monkey-patches `tool_executor.handle_function_call` to swap `agent._memory_store` with `MISMemoryStore` on every memory write. ALL memory writes now go through MIS policy checks.

```python
# In MISProvider.initialize():
# Patches tool_executor so memory tool uses MISMemoryStore
# No changes to Hermes core code — all in the plugin
```

### 🔴 Structured Violation Resolution
**v3 Problem:** Violations returned a string error. Agent had to figure out what to do.

**v4 Fix:** Violations return structured suggestions with actionable choices:

```json
{
    "success": false,
    "error": "Too long (318 chars > 200)",
    "reason": "too_long",
    "suggestions": [
        {"action": "match_skill", "skill": "esp32-s3-touch-lcd-7", "hint": "追加到已有 Skill: esp32-s3-touch-lcd-7"},
        {"action": "create_skill", "skill": "esp32-project", "hint": "创建新 Skill: esp32-project"},
        {"action": "shorten", "hint": "缩短到150字符以内"},
        {"action": "force", "hint": "忽略限制直接写入（不推荐）"}
    ],
    "pending_id": 0
}
```

### 🟡 Pending Violations in System Prompt
Blocked writes are tracked as pending violations and shown prominently in the system prompt:

```
⚠️ [MIS] 1 条记忆写入被拦截：
  [0] "§ESP32-S3项目：dir=D:\PROJ\danzi..." (Too long, 318 chars > 200)
      → 追加到已有 Skill: esp32-s3-touch-lcd-7
      → 缩短到150字符以内
  处理：mis(action='resolve', pending_id=0, choice='match_skill'|'create_skill'|'shorten'|'force')
```

### 🟡 Auto-Skill Matching
When a violation is detected, MIS automatically:
1. Searches existing skills by keyword overlap
2. Suggests matching skills to append to
3. Suggests new skill names based on content topic
4. On resolution: creates short index in MEMORY.md + moves details to skill's `references/memory-overflow.md`

### Resolve Actions

| Choice | What happens |
|--------|-------------|
| `match_skill` | Creates `§topic：详见skill xxx` in MEMORY.md, appends full content to skill's references |
| `create_skill` | Creates new skill with SKILL.md + references, adds short index |
| `shorten` | Agent provides shortened version, MIS validates and writes |
| `force` | Bypasses policy, writes directly (not recommended) |

```python
# Resolve with skill match
mis(action='resolve', pending_id=0, choice='match_skill', skill='esp32-s3-touch-lcd-7')

# Resolve by creating new skill
mis(action='resolve', pending_id=0, choice='create_skill', skill='my-new-skill')

# Resolve by shortening
mis(action='resolve', pending_id=0, choice='shorten', content='§ESP32项目：详见skill esp32')

# Force write
mis(action='resolve', pending_id=0, choice='force')

# List all pending violations
mis(action='resolve')
```

---

## v3 Features (still available)

| Feature | Description |
|---------|-------------|
| **Auto-archival** | Overflow entries archived transparently (no error) |
| **Cross-layer search** | `mis(action='search', keyword='...')` searches both layers |
| **Archive promotion** | Restore archived entries |
| **Status dashboard** | `mis(action='status')` shows usage stats |
| **Write-failure recovery** | 4-level fallback chain, data never lost |
| **Access tracking** | Keyword-based, per-session, no LLM calls |
| **Priority eviction** | P0 (core) → P3 (temp) |
| **Dead reference detection** | Detects references to non-existent skills |
| **Concurrency safe** | Per-session state for gateway multi-session |
| **Pre-compress save** | Extracts key info before context compression |
| **Fact detection** | Scans conversation for memory-worthy content |
| **3-layer archive** | Active → Archive → Deep Archive |
| **User profile interception** | Validates both memory and user target writes |

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
cp __init__.py ~/.hermes/plugins/memory/mis/
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

### Search & Archive

```python
# Search across both layers
mis(action='search', keyword='distillyourself')

# View memory status
mis(action='status')

# Manually archive an entry
mis(action='archive', old_text='old project')
```

### Violation Resolution (v4)

```python
# List pending violations
mis(action='resolve')

# Resolve with specific choice
mis(action='resolve', pending_id=0, choice='match_skill', skill='target-skill')
mis(action='resolve', pending_id=0, choice='create_skill', skill='new-skill-name')
mis(action='resolve', pending_id=0, choice='shorten', content='shortened version')
mis(action='resolve', pending_id=0, choice='force')
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Agent calls memory(action='add', content='...')        │
│                          ↓                              │
│  tool_executor.handle_function_call()                   │
│    [MIS monkey-patch: swap agent._memory_store]         │
│                          ↓                              │
│  MISMemoryStore.add()                                   │
│    → _check_mis_policy_v2(content)                      │
│       ├─ PASS → super().add() → native MemoryStore      │
│       └─ BLOCKED → store as pending_violation           │
│                      → return suggestions               │
│                      → show in system prompt             │
│                          ↓                              │
│  Agent sees violation → user chooses resolution         │
│    → mis(action='resolve', choice='match_skill')        │
│       ├─ match_skill → §index + append to skill refs    │
│       ├─ create_skill → new SKILL.md + §index           │
│       ├─ shorten → validate shortened content           │
│       └─ force → bypass policy, write directly          │
└─────────────────────────────────────────────────────────┘
```

### MemoryProvider Hooks Used

| Hook | Purpose |
|------|---------|
| `system_prompt_block()` | Inject strategy + pending violations + archive summary |
| `prefetch(query)` | Access tracking + capacity check + pending violation alerts |
| `sync_turn(user, asst)` | Conversation fact detection |
| `on_pre_compress(msgs)` | Save key info before compression |
| `on_session_end(msgs)` | Force-archive pending writes + maintenance |
| `on_session_switch()` | Migrate pending writes on /new |
| `on_memory_write()` | Post-write audit (v4: uses v2 policy check) |
| `handle_tool_call()` | mis tool: check/search/status/archive/resolve |

---

## 🔒 Policy Enforcement

### Write Validation (code-level, not prompt)

```
< 50 chars   → Always allowed (preferences)
50-150 chars → Allowed if no structure
150-200 chars → Allowed with suggestion (gray zone)
> 200 chars  → Blocked → pending violation with suggestions
Structured content (lists, tables, steps) → Blocked
Dead skill references → Blocked
Domain details (IPs, passwords, schemas) → Blocked
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
| system_prompt_block (pending violations) | When blocked writes exist | 0-100 |
| system_prompt_block (archive summary) | When archive exists | 0-50 |
| system_prompt_block (warnings) | When issues exist | 0-40 |
| **Normal operation** | | **~50/turn** |
| **With violations + archive** | | **~240/turn** |

---

## ⚠️ Important Notes

### Monkey-Patch Approach
MIS v4 uses a monkey-patch on `tool_executor.handle_function_call` to intercept memory writes. This is necessary because:
1. `agent._memory_store` is initialized as native `MemoryStore` in Hermes core
2. We cannot modify Hermes core code (to avoid merge conflicts on updates)
3. The patch is applied once during plugin initialization and is idempotent (`_mis_patched` flag)

### Compatibility
- **Hermes versions:** Tested with Hermes Agent (latest)
- **Backward compatible:** All v3 features still work
- **No core changes:** All modifications in the plugin file only

---

## 🤝 Contributing

```bash
git clone https://github.com/FSWei/hermes-mis.git
cd hermes-mis
# Edit __init__.py
# Test: hermes -p test-profile chat -q "test memory"
```

## 📄 License

MIT
