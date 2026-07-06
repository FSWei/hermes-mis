# Hermes MIS (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**Hermes Agent 记忆策略插件 — 代码级强制执行。Memory 只存索引，Skill 存详情。零安装、零依赖。**

[English](README.md)

---

## 🎯 什么是 MIS？

Hermes 原版 Memory 只有 ~2200 字节，存几个项目的详细信息就满了。

MIS (Memory-Index-Skill) 把 Memory 拆成三层：
- **Memory（索引层）**：只写索引行，每行约 50 字节
- **Skill（存储层）**：存完整项目内容，每个可达数万字节
- **SOUL（规则层）**：注入 MIS 规则，每轮自动生效

**与纯提示词方案的区别**：MIS 在**代码层面**强制执行策略。当 LLM 尝试把项目详情写入 Memory 时，写入会被**直接拒绝**并返回明确的错误信息。这不是建议——这是程序级的门禁。

**效果：10 个项目 = 10 行索引 ≈ 500 字节，等效容量 100+ KB，扩展约 100 倍。**

---

## 🚀 一键安装

### 安装插件

```bash
hermes plugins install FSWei/hermes-mis
```

### 激活

```bash
hermes plugins enable mis
```

然后编辑 `~/.hermes/config.yaml`（或 `~/.hermes/profiles/<profile>/config.yaml`）：

```yaml
memory:
  provider: mis
```

或者用交互式设置：
```bash
hermes memory setup
```

### 验证

```bash
hermes memory status
# 应该显示：Provider: mis
```

**就这么简单。** 不需要 pip install，不需要 npm install，不需要外部服务，不需要 API Key。

---

## 📖 优化前后对比

### 优化前

```
Memory（2200 字节，100% 满）：
────────────────────────────────────────────────────────────────
my-webapp — React+Node.js+PostgreSQL 电商平台。
服务器 10.0.1.100。JWT 认证：已实现。支付集成：Stripe API。
数据库迁移：见 skill my-webapp Pitfall #12。Redis 缓存...

my-api — FastAPI+Python REST API 服务。服务器 10.0.1.101。
端点：/users, /products, /orders。限流：100 req/min...

[只能放 3-5 个项目！]
```

### 优化后

```
Memory（500 字节，23% 使用）：
────────────────────────────────────────────────────────────────
§my-webapp：详见 skill my-webapp。
§my-api：详见 skill my-api。
§my-blog：详见 skill my-blog。
§my-bot：详见 skill my-bot。
§my-tools：详见 skill my-tools。
§user-config：详见 skill user-config。
§platform-a：详见 skill platform-a。
§project-x：详见 skill project-x。

[10+ 个项目！等效容量 100+ KB]
```

---

## 🔧 工作原理

### 架构

```
原生 MemoryStore (tools/memory_tool.py)
    └── MISMemoryStore（继承全部存储逻辑）
            └── MISProvider（MemoryProvider 插件）
                    ├── add() → MIS 策略检查 → super().add()
                    ├── replace() → MIS 策略检查 → super().replace()
                    ├── apply_batch() → MIS 策略检查 → super().apply_batch()
                    └── prefetch() → 每轮扫描所有条目检测违规
```

**零重新实现。** 所有存储操作（持久化、§ 分隔符、去重、漂移检测、文件锁、威胁扫描、字符限制）全部继承自原生 MemoryStore。MIS 只在写入入口添加验证。

### 策略执行

| 内容类型 | 目标 | 结果 |
|---|---|---|
| `§name：详见 skill xxx` | memory | ✅ 允许（索引行） |
| 服务器 IP、端口、技术栈 | memory | ❌ **拒绝** |
| API 端点、凭证 | memory | ❌ **拒绝** |
| 用户偏好、环境信息 | memory | ✅ 允许 |
| 任何内容 | user | ✅ 允许（不检查） |

