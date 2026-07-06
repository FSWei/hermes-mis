---
name: hermes-mis
description: "MIS (Memory-Index-Skill) — Hermes memory provider plugin with program-level enforcement. Memory stores indexes only, Skills store details. Zero-install, zero-dependency."
triggers:
  - 记忆扩展
  - memory扩展
  - 无限记忆
  - memory index skill
  - MIS
  - hermes-mis
  - memory优化
  - memory policy
---

# Hermes MIS (Memory-Index-Skill)

**Program-level memory policy enforcement for Hermes.**

Memory stores INDEXES ONLY. Skills store full details. Policy enforced at code level, not prompt level.

## Installation (Plugin — Recommended)

```bash
# One-command install
hermes plugins install FSWei/hermes-mis

# Activate
hermes plugins enable mis
```

Then edit `~/.hermes/config.yaml`:
```yaml
memory:
  provider: mis
```

Or use the interactive setup:
```bash
hermes memory setup
```

**Verify:**
```bash
hermes memory status
# Should show: Provider: mis
```

## How It Works

### Architecture

```
Native MemoryStore (tools/memory_tool.py)
    └── MISMemoryStore (inherits ALL storage logic)
            └── MISProvider (MemoryProvider plugin)
                    ├── add() → MIS policy check → super().add()
                    ├── replace() → MIS policy check → super().replace()
                    ├── apply_batch() → MIS policy check → super().apply_batch()
                    └── prefetch() → scan all entries for violations each turn
```

**Zero reimplementation.** All storage (persistence, § delimiter, dedup, drift detection, file locking, threat scanning, char limits) is inherited from the native MemoryStore. MIS only adds validation at write entry points.

### Policy Rules

| Content Type | Target | Action |
|---|---|---|
| `§name：详见 skill xxx` | memory | ✅ Allowed (index line) |
| Server IPs, ports, tech stack | memory | ❌ **Rejected** |
| API endpoints, credentials | memory | ❌ **Rejected** |
| User preferences, env info | memory | ✅ Allowed |
| Anything | user | ✅ Allowed (no MIS check) |

### What Happens When Policy Is Violated

1. **Write-time enforcement**: LLM calls `memory(action='add', content='服务器 10.0.1.1')` → **rejected** with clear error message telling it to use a Skill instead.

2. **Per-turn scanning**: `prefetch()` scans all memory entries each turn. If existing violations are found, a warning is injected into context every turn until fixed.

3. **Session-end logging**: Violations are logged at session end for observability.

## Migration (First-Time Setup)

After installing the plugin, existing memory entries may contain project details that should be in Skills. Run the migration:

### Step 1: Diagnose

1. Read `~/.hermes/memories/MEMORY.md` (or `~/.hermes/profiles/<profile>/memories/MEMORY.md`)
2. Identify entries with project details (IPs, tech stack, API endpoints, etc.)
3. List existing Skills with `skills_list`

### Step 2: Migrate

For each project detail entry in Memory:

1. **Create a Skill:**
   ```
   skill_manage(action='create', name='project-name', content='full project details here')
   ```

2. **Replace Memory entry with index line:**
   ```
   memory(action='replace', target='memory',
          old_text='the old project detail entry',
          content='§project-name：详见 skill project-name。关键常量。')
   ```

### Step 3: Verify

After migration, `prefetch()` should return empty (no violations). The plugin will warn you each turn about any remaining violations.

## Key Constants

- Memory char limit: 2200 (configurable via `memory.memory_char_limit`)
- User char limit: 1375 (configurable via `memory.user_char_limit`)
- Entry delimiter: `§` (newline-section sign-newline)

## Pitfalls

### Pitfall #1: Import Path Is Internal API
`from tools.memory_tool import MemoryStore` is not a public API. If Hermes restructures, the plugin fails with a clear error message. This is acceptable — the plugin tracks Hermes versions.

### Pitfall #2: Only One Memory Provider at a Time
Setting `memory.provider: mis` disables the native memory tool entirely. MIS handles ALL memory operations (add/replace/remove for both `memory` and `user` targets).

### Pitfall #3: Plugin Directory Location
User-installed plugins go to `$HERMES_HOME/plugins/`, which is profile-scoped:
- Default: `~/.hermes/plugins/`
- Profile "chips": `~/.hermes/profiles/chips/plugins/`
- Use `hermes memory status` to verify the plugin is discovered.

### Pitfall #4: User Target Bypasses MIS Check
MIS policy only validates `target='memory'`. The `target='user'` store (user profile) is unrestricted — user preferences, personal details, etc. go there freely.

## Uninstallation

```bash
# Remove plugin
rm -rf $HERMES_HOME/plugins/mis

# Or if installed via hermes plugins:
hermes plugins remove mis

# Revert to built-in memory
# Edit config.yaml: remove memory.provider or set to builtin
```

## References

- GitHub: https://github.com/FSWei/hermes-mis
- Hermes MemoryProvider docs: `agent/memory_provider.py`
- Native MemoryStore: `tools/memory_tool.py`
