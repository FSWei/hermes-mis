# Hermes MIS (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**Program-level memory policy enforcement for Hermes Agent. Memory stores indexes only, Skills store details. Zero-install, zero-dependency.**

[中文文档](README.zh-CN.md)

---

## 🎯 What is MIS?

Hermes's default Memory has only ~2200 bytes, which fills up quickly with detailed project information.

MIS (Memory-Index-Skill) splits Memory into three layers:
- **Memory (Index Layer)**: Only stores index lines, ~50 bytes each
- **Skill (Storage Layer)**: Stores complete project content, each can be tens of thousands of bytes
- **SOUL (Rule Layer)**: Injects MIS rules, automatically applied every turn

**The difference from prompt-based approaches:** MIS enforces its policy at the **code level**. When the LLM tries to write project details to Memory, the write is **rejected** with a clear error message. This is not a suggestion — it's a program-level gate.

**Result: 10 projects = 10 index lines ≈ 500 bytes, effective capacity 100+ KB, ~100x expansion.**

---

## 🚀 Quick Start

### One-Command Install

```bash
hermes plugins install FSWei/hermes-mis
```

### Activate

```bash
hermes plugins enable mis
```

Then set MIS as your memory provider. Edit `~/.hermes/config.yaml` (or `~/.hermes/profiles/<profile>/config.yaml`):

```yaml
memory:
  provider: mis
```

Or use the interactive setup:
```bash
hermes memory setup
```

### Verify

```bash
hermes memory status
# Should show: Provider: mis
```

**That's it.** No pip install, no npm install, no external services, no API keys.

---

## 📖 Before & After Example

### Before MIS

```
Memory (2200 bytes, 100% full):
────────────────────────────────────────────────────────────────────
my-webapp — React+Node.js+PostgreSQL e-commerce platform. 
Server 10.0.1.100. JWT authentication: implemented. Payment 
integration: Stripe API. Database migrations: see skill my-webapp 
Pitfall #12. Redis caching for product listings...

my-api — FastAPI+Python REST API service. Server 10.0.1.101. 
Endpoints: /users, /products, /orders. Rate limiting: 100 req/min. 
API docs at /docs endpoint...

[ONLY 3-5 PROJECTS FIT!]
```

### After MIS

```
Memory (500 bytes, 23% used):
────────────────────────────────────────────────────────────────────
§my-webapp：详见 skill my-webapp。
§my-api：详见 skill my-api。
§my-blog：详见 skill my-blog。
§my-bot：详见 skill my-bot。
§my-tools：详见 skill my-tools。
§user-config：详见 skill user-config。
§platform-a：详见 skill platform-a。
§project-x：详见 skill project-x。

[10+ PROJECTS FIT! 100+ KB EFFECTIVE CAPACITY]
```

---

## 🔧 How It Works

### Architecture

```
Native MemoryStore (tools/memory_tool.py)
    └── MISMemoryStore (inherits ALL storage logic)
            └── MISProvider (MemoryProvider plugin)
                    ├── add() → MIS policy check → super().add()
                    ├── replace() → MIS policy check → super().replace()
                    ├── apply_batch() → MIS policy check → super().apply_batch()
                    └── prefetch() → scan all entries for violations each turn
```

**Zero reimplementation.** All storage operations (persistence, § delimiter, dedup, drift detection, file locking, threat scanning, char limits) are inherited from the native `MemoryStore`. MIS only adds validation at write entry points.

### Policy Enforcement

| Content Type | Target | Result |
|---|---|---|
| `§name：详见 skill xxx` | memory | ✅ Allowed |
| Server IPs, ports, tech stack | memory | ❌ **Rejected** |
| API endpoints, credentials | memory | ❌ **Rejected** |
| User preferences, env info | memory | ✅ Allowed |
| Anything | user | ✅ Allowed |

When a write is rejected, the LLM receives:
```
[MIS Policy] Content contains project details (server IP address, port number).
Memory only accepts index lines. Store project details in a Skill instead.

Correct format:
  memory(action='add', target='memory', content='§项目名：详见 skill skill-name。')

To create a Skill:
  skill_manage(action='create', name='skill-name', content='...')
```

### Per-Turn Scanning

Even if existing memory entries have violations (from before MIS was installed), the plugin scans all entries each turn via `prefetch()` and injects a warning:

```
[MIS Alert] 2 entry/entries in MEMORY.md violate MIS policy:
  - [server IP address] 服务器 59.110.226.32，/opt/distill/...
  - [tech stack] 技术栈：Vue 3 + Express + SQLite...
Action required: migrate these entries to Skills...
```

---

## 📦 What's Included

```
hermes-mis/
├── plugin/               # Hermes MemoryProvider plugin
│   ├── plugin.yaml       # Plugin metadata
│   └── __init__.py       # MISProvider + MISMemoryStore + policy engine
├── SKILL.md              # Hermes Skill (migration guide + reference)
├── README.md             # This file
├── README.zh-CN.md       # 中文文档
├── LICENSE
└── .gitignore
```

---

## 🔄 Migration Guide

After installing, existing memory entries may need migration:

1. **Read your memory file:**
   ```
   read_file(path='~/.hermes/memories/MEMORY.md')
   # Or for profiles: ~/.hermes/profiles/<profile>/memories/MEMORY.md
   ```

2. **For each project detail entry, create a Skill and replace:**
   ```
   # Create Skill with full details
   skill_manage(action='create', name='my-project', content='full project info here...')
   
   # Replace Memory entry with index line
   memory(action='replace', target='memory',
          old_text='old project detail text',
          content='§my-project：详见 skill my-project。')
   ```

3. **Verify:** `prefetch()` returns empty when all violations are resolved.

---

## ⚙️ Configuration

```yaml
# config.yaml
memory:
  provider: mis                    # Activate MIS
  memory_char_limit: 2200         # Memory store char limit (default: 2200)
  user_char_limit: 1375           # User profile char limit (default: 1375)
```

---

## 🆚 Comparison

| Feature | Prompt-Only MIS | **MIS Plugin** |
|---|---|---|
| Policy enforcement | LLM "should follow" rules | **Code-level rejection** |
| Reliability | ~70% (LLM may ignore) | **~100% (programmatic)** |
| Per-turn scanning | Manual (SOUL.md rule) | **Automatic (prefetch)** |
| Installation | Edit SOUL.md manually | **`hermes plugins install`** |
| Updates | Manual SKILL.md edits | **`hermes plugins update`** |
| Dependencies | None | None |
| Storage implementation | N/A (uses native) | **Inherits native MemoryStore** |

---

## ❓ FAQ

**Q: Will this break my existing memory?**
A: No. MIS only adds validation for NEW writes. Existing entries are preserved. The `prefetch()` scan will flag old violations as warnings until you migrate them.

**Q: Can I use MIS with MCP memory tools (engram, gbrain, etc.)?**
A: Yes. MIS replaces the built-in memory tool. MCP tools are separate and work alongside it.

**Q: What if Hermes updates break the plugin?**
A: The plugin imports `MemoryStore` from Hermes's internal API. If Hermes restructures, the plugin will fail with a clear error message. Update the plugin or switch back to built-in: `hermes memory setup`.

**Q: Does this affect the `user` target?**
A: No. MIS policy only validates `target='memory'`. The `target='user'` store is unrestricted.

---

## 📄 License

MIT

---

## 🔗 Links

- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent Docs](https://hermes-agent.nousresearch.com/docs)
