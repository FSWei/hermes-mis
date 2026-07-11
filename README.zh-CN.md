# Hermes MIS v4 (Memory-Index-Skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)

**Hermes Agent 三层记忆管理引擎 — 实时写入拦截 + 违规解决 + 自动 Skill 路由。**

[English](README.md)

---

## 🎯 MIS 是什么？

MIS 是 Hermes MemoryProvider 插件，把默认的扁平记忆系统升级为三层架构：

### Layer 1: 活跃层（MEMORY.md / USER.md）
- 每轮注入系统 prompt
- 只存短索引行：`§项目名：详见 skill xxx`
- **代码级写入拦截**（非 prompt 级）
- 支持 `memory` 和 `user` 双目标拦截

### Layer 2: 归档层（memory-archive / user-archive）
- 溢出自动归档，带时间戳
- 跨层搜索（4 层：active memory + user + archive + user-archive）

### Layer 3: 深度归档（deep-archive）
- 永久存储，write-once，不再处理
- 30 天未归位的条目自动下沉

---

## ✨ v4 新特性

### 🔴 实时写入拦截（修复致命 Bug）

**v3 问题：** `memory` 工具直接调用原生 MemoryStore，完全绕过 MIS。MIS 只能在事后记日志。

**v4 修复：** 通过 monkey-patch `tool_executor.handle_function_call`，在每次 memory 写入时将 `agent._memory_store` 替换为 `MISMemoryStore`。所有 memory 写入都经过 MIS 策略检查。不修改 Hermes 核心代码。

### 🔴 结构化违规解决

**v3 问题：** 违规返回字符串错误，agent 需要自己判断怎么做。

**v4 修复：** 违规返回结构化建议，用户可选择处理方式：

```python
# 违规时返回：
{
    "success": False,
    "error": "Too long (318 chars > 200)",
    "reason": "too_long",
    "suggestions": [
        {"action": "match_skill", "skill": "esp32-s3-touch-lcd-7", "hint": "追加到已有 Skill"},
        {"action": "create_skill", "skill": "esp32-project", "hint": "创建新 Skill"},
        {"action": "shorten", "hint": "缩短到150字符以内"},
        {"action": "force", "hint": "忽略限制直接写入"}
    ],
    "pending_id": 0
}
```

### 🟡 System Prompt 主动提醒

被拦截的写入会在 system prompt 中主动展示：

```
⚠️ [MIS] 1 条记忆写入被拦截：
  [0] "§ESP32-S3项目：dir=D:\PROJ\danzi..." (超长, 318字符 > 200)
      → 追加到已有 Skill: esp32-s3-touch-lcd-7
      → 缩短到150字符以内
  处理：mis(action='resolve', pending_id=0, choice='match_skill'|'create_skill'|'shorten'|'force')
```

### 🟡 自动 Skill 匹配

违规时自动：
1. 按关键词搜索已有 Skill 名称
2. 建议匹配的 Skill 追加内容
3. 建议新 Skill 名称
4. 解决时：创建短索引 + 将详情移入 Skill 的 `references/memory-overflow.md`

---

## 📖 使用

### 写入拦截（自动，无需手动操作）

```python
# 直接写入，MIS 自动拦截
memory(action='add', target='memory', content='很长的内容...')

# 如果被拦截，返回 suggestions 和 pending_id
# Agent 或用户选择处理方式
mis(action='resolve', pending_id=0, choice='match_skill', skill='target-skill')
```

### 解决违规

```python
# 查看待处理违规
mis(action='resolve')

# 四种处理方式
mis(action='resolve', pending_id=0, choice='match_skill', skill='esp32')  # 追加到已有 Skill
mis(action='resolve', pending_id=0, choice='create_skill', skill='new-skill')  # 创建新 Skill
mis(action='resolve', pending_id=0, choice='shorten', content='缩短后的内容')  # 手动缩短
mis(action='resolve', pending_id=0, choice='force')  # 强制写入
```

### 搜索与归档

```python
mis(action='search', keyword='distillyourself')  # 跨层搜索
mis(action='status')  # 查看状态
mis(action='check', content='...', target='memory')  # 写入前预检
```

---

## 🏗️ 架构

```
Agent 调用 memory(action='add', content='...')
                    ↓
tool_executor.handle_function_call()
  [MIS monkey-patch: 替换 agent._memory_store]
                    ↓
MISMemoryStore.add()
  → _check_mis_policy_v2(content)
     ├─ 通过 → super().add() → 原生 MemoryStore
     └─ 拦截 → 存为 pending_violation
                → 返回 suggestions
                → system prompt 展示
                    ↓
Agent 看到违规 → 用户选择解决方式
  → mis(action='resolve', choice='match_skill')
     ├─ match_skill → §索引 + 追加到 Skill references
     ├─ create_skill → 新建 SKILL.md + §索引
     ├─ shorten → 验证缩短后内容
     └─ force → 绕过策略直接写入
```

---

## 🚀 安装

```bash
# 一键安装
hermes plugins install FSWei/hermes-mis

# 启用
hermes plugins enable mis
hermes memory provider mis
```

手动安装：
```bash
mkdir -p ~/.hermes/plugins/memory/mis
cp __init__.py ~/.hermes/plugins/memory/mis/
cp plugin/plugin.yaml ~/.hermes/plugins/memory/mis/
hermes plugins enable mis
hermes memory provider mis
```

---

## 🔒 策略规则

```
< 50字符    → 直接通过
50-150字符  → 无结构化内容则通过
150-200字符 → 灰色地带，通过但有建议
> 200字符   → 拦截 → pending violation + 建议
结构化内容（列表、表格、步骤）→ 拦截
死引用（指向不存在的 Skill）→ 拦截
领域细节（IP、密码、Schema）→ 拦截
```

## ⚠️ Monkey-Patch 说明

MIS v4 通过 monkey-patch `tool_executor.handle_function_call` 实现写入拦截。原因：
1. `agent._memory_store` 在 Hermes 核心代码中初始化为原生 MemoryStore
2. 不能修改 Hermes 核心代码（避免更新时合并冲突）
3. patch 在插件初始化时执行一次，幂等（`_mis_patched` 标志位）

---

## 📄 License

MIT
