# Hermes MIS (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**One-command memory optimization for Hermes Agent — 100x capacity expansion via pure configuration. No source code changes.**

[中文文档](README.zh-CN.md)

## What is MIS?

Hermes's default Memory has only ~2200 bytes, which fills up quickly with detailed project information.

MIS (Memory-Index-Skill) splits Memory into three layers:
- **Memory (Index Layer)**: Only stores index lines, ~50 bytes each
- **Skill (Storage Layer)**: Stores complete project content, each can be tens of thousands of bytes
- **SOUL (Rule Layer)**: Injects MIS rules, automatically applied every turn

**Result: 10 projects = 10 index lines ≈ 500 bytes, effective capacity 100+ KB, ~100x expansion.**

## Quick Start

### Option 1: Manual Install

1. Copy `SKILL.md` to `~/.hermes/skills/hermes-mis.md`
2. Say to Hermes: `Enable memory optimization`
3. Hermes will automatically diagnose, optimize, and output results

### Option 2: Command Line Install

```bash
# Copy SKILL.md to Hermes skills directory
cp SKILL.md ~/.hermes/skills/hermes-mis.md

# Or create directory and copy
mkdir -p ~/.hermes/skills
cp SKILL.md ~/.hermes/skills/hermes-mis.md
```

Then say to Hermes: `Enable memory optimization`

## Optimization Results

| Metric | Before | After |
|--------|--------|-------|
| Memory Usage | 2200 bytes (100%) | ~500 bytes (23%) |
| Effective Capacity | 2.2 KB | 100+ KB |
| Project Support | 3-5 projects | 10-20 projects |

## How It Works

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

## Example

### Memory Before Optimization

```
distillyourself.cn — Vue3+Express+SQLite+multi-provider AI personality analysis engine. Server 59.110.226.32.
JWT bypass captcha solution: see skill distillyourself Pitfall #40~41. MiMo JSON parsing issues see 
distillyourself references/mimo-json-parsing-issues.md. Batch distillation: see skill 
celebrity-batch-distill (JWT bypass captcha). Alibaba Cloud RAM strategy: distill-captcha/mail/DNSaccess.
```

### Memory After Optimization

```
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
```

## FAQ

**Q: Will optimization affect Hermes's normal operation?**
A: No. MIS only changes how Memory is used, all functions remain unchanged.

**Q: Do I need to manually load Skills after optimization?**
A: No. MIS rules are automatically applied. When Hermes sees `see skill xxx`, it automatically loads.

**Q: What if Memory approaches the limit again?**
A: Run `Enable memory optimization` again. Hermes will enter incremental mode, only optimizing problematic parts.

**Q: Can I use multiple projects simultaneously?**
A: Yes. Each project has its own Skill, Memory only adds one index line.

## License

MIT

## Related Projects

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent Framework
- [GitBrain](https://github.com/fswei/gitbrain) — Multi-device Memory Sync (formerly MaC)
