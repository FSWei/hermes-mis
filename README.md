# Hermes MIS (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**One-command memory optimization for Hermes Agent — 100x capacity expansion via pure configuration. No source code changes.**

[中文文档](README.zh-CN.md)

---

## 🎯 What is MIS?

Hermes's default Memory has only ~2200 bytes, which fills up quickly with detailed project information.

MIS (Memory-Index-Skill) splits Memory into three layers:
- **Memory (Index Layer)**: Only stores index lines, ~50 bytes each
- **Skill (Storage Layer)**: Stores complete project content, each can be tens of thousands of bytes
- **SOUL (Rule Layer)**: Injects MIS rules, automatically applied every turn

**Result: 10 projects = 10 index lines ≈ 500 bytes, effective capacity 100+ KB, ~100x expansion.**

---

## 📖 Before & After Example

### Before MIS

```
Memory (2200 bytes, 100% full):
────────────────────────────────────────────────────────────────────
distillyourself.cn — Vue3+Express+SQLite+multi-provider AI personality 
analysis engine. Server 59.110.226.32. JWT bypass captcha solution: see 
skill distillyourself Pitfall #40~41. MiMo JSON parsing issues see 
distillyourself references/mimo-json-parsing-issues.md. Batch distillation: 
see skill celebrity-batch-distill (JWT bypass captcha). Alibaba Cloud RAM 
strategy: distill-captcha/mail/DNSaccess.

DevEnv — Spring Boot + Vue 3 + Docker Compose development environment. 
Server 47.108.94.248. Domain: devenv.com.cn. Nginx reverse proxy, PM2 
process manager...

[ONLY 3-5 PROJECTS FIT!]
```

### After MIS

```
Memory (500 bytes, 23% used):
────────────────────────────────────────────────────────────────────
§distillyourself: see skill distillyourself. server 59.110.226.32.
§DevEnv: see skill devenv. server 47.108.94.248.
§blog: see skill personal-website. server 47.108.94.248.
§media: see skill self-media-video.
§celebrity: see skill celebrity-batch-distill.
§Hermes: see skill hermes-agent.
§identity: see skill fsw-identity.
§Feishu: see skill feishu-platform.
§todo: see skill todo-list.
§GitBrain: see skill gitbrain.

[10+ PROJECTS FIT! 100+ KB EFFECTIVE CAPACITY]
```

**The magic:** When Hermes sees `§distillyourself: see skill distillyourself`, it automatically loads the full Skill file with all details.

---

## ⚡ Quick Start

### Option 1: One-Command Install (Recommended)

Say to Hermes:
```
Install skill from https://github.com/FSWei/hermes-mis
```

Or use CLI:
```bash
hermes skills install https://github.com/FSWei/hermes-mis
```

Then say: `Enable memory optimization`

### Option 2: Manual Install

1. Copy `SKILL.md` to `~/.hermes/skills/hermes-mis.md`
2. Say to Hermes: `Enable memory optimization`
3. Hermes will automatically diagnose, optimize, and output results

---

## 📊 Optimization Results

| Metric | Before | After |
|--------|--------|-------|
| Memory Usage | 2200 bytes (100%) | ~500 bytes (23%) |
| Effective Capacity | 2.2 KB | 100+ KB |
| Project Support | 3-5 projects | 10-20 projects |

---

## 🔧 How It Works

### 1. Diagnose Memory

Hermes analyzes your Memory content and classifies it:
- **Index lines** (keep): Starts with `§`, contains `see skill`
- **User preferences** (keep): Name, IP, language, style, etc.
- **Project details** (migrate): Tech stack, server, API, architecture, etc.

### 2. Optimize Memory

Migrate project details from Memory to Skill, Memory only keeps indexes:

```
Before: distillyourself.cn — Vue3+Express+SQLite+multi-provider AI personality analysis engine. Server 59.110.226.32...
After: §distillyourself: see skill distillyourself. server 59.110.226.32.
```

### 3. Create Skill Files

Create independent Skill files for each project, containing complete technical details, architecture, Pitfalls, etc.

### 4. Inject MIS Rules

Inject MIS core rules into SOUL.md:
- **Memory Management**: Memory is index, Skill is storage
- **Write Rules**: Must read Memory before writing
- **Project Work**: For projects → read Memory to find index → skill_view to load

### 5. Verify

Check Memory usage rate, index integrity, SOUL rule completeness.

---

## 📊 Competitive Analysis

### Agent Memory Optimization Solutions

| Solution | Approach | Install | Dependencies | Agent Support |
|----------|----------|---------|--------------|---------------|
| **MIS** | Index + Skill | `hermes skills install` | Zero | Hermes |
| **Mem0** | API service | `pip install mem0ai` | Python + Server | Multi-agent |
| **Letta** | Context repos | Framework | Python + Git | Custom |
| **MemGPT** | Virtual memory | Framework | Python | Custom |
| **Claude Memory** | Built-in | N/A | None | Claude only |

### Key Differentiators

| Feature | MIS | Mem0 | Letta | MemGPT |
|---------|-----|------|-------|--------|
| **Zero install** | ✅ | ❌ | ❌ | ❌ |
| **Zero dependencies** | ✅ | ❌ (Python) | ❌ (Python) | ❌ (Python) |
| **One-command setup** | ✅ | ❌ | ❌ | ❌ |
| **Pure config** | ✅ | ❌ | ❌ | ❌ |
| **100x expansion** | ✅ | ~10x | ~50x | ~50x |
| **Hermes native** | ✅ | ❌ | ❌ | ❌ |
| **Version control** | ✅ (Skill files) | ❌ | ✅ (Git) | ❌ |

### Why MIS?

1. **Zero dependencies** — No Python, Node.js, or extra servers needed
2. **One-command setup** — Just say "Enable memory optimization"
3. **Pure config** — No code changes, just configuration
4. **100x expansion** — From 2.2KB to 100+KB effective capacity
5. **Hermes native** — Deep integration with Hermes Skill/Memory/SOUL
6. **Version control** — Skill files can be Git-tracked

---

## ❓ FAQ

**Q: Will optimization affect Hermes's normal operation?**
A: No. MIS only changes how Memory is used, all functions remain unchanged.

**Q: Do I need to manually load Skills after optimization?**
A: No. MIS rules are automatically applied. When Hermes sees `see skill xxx`, it automatically loads.

**Q: What if Memory approaches the limit again?**
A: Run `Enable memory optimization` again. Hermes will enter incremental mode, only optimizing problematic parts.

**Q: Can I use multiple projects simultaneously?**
A: Yes. Each project has its own Skill, Memory only adds one index line.

---

## 📄 License

MIT

## 🔗 Related Projects

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent Framework
