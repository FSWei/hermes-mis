---
name: hermes-mis
description: "One-time memory architecture migration for Hermes. Diagnoses Memory usage, migrates project details to Skills, creates index lines, slims SOUL.md, and injects MIS rules that persist permanently via SOUL. Run once, benefit forever."
---

# Hermes MIS (Memory-Index-Skill)

**One-time migration, permanent benefit.** After one execution, MIS rules are written to SOUL.md and automatically applied every turn.

## Core Principle

```
Before: Memory stores project details → 2200 bytes full → 3-5 projects
After: Memory stores index + Skill stores details → 500 bytes + 100KB → 10-20 projects
```

**Three-layer architecture:**
- **Memory (Index Layer, ~500 bytes)**: `§project_name: see skill xxx. key_constants.`
- **Skill (Storage Layer, ~100KB)**: Complete project information
- **SOUL (Rule Layer, ~1KB)**: MIS core rules, injected every turn

## Execution Flow

### Step 1: Diagnose

**Actions:**
1. Use `read_file` to read `~/.hermes/memories/MEMORY.md`
2. Use `read_file` to read `~/.hermes/soul.md`
3. Use `skills_list` to view existing Skills

**Analyze Memory content, classify line by line:**

| Type | Criteria | Action |
|------|----------|--------|
| Index lines | Starts with `§`, contains `see skill` | Keep, check if corresponding Skill exists |
| User preferences | < 80 bytes, contains name/IP/language/style keywords | Keep |
| Project details | > 80 bytes, or contains tech stack/server/API/architecture keywords | Migrate to Skill |
| Ambiguous content | Between the two | List, ask user to decide |

**Keyword detection (any match = project details):**
- Tech: `tech stack`, `architecture`, `API`, `endpoint`, `database`, `framework`, `Vue`, `React`, `Express`, `SQLite`
- Deploy: `server`, `deploy`, `Nginx`, `Docker`, `SSL`, `domain`
- Status: `in development`, `completed`, `maintaining`, `Pitfalls`, `pending`
- Config: `port`, `path`, `config`, `environment variables`

**Output diagnostic report:**
```
📊 Memory Diagnostic

Usage: 2195/2200 bytes (99%)
Index lines: 3 (keep)
User preferences: 2 (keep)
Project details: 5 (need migration)
Ambiguous content: 1 (need confirmation)

❓ "xxx: ..." — Is this project detail or user preference?

After migration: ~500 bytes (23%)
```

### Step 2: Optimize Memory

**Use `memory` tool's `replace` operation to replace one by one:**

**Replacement rule:**
```
Old: Full project description (may be 200-500 bytes)
New: §project_name: see skill project_name. key_constants. (~50 bytes)
```

**Index line format specification:**
- Must start with `§`
- Must contain `see skill xxx`
- Can include 1-2 key constants (server IP, port, status)
- Total length ≤ 100 bytes

**Key constants selection priority:**
1. Server IP/domain (most frequently used)
2. Port number
3. Project status (in development/completed/maintaining)
4. Other high-frequency information

**Examples:**
```
§my-app: see skill my-app. server 1.2.3.4.
§blog: see skill blog. domain example.com. completed.
§api: see skill api. port 3000. in development.
```

### Step 3: Create Skill Files

**Use `skill_manage(action='create')` to create, auto-generated from Memory content:**

**Description auto-generation rules:**
- Extract from the first sentence of old content
- If it contains project type description, use directly
- Otherwise use "project_name — short description" format

**Skill content structure:**
```markdown
---
name: project_name
description: "One-sentence description migrated from Memory"
---

# Project Name

(Complete content migrated from Memory, reorganized)

## Basic Info
- Project Type: (Web app/CLI tool/library/service)
- Tech Stack: (extracted from old content)
- Server: (extracted from old content)
- Status: (in development/completed/maintaining)

## Detailed Info
(Technical details, architecture, API, etc. from old content)

## Pitfalls
(Problems and notes mentioned in old content)

## Related Resources
(Links and documentation addresses from old content)
```

