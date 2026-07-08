# Hermes MIS v2 (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**Hermes Agent 双层记忆管理引擎 — 活跃层 + 归档层，自动归档、跨层搜索、访问追踪、写入回退。**

[English](README.md)

---

## 🎯 MIS v2 是什么？

MIS 是 Hermes MemoryProvider 插件，把默认的扁平记忆系统升级为双层架构：

### Layer 1: 活跃层（MEMORY.md）
- 每轮注入系统 prompt（~2,200 字符）
- 只存短索引行：`§项目名：详见 skill xxx`
- 代码级写入验证（格式、长度、结构、死引用）

### Layer 2: 归档层（memory-archive skill）
- 首次淘汰时自动创建
- 带时间戳的归档条目，可通过 `memory(action='search')` 搜索
- 通过 `memory(action='promote')` 恢复
- 50KB 软限制，自动压缩旧条目

---

## ✨ v2 新特性

| 特性 | 说明 |
|------|------|
| **自动归档** | 溢出条目透明归档（不报错） |
| **跨层搜索** | `memory(action='search', keyword='...')` 同时搜索两层 |
| **归档恢复** | `memory(action='promote', old_text='...')` 从归档恢复 |
| **状态查询** | `memory(action='status')` 查看容量统计 |
| **手动归档** | `memory(action='archive', old_text='...')` 手动归档 |
| **写入回退** | 四级回退链，数据永不丢失 |
| **访问追踪** | 关键词匹配，per-session，无 LLM 调用 |
| **优先级淘汰** | P0（核心）→ P1（环境）→ P2（项目）→ P3（临时） |
| **死引用检测** | 检测引用不存在的 skill |
| **并发安全** | per-session 状态，支持 gateway 多 session |
| **压缩前保存** | 上下文压缩前提取关键信息 |
| **对话事实标记** | 扫描对话中的记忆关键词 |

---

## 🚀 安装

```bash
# 一键安装
hermes plugins install FSWei/hermes-mis

# 启用
hermes plugins enable mis
hermes memory provider mis
```

---

## 📖 使用

### 标准操作（向后兼容）

```python
memory(action='add', target='memory', content='§项目：详见 skill my-project')
memory(action='replace', target='memory', old_text='旧内容', content='新内容')
memory(action='remove', target='memory', old_text='要删除的内容')
```

### v2 新操作

```python
memory(action='search', keyword='distillyourself')     # 跨层搜索
memory(action='promote', old_text='distillyourself')    # 恢复归档
memory(action='status')                                 # 状态查询
memory(action='archive', old_text='旧项目')              # 手动归档
```

---

## 📄 License

MIT
