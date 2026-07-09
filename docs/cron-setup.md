# MIS Archive Classification Cron Job

每周一次自动将归档条目分类到 Skills 或 Deep Archive。

## 组成部分

MIS 归档分类由两部分组成：

1. **数据收集脚本** — `scripts/archive-classify.py`（在仓库中）
   - 读取 memory-archive 和 user-archive 文件
   - 标记超过 30 天的条目（auto-sink 候选）
   - 扫描 Skills 索引
   - 输出 JSON 给 agent

2. **分类逻辑** — Hermes cron job prompt（本地注册，不在仓库中）
   - Agent 读取脚本输出的 JSON
   - LLM 判断每条属于哪个 Skill
   - 执行写入/移动操作

## 注册 Cron Job

在 Hermes 中使用 `cronjob` 工具注册：

```bash
cronjob(action='create', schedule='0 3 * * 1', name='MIS Archive Classification')
```

完整 prompt 文本：

```
MIS v3 每周归档分类任务。

运行脚本：
python3 ~/.hermes/profiles/chips/scripts/archive-classify.py

读取输出 JSON，然后：

1. 检查 summary
   - 如果 total_actionable == 0 → 输出"无需处理"，结束
   - 否则继续

2. 处理 auto_sink 条目（old 字段）
   - 直接移动到 deep-archive/references/archived-entries.md
   - 格式保持: [timestamp] [source] text
   - 从原 archive 文件删除

3. 处理 classify 条目（pending 字段）
   - 读取 text 字段内容
   - 在 skills 字典中查找最佳匹配（基于标题、描述、内容语义相关性）
   - 如果找到匹配 skill → 将条目写入该 skill 的 references/ 归档区
   - 如果无法匹配任何现有 skill → 留在 archive（下次再试）

输出格式：
- 每次操作（写入 Skill 或下沉 Deep Archive）记录一行
- 最后总结: 处理了多少条，写入哪些 Skills，下沉多少条
- 不要输出脚本原始数据，只输出决策结果
```

## 运行流程

```
每周一 03:00 (Hermes cron 触发)
       ↓
运行 archive-classify.py (数据收集)
       ↓
输出 JSON: 条目列表 + Skills 索引
       ↓
Agent LLM 分类
       ↓
┌─────────────────────────────────┐
│ >30 天条目 → Deep Archive       │
│ 匹配 Skill → 写入 Skill         │
│ 不匹配 → 留在 Archive           │
└─────────────────────────────────┘
       ↓
输出分类报告
```

## 手动运行

测试时可以手动触发：

```bash
# 收集数据
python3 ~/.hermes/profiles/chips/scripts/archive-classify.py

# 手动分类（模拟 cron job）
# 读取 JSON 输出，然后按上述流程处理
```

## 相关文件

- 数据收集脚本: `~/.hermes/profiles/chips/scripts/archive-classify.py`
- Memory Archive: `~/.hermes/profiles/chips/skills/memory-archive/references/archived-entries.md`
- User Archive: `~/.hermes/profiles/chips/skills/user-archive/references/user-entries.md`
- Deep Archive: `~/.hermes/profiles/chips/skills/deep-archive/references/archived-entries.md`

## 注意事项

- Cron job 注册在 Hermes 本地，不在仓库中
- 首次使用需要手动注册 cron job（见上方注册命令）
- 数据收集脚本可在任何地方运行（输出 JSON 给 agent）
- 分类逻辑依赖 Hermes cron job 的 prompt 文本