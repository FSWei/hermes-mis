# Hermes MIS (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**一句话启用 Hermes 记忆优化 — 不改源码，纯配置实现 100 倍容量扩展。**

[English](README.md)

## 什么是 MIS？

Hermes 原版 Memory 只有 ~2200 字节，存几个项目的详细信息就满了。

MIS (Memory-Index-Skill) 方案把 Memory 拆成三层：
- **Memory（索引层）**：只写索引行，每行约 50 字节
- **Skill（存储层）**：存完整项目内容，每个可达数万字节
- **SOUL（规则层）**：注入 MIS 规则，每轮自动生效

**效果：10 个项目 = 10 行索引 ≈ 500 字节，等效容量 100+ KB，扩展约 100 倍。**

## 快速开始

### 方式一：手动安装

1. 把 `SKILL.md` 复制到 `~/.hermes/skills/hermes-mis.md`
2. 在 Hermes 中说：`启用记忆优化`
3. Hermes 会自动诊断、优化、输出结果

### 方式二：命令行安装

```bash
# 复制 SKILL.md 到 Hermes skills 目录
cp SKILL.md ~/.hermes/skills/hermes-mis.md

# 或者创建目录并复制
mkdir -p ~/.hermes/skills
cp SKILL.md ~/.hermes/skills/hermes-mis.md
```

然后在 Hermes 中说：`启用记忆优化`

## 优化效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Memory 使用 | 2200 字节 (100%) | ~500 字节 (23%) |
| 有效容量 | 2.2 KB | 100+ KB |
| 项目支持 | 3-5 个 | 10-20 个 |

## 工作原理

### 1. 诊断 Memory

Hermes 会分析你的 Memory 内容，分类为：
- **索引行**（保留）：以 `§` 开头，包含 `详见 skill`
- **用户偏好**（保留）：姓名、IP、语言、风格等
- **项目详情**（需迁移）：技术栈、服务器、API、架构等

### 2. 优化 Memory

把项目详情从 Memory 迁移到 Skill，Memory 只保留索引：

```
旧：distillyourself.cn — Vue3+Express+SQLite+多Provider AI 人格分析引擎，服务器 59.110.226.32...
新：§distillyourself：详见 skill distillyourself。服务器 59.110.226.32。
```

### 3. 创建 Skill 文件

为每个项目创建独立的 Skill 文件，包含完整的技术细节、架构、Pitfalls 等。

### 4. 注入 MIS 规则

在 SOUL.md 中注入 MIS 核心规则：
- **记忆管理**：Memory 是索引，Skill 是存储
- **写入规则**：写 Memory 前必须先读 Memory
- **项目工作**：涉及项目 → 先读 Memory 找到索引 → skill_view 加载

### 5. 验证

检查 Memory 使用率、索引完整性、SOUL 规则完整性。

## 示例

### 优化前的 Memory

```
distillyourself.cn — Vue3+Express+SQLite+多Provider AI 人格分析引擎。服务器 59.110.226.32。
JWT 绕验证码方案：详见 skill distillyourself 的 Pitfall #40~41。MiMo JSON 解析问题见 
distillyourself 的 references/mimo-json-parsing-issues.md。批量蒸馏：详见 skill 
celebrity-batch-distill（JWT 绕验证码）。阿里云 RAM 策略：distill-captcha/mail/DNSaccess。
```

### 优化后的 Memory

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

## 常见问题

### Q: 优化后会影响 Hermes 的正常使用吗？

A: 不会。MIS 只是改变了 Memory 的使用方式，所有功能都保持不变。

### Q: 优化后需要手动加载 Skill 吗？

A: 不需要。MIS 规则会自动生效，当 Hermes 看到 `详见 skill xxx` 时会自动加载。

### Q: 如果 Memory 再次接近上限怎么办？

A: 重新运行 `启用记忆优化`，Hermes 会进入增量模式，只优化有问题的部分。

### Q: 可以同时使用多个项目吗？

A: 可以。每个项目一个 Skill，Memory 只增加一行索引。

## 许可证

MIT

## 相关项目

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent 框架
- [GitBrain](https://github.com/fswei/gitbrain) — 多设备记忆同步（原 MaC）