写入被拒绝时，LLM 会收到：
```
[MIS Policy] 内容包含项目详情（服务器 IP、端口）。
Memory 只接受索引行。请将项目详情存储在 Skill 中。

正确格式：
  memory(action='add', target='memory', content='§项目名：详见 skill skill-name。')

创建 Skill：
  skill_manage(action='create', name='skill-name', content='...')
```

### 每轮扫描

即使 Memory 中已有违规条目（MIS 安装前遗留的），插件每轮通过 `prefetch()` 扫描所有条目并在上下文中注入警告：

```
[MIS Alert] MEMORY.md 中有 2 条违规条目：
  - [服务器 IP] 服务器 59.110.226.32，/opt/distill/...
  - [技术栈] 技术栈：Vue 3 + Express + SQLite...
需要操作：将这些条目迁移到 Skill...
```

---

## 📦 仓库结构

```
hermes-mis/
├── plugin/               # Hermes MemoryProvider 插件
│   ├── plugin.yaml       # 插件元数据
│   └── __init__.py       # MISProvider + MISMemoryStore + 策略引擎
├── SKILL.md              # Hermes Skill（迁移指南 + 参考）
├── README.md             # 英文文档
├── README.zh-CN.md       # 本文件
├── LICENSE
└── .gitignore
```

---

## 🔄 迁移指南

安装插件后，现有 Memory 条目可能需要迁移：

1. **读取 Memory 文件：**
   ```
   read_file(path='~/.hermes/memories/MEMORY.md')
   # 或 profile 版：~/.hermes/profiles/<profile>/memories/MEMORY.md
   ```

2. **对每个项目详情条目，创建 Skill 并替换：**
   ```
   # 创建 Skill 存完整详情
   skill_manage(action='create', name='my-project', content='完整的项目信息...')
   
   # 替换 Memory 条目为索引行
   memory(action='replace', target='memory',
          old_text='旧的项目详情文本',
          content='§my-project：详见 skill my-project。')
   ```

3. **验证：** 所有违规修复后，`prefetch()` 返回空。

---

## ⚙️ 配置

```yaml
# config.yaml
memory:
  provider: mis                    # 激活 MIS
  memory_char_limit: 2200         # Memory 字符限制（默认：2200）
  user_char_limit: 1375           # User 字符限制（默认：1375）
```

---

## 🆚 对比

| 特性 | 纯提示词 MIS | **MIS 插件** |
|---|---|---|
| 策略执行 | LLM "应该遵守" 规则 | **代码级拒绝** |
| 可靠性 | ~70%（LLM 可能无视） | **~100%（程序强制）** |
| 每轮扫描 | 手动（SOUL.md 规则） | **自动（prefetch）** |
| 安装方式 | 手动编辑 SOUL.md | **`hermes plugins install`** |
| 更新方式 | 手动编辑 SKILL.md | **`hermes plugins update`** |
| 依赖 | 无 | 无 |
| 存储实现 | N/A（用原生） | **继承原生 MemoryStore** |

---

## ❓ FAQ

**Q: 会破坏现有 Memory 吗？**
A: 不会。MIS 只对新写入做验证。现有条目保留不变。`prefetch()` 扫描会把旧的违规条目标记为警告，直到你迁移它们。

**Q: 能和 MCP 记忆工具（engram、gbrain 等）一起用吗？**
A: 可以。MIS 替换的是内置 memory 工具。MCP 工具是独立的，可以并行使用。

**Q: Hermes 更新后插件会失效吗？**
A: 插件从 Hermes 的内部 API 导入 `MemoryStore`。如果 Hermes 重构了这个模块，插件会报明确的错误。更新插件或切回内置：`hermes memory setup`。

**Q: 影响 `user` 目标吗？**
A: 不影响。MIS 策略只验证 `target='memory'`。`target='user'` 不受限制。

---

## 📄 许可证

MIT

---

## 🔗 链接

- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent 文档](https://hermes-agent.nousresearch.com/docs)
