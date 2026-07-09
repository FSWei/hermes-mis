# Hermes MIS v3 (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**Hermes Agent 三层记忆管理引擎 — 活跃层 → 归档层 → 深度归档，代码级写入验证。**

[English](README.md)

---

## 🎯 MIS v3 是什么？

MIS 是 Hermes MemoryProvider 插件，把默认的扁平记忆系统升级为三层架构：

### Layer 1: 活跃层（MEMORY.md / USER.md）
- 每轮注入系统 prompt
- 只存短索引行：`§项目名：详见 skill xxx`
- **`mis_check` 工具**在写入前验证（代码级，非 prompt 级）
- 支持 `memory` 和 `user` 双目标拦截

### Layer 2: 归档层（memory-archive / user-archive）
- 溢出自动归档，带时间戳
- 每周 LLM 分类 cron，归位到正确的 Skill
- 跨层搜索（4 层：active memory + user + archive + user-archive）

### Layer 3: 深度归档（deep-archive）
- 永久存储，write-once，不再处理
- 30 天未归位的条目自动下沉

---

## ✨ v3 新特性

| 特性 | 说明 |
|------|------|
| **mis_check 工具** | 写入前验证，绕过核心工具名冲突 |
| **User 目标拦截** | memory 和 user 都走 MIS 策略检查 |
| **三层归档流水线** | Active → Archive → Deep Archive |
| **每周分类 cron** | LLM 自动将归档条目归位到正确 Skill |
| **30 天自动下沉** | 时间驱动，不依赖 LLM 判断 |
| **自动归档** | 溢出条目透明归档（不报错） |
| **跨层搜索** | 4 层搜索（memory + user + 两个 archive） |
| **优先级淘汰** | P0（核心）→ P3（临时） |
| **并发安全** | per-session 状态，gateway 多 session 安全 |

---

## 🚀 安装

```bash
# 一键安装
hermes plugins install FSWei/hermes-mis

# 启用
hermes plugins enable mis
hermes memory provider mis
```

配置 `~/.hermes/config.yaml`：
```yaml
memory:
  provider: mis
  memory_char_limit: 2200
  user_char_limit: 1375
```

验证：`hermes memory status` → 应显示 `Provider: mis ← active`

---

## 📖 使用

### mis_check 工作流

写入前先验证：
```
mis_check(content="...", target="memory")  → PASS/FAIL
  ↓ PASS
memory(action='add', content="...")
```

### Cron 脚本

```bash
cp scripts/archive-classify.py ~/.hermes/profiles/<profile>/scripts/
```

创建每周 cron job（周一 03:00），自动分类归档条目到 Skill 或深度归档。

---

## 📄 License

MIT