**Handling existing Skills:**
- If Skill exists and content is complete → Skip, only update Memory index
- If Skill exists but missing migrated content → Use `skill_manage(action='patch')` to supplement
- If Skill exists but content conflicts → List differences, ask user

### Step 4: Slim SOUL.md and Inject MIS Rules

**Use `read_file` to read SOUL.md, analyze and slim down:**

**MIS core rules (must be written):**
```markdown
## Memory Management
Memory is index, Skill is storage. Must load when seeing "see skill xxx".
Project details go to Skill, Memory only stores index.

## Write Rules
Must read Memory before writing. Check existing entries before deciding add/replace/merge.
Project details → write to Skill, Memory only stores index.

## Project Work
For projects → read Memory to find index → skill_view to load → then start working.

## Todo Management
User says "remember this"/"add todo"/"add TODO" → read todo-list skill → append todo item.
User says "show todos" → read todo-list skill → display list.
Todo items only exist in todo-list skill, not in Memory.
```

**Personalized rules to keep (do not delete):**
- Lines containing `see skill` references (pointing to user's own Skills)
- Platform-specific rules (Feishu, WeChat, Telegram output formats)
- User identity/preference rules
- Todo management rules
- Security rules

**Content to delete:**
- Same rule appearing more than once (keep the most concise version)
- Project details (should be in Skill, not in SOUL)
- Outdated feature rules (no longer in use)
- Overly detailed explanations (SOUL only keeps trigger conditions, details go to Skill)

**SOUL size targets:**
- Ideal: 800-1200 bytes
- Acceptable: 1200-1800 bytes
- Needs slimming: > 1800 bytes

### Step 5: Verify

**Check each item:**

1. **Memory usage rate**
   - Target: < 50% (~1100 bytes)
   - If still > 70%, check for missed project details

2. **Index integrity**
   - Iterate all lines starting with `§` in Memory
   - Extract xxx from `see skill xxx`
   - Verify Skill exists with `skill_view(name=xxx)`
   - If Skill doesn't exist, create or report

3. **SOUL rule integrity**
   - Confirm contains "Memory Management" module
   - Confirm contains "Write Rules" module
   - Confirm contains "Project Work" module
   - Confirm size < 1800 bytes

4. **Output report:**
```
✅ MIS Migration Complete!

📊 Optimization Results:
- Memory: 2195 bytes (99%) → 480 bytes (22%)
- Skills: 5 created, 1 updated
- SOUL: 3.2KB → 1.1KB (MIS rules injected)
- Effective capacity: 2.2KB → 100+KB (~50x expansion)

📋 Created Skills:
- my-app (Web application)
- my-api (Backend service)
- my-blog (Personal blog)
...

⚠️ Notes:
- MIS rules written to SOUL.md, automatically applied from now on
- When adding new projects, Memory only stores index, details go to Skill
- If Memory approaches limit again, re-run this optimization
```

## Incremental Mode

If user's Memory is already in MIS format (mostly `§` index lines), but approaching the limit again:

1. Check for missed project details
2. Check for overly long index lines (> 100 bytes)
3. Check for duplicate index lines
4. Only optimize problematic parts, don't repeat the entire flow

## Edge Case Handling

**Memory already in MIS format:**
- Output "Already in MIS format, no optimization needed"
- Check index integrity

**SOUL already very slim (< 1KB):**
- Check if it contains MIS rules
- If missing, add MIS rules
- If already present, skip

**Skill exists but content incomplete:**
- List missing content
- Use `skill_manage(action='patch')` to supplement

**Memory content is all user preferences (no project details):**
- Output "No optimization needed, Memory is all user preferences"
- Suggest user add project information to Memory

## Notes

1. **Confirm before proceeding** — Ask user to continue after diagnosis
2. **Don't delete user preferences** — Name, IP, language, style stay in Memory
3. **Index lines must be concise** — Each line ≤ 100 bytes, only project name + key constants
4. **Skill naming must be semantically clear** — Filename is project name
5. **SOUL can't be too short** — At least keep Memory Management, Write Rules, Project Work
6. **One-time migration** — No need to trigger this Skill again after completion
