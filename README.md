# Hermes MIS (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

<p align="center">
  <strong>English</strong> | <a href="#中文">中文</a>
</p>

---

## English

**One-command memory optimization for Hermes — 100x capacity expansion without modifying source code.**

### What is MIS?

Hermes's default Memory has only ~2200 bytes, which fills up quickly with detailed project information.

MIS (Memory-Index-Skill) splits Memory into three layers:
- **Memory (Index Layer)**: Only stores index lines, ~50 bytes each
- **Skill (Storage Layer)**: Stores complete project content, each can be tens of thousands of bytes
- **SOUL (Rule Layer)**: Injects MIS rules, automatically applied every turn

**Result: 10 projects = 10 index lines ≈ 500 bytes, effective capacity 100+ KB, ~100x expansion.**

### Quick Start

#### Option 1: Manual Install

1. Copy `SKILL.md` to `~/.hermes/skills/hermes-mis.md`
2. Say to Hermes: `启用记忆优化` (Enable memory optimization)
3. Hermes will automatically diagnose, optimize, and output results

#### Option 2: Command Line Install

```bash
# Copy SKILL.md to Hermes skills directory
cp SKILL.md ~/.hermes/skills/hermes-mis.md

# Or create directory and copy
mkdir -p ~/.hermes/skills
cp SKILL.md ~/.hermes/skills/hermes-mis.md
```

Then say to Hermes: `启用记忆优化`

### Optimization Results

| Metric | Before | After |
|--------|--------|-------|
| Memory Usage | 2200 bytes (100%) | ~500 bytes (23%) |
| Effective Capacity | 2.2 KB | 100+ KB |
| Project Support | 3-5 projects | 10-20 projects |

### How It Works

#### 1. Diagnose Memory

Hermes analyzes your Memory content and classifies it:
- **Index lines** (keep): Starts with `§`, contains `详见 skill`
- **User preferences** (keep): Name, IP, language, style, etc.
- **Project details** (migrate): Tech stack, server, API, architecture, etc.

#### 2. Optimize Memory

Migrate project details from Memory to Skill, Memory only keeps indexes:

```
Before: distillyourself.cn — Vue3+Express+SQLite+multi-provider AI personality analysis engine. Server 59.110.226.32...
After: §distillyourself：详见 skill distillyourself。服务器 59.110.226.32。
```

#### 3. Create Skill Files

Create independent Skill files for each project, containing complete technical details, architecture, Pitfalls, etc.

#### 4. Inject MIS Rules

Inject MIS core rules into SOUL.md:
- **Memory Management**: Memory is index, Skill is storage
- **Write Rules**: Must read Memory before writing
- **Project Work**: For projects → read Memory to find index → skill_view to load

#### 5. Verify

Check Memory usage rate, index integrity, SOUL rule completeness.

### Example

#### Memory Before Optimization

```
distillyourself.cn — Vue3+Express+SQLite+multi-provider AI personality analysis engine. Server 59.110.226.32.
JWT bypass captcha solution: see skill distillyourself Pitfall #40~41. MiMo JSON parsing issues see 
distillyourself references/mimo-json-parsing-issues.md. Batch distillation: see skill 
celebrity-batch-distill (JWT bypass captcha). Alibaba Cloud RAM strategy: distill-captcha/mail/DNSaccess.
```

#### Memory After Optimization

```
§distillyourself：详见 skill distillyourself。服务器 59.110.226.32。
§DevEnv：详见 skill devenv。服务器 47.108.94.248。
§个人博客：详见 skill personal-website。服务器 47.108.94.248。
§自媒体：详见 skill self-media-video。
§名人蒸馏：详见 skill celebrity-batch-distill。
§Hermes配置：详见 skill hermes-agent。
§用户身份：详见 skill fsw-identity。
§飞书平台：详见 skill feishu-platform。
§待办：详见 skill todo-list。
§GitBrain：详见 skill gitbrain。
```

### FAQ

**Q: Will optimization affect Hermes's normal operation?**
A: No. MIS only changes how Memory is used, all functions remain unchanged.

**Q: Do I need to manually load Skills after optimization?**
A: No. MIS rules are automatically applied. When Hermes sees `详见 skill xxx`, it automatically loads.

**Q: What if Memory approaches the limit again?**
A: Run `启用记忆优化` again. Hermes will enter incremental mode, only optimizing problematic parts.

**Q: Can I use multiple projects simultaneously?**
A: Yes. Each project has its own Skill, Memory only adds one index line.

### License

MIT

