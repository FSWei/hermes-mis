# Hermes MIS (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**一句话启用 Hermes 记忆优化 — 不改源码，纯配置实现 100 倍容量扩展。**

[English](README.md)

---

## 🎯 什么是 MIS？

Hermes 原版 Memory 只有 ~2200 字节，存几个项目的详细信息就满了。

MIS (Memory-Index-Skill) 方案把 Memory 拆成三层：
- **Memory（索引层）**：只写索引行，每行约 50 字节
- **Skill（存储层）**：存完整项目内容，每个可达数万字节
- **SOUL（规则层）**：注入 MIS 规则，每轮自动生效

**效果：10 个项目 = 10 行索引 ≈ 500 字节，等效容量 100+ KB，扩展约 100 倍。**

---

## 📖 优化前后对比

### 优化前

```
Memory（2200 字节，100% 满）：
────────────────────────────────────────────────────────────────────
my-webapp — React+Node.js+PostgreSQL 电商平台。
服务器 10.0.1.100。JWT 认证：已实现。支付集成：Stripe API。
数据库迁移：详见 skill my-webapp Pitfall #12。Redis 缓存产品列表...

my-api — FastAPI+Python REST API 服务。
服务器 10.0.1.101。端点：/users, /products, /orders。
速率限制：100 请求/分钟。API 文档在 /docs 端点...

[只能放 3-5 个项目！]
```

### 优化后

```
Memory（500 字节，23% 使用）：
────────────────────────────────────────────────────────────────────
§my-webapp：详见 skill my-webapp。服务器 10.0.1.100。
§my-api：详见 skill my-api。服务器 10.0.1.101。
§my-blog：详见 skill my-blog。域名 blog.example.com。
§my-bot：详见 skill my-bot。
§my-tools：详见 skill my-tools。
§user-config：详见 skill user-config。
§platform-a：详见 skill platform-a。
§project-x：详见 skill project-x。

[10+ 个项目！100+ KB 有效容量]
```

**魔法所在：** 当 Hermes 看到 `§my-webapp：详见 skill my-webapp` 时，会自动加载完整的 Skill 文件，获取所有详情。

---

## ⚡ 快速开始

### 方式一：一句话安装（推荐）

对 Hermes 说：
```
从 https://github.com/FSWei/hermes-mis 安装 skill
```

或使用命令行：
```bash
hermes skills install https://github.com/FSWei/hermes-mis
```

然后说：`启用记忆优化`

### 方式二：手动安装

1. 把 `SKILL.md` 复制到 `~/.hermes/skills/hermes-mis.md`
2. 在 Hermes 中说：`启用记忆优化`
3. Hermes 会自动诊断、优化、输出结果

---

## 📊 优化效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| Memory 使用 | 2200 字节 (100%) | ~500 字节 (23%) |
| 有效容量 | 2.2 KB | 100+ KB |
| 项目支持 | 3-5 个 | 10-20 个 |

---

## 🔧 工作原理

### 1. 诊断 Memory

Hermes 会分析你的 Memory 内容，分类为：
- **索引行**（保留）：以 `§` 开头，包含 `详见 skill`
- **用户偏好**（保留）：姓名、IP、语言、风格等
- **项目详情**（需迁移）：技术栈、服务器、API、架构等

### 2. 优化 Memory

把项目详情从 Memory 迁移到 Skill，Memory 只保留索引：

```
旧：my-webapp — React+Node.js+PostgreSQL 电商平台，服务器 10.0.1.100...
新：§my-webapp：详见 skill my-webapp。服务器 10.0.1.100。
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

---

## 📊 竞品分析

### Agent 记忆优化方案对比

| 方案 | 方式 | 安装 | 依赖 | Agent 支持 |
|------|------|------|------|-----------|
| **MIS** | 索引 + Skill | `hermes skills install` | 零 | Hermes |
| **Mem0** | API 服务 | `pip install mem0ai` | Python + 服务器 | 多 Agent |
| **Letta** | 上下文仓库 | 框架 | Python + Git | 自定义 |
| **MemGPT** | 虚拟内存 | 框架 | Python | 自定义 |
| **Claude Memory** | 内置 | N/A | 无 | 仅 Claude |

### 关键差异化

| 特性 | MIS | Mem0 | Letta | MemGPT |
|------|-----|------|-------|--------|
| **零安装** | ✅ | ❌ | ❌ | ❌ |
| **零依赖** | ✅ | ❌ (Python) | ❌ (Python) | ❌ (Python) |
| **一句话配置** | ✅ | ❌ | ❌ | ❌ |
| **纯配置** | ✅ | ❌ | ❌ | ❌ |
| **100 倍扩展** | ✅ | ~10 倍 | ~50 倍 | ~50 倍 |
| **Hermes 原生** | ✅ | ❌ | ❌ | ❌ |
| **版本控制** | ✅ (Skill 文件) | ❌ | ✅ (Git) | ❌ |

### 为什么选择 MIS？

1. **零依赖** — 不需要 Python、Node.js 或额外服务器
2. **一句话配置** — 只需说"启用记忆优化"
3. **纯配置** — 不改源码，只改配置
4. **100 倍扩展** — 从 2.2KB 到 100+KB 有效容量
5. **Hermes 原生** — 深度集成 Hermes Skill/Memory/SOUL
6. **版本控制** — Skill 文件可以用 Git 追踪

---

## ❓ 常见问题

### Q: 优化后会影响 Hermes 的正常使用吗？

A: 不会。MIS 只是改变了 Memory 的使用方式，所有功能都保持不变。

### Q: 优化后需要手动加载 Skill 吗？

A: 不需要。MIS 规则会自动生效，当 Hermes 看到 `详见 skill xxx` 时会自动加载。

### Q: 如果 Memory 再次接近上限怎么办？

A: 重新运行 `启用记忆优化`，Hermes 会进入增量模式，只优化有问题的部分。

### Q: 可以同时使用多个项目吗？

A: 可以。每个项目一个 Skill，Memory 只增加一行索引。

---

## 📄 许可证

MIT

## 🔗 相关项目

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — AI Agent 框架