### Related Projects

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent Framework
- [GitBrain](https://github.com/fswei/gitbrain) — Multi-device Memory Sync (formerly MaC)

---

<a id="中文"></a>

## 中文

**一句话启用 Hermes 记忆优化 — 不改源码，纯配置实现 100 倍容量扩展。**

### 什么是 MIS？

Hermes 原版 Memory 只有 ~2200 字节，存几个项目的详细信息就满了。

MIS (Memory-Index-Skill) 方案把 Memory 拆成三层：
- **Memory（索引层）**：只写索引行，每行约 50 字节
- **Skill（存储层）**：存完整项目内容，每个可达数万字节
- **SOUL（规则层）**：注入 MIS 规则，每轮自动生效

**效果：10 个项目 = 10 行索引 ≈ 500 字节，等效容量 100+ KB，扩展约 100 倍。**

### 快速开始

#### 方式一：手动安装

1. 把 `SKILL.md` 复制到 `~/.hermes/skills/hermes-mis.md`
2. 在 Hermes 中说：`启用记忆优化`
3. Hermes 会自动诊断、优化、输出结果

#### 方式二：命令行安装

```bash
# 复制 SKILL.md 到 Hermes skills 目录
cp SKILL.md ~/.hermes/skills/hermes-mis.md

# 或者创建目录并复制
mkdir -p ~/.hermes/skills
cp SKILL.md ~/.hermes/skills/hermes-mis.md
```

然后在 Hermes 中说：`启用记忆优化`

### 优化效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Memory 使用 | 2200 字节 (100%) | ~500 字节 (23%) |
| 有效容量 | 2.2 KB | 100+ KB |
| 项目支持 | 3-5 个 | 10-20 个 |

### 工作原理

#### 1. 诊断 Memory

Hermes 会分析你的 Memory 内容，分类为：
- **索引行**（保留）：以 `§` 开头，包含 `详见 skill`
- **用户偏好**（保留）：姓名、IP、语言、风格等
- **项目详情**（需迁移）：技术栈、服务器、API、架构等

#### 2. 优化 Memory

把项目详情从 Memory 迁移到 Skill，Memory 只保留索引：

```
旧：distillyourself.cn — Vue3+Express+SQLite+多Provider AI 人格分析引擎，服务器 59.110.226.32...
新：§distillyourself：详见 skill distillyourself。服务器 59.110.226.32。
```

#### 3. 创建 Skill 文件

为每个项目创建独立的 Skill 文件，包含完整的技术细节、架构、Pitfalls 等。

#### 4. 注入 MIS 规则

在 SOUL.md 中注入 MIS 核心规则：
- **记忆管理**：Memory 是索引，Skill 是存储
- **写入规则**：写 Memory 前必须先读 Memory
- **项目工作**：涉及项目 → 先读 Memory 找到索引 → skill_view 加载

#### 5. 验证

检查 Memory 使用率、索引完整性、SOUL 规则完整性。

### 示例

#### 优化前的 Memory

```
distillyourself.cn — Vue3+Express+SQLite+多Provider AI 人格分析引擎。服务器 59.110.226.32。
JWT 绕验证码方案：详见 skill distillyourself 的 Pitfall #40~41。MiMo JSON 解析问题见 
distillyourself 的 references/mimo-json-parsing-issues.md。批量蒸馏：详见 skill 
celebrity-batch-distill（JWT 绕验证码）。阿里云 RAM 策略：distill-captcha/mail/DNSaccess。
```

#### 优化后的 Memory

```
§distillyourself：详见 skill distillyourself。服务器 59.110.226.32。
§DevEnv：详见 skill devenv。服务器 47.108.94.248。
§个人博客：详见 skill personal-website。服务器 47.108.94.248。
§自媒体：详见 skill self-media-video。
§名人蒸馏：详见 skill celebrity-batch-distill。
§Hermes配置：详见 skill hermes-agent。
§用户身份：详见 skill fsw-identity。
§飞书平台：详见 skill feishu-platform。
§待办：详见 skill todo-list。
§GitBrain：详见 skill gitbrain。
```

### 常见问题

### Q: 优化后会影响 Hermes 的正常使用吗？

A: 不会。MIS 只是改变了 Memory 的使用方式，所有功能都保持不变。

### Q: 优化后需要手动加载 Skill 吗？

A: 不需要。MIS 规则会自动生效，当 Hermes 看到 `详见 skill xxx` 时会自动加载。

### Q: 如果 Memory 再次接近上限怎么办？

A: 重新运行 `启用记忆优化`，Hermes 会进入增量模式，只优化有问题的部分。

### Q: 可以同时使用多个项目吗？

A: 可以。每个项目一个 Skill，Memory 只增加一行索引。

### 许可证

MIT

### 相关项目

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent 框架
- [GitBrain](https://github.com/fswei/gitbrain) — 多设备记忆同步（原 MaC）
