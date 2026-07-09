#!/usr/bin/env python3
"""Archive Classification Context Collector (MIS Layer 2→3).

Reads memory-archive and user-archive files, identifies entries older than
30 days (auto-sink candidates), and outputs structured data for the agent
to classify into skills or deep-archive.

This script does NOT make classification decisions — it only collects and
formats data. The agent (LLM) does the actual classification.
"""

import json
import re
import os
from datetime import datetime, timedelta
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
# If HERMES_HOME already points to a profile dir, use it directly
if (HERMES_HOME / "skills").exists():
    PROFILE_DIR = HERMES_HOME
else:
    PROFILE_DIR = HERMES_HOME / "profiles" / "chips"
SKILLS_DIR = PROFILE_DIR / "skills"

MEMORY_ARCHIVE_FILE = SKILLS_DIR / "memory-archive" / "references" / "archived-entries.md"
USER_ARCHIVE_FILE = SKILLS_DIR / "user-archive" / "references" / "user-entries.md"
DEEP_ARCHIVE_FILE = SKILLS_DIR / "deep-archive" / "references" / "archived-entries.md"

AUTO_SINK_DAYS = 30


def read_entries(filepath: Path) -> list:
    """Read archive entries with timestamps."""
    if not filepath.exists():
        return []
    content = filepath.read_text(encoding="utf-8")
    entries = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith(">"):
            entries.append(line)
    return entries


def parse_entry(raw: str) -> dict:
    """Parse timestamped entry into structured data."""
    ts_match = re.match(r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\]\s*', raw)
    if ts_match:
        ts_str = ts_match.group(1)
        text = raw[ts_match.end():].strip()
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
        except ValueError:
            ts = None
    else:
        ts = None
        text = raw

    # Strip source prefix from deep-archive entries
    text = re.sub(r'^\[(memory|user)\]\s*', '', text)

    return {"raw": raw, "text": text, "timestamp": ts}


def get_skills_index() -> dict:
    """Get skill names with descriptions. Handles nested dirs."""
    skills = {}
    if not SKILLS_DIR.exists():
        return skills
    # Find all SKILL.md files (up to 2 levels deep)
    for skill_md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        # Skip if too deep (>2 levels from skills dir)
        rel = skill_md.relative_to(SKILLS_DIR)
        if len(rel.parts) > 2:
            continue
        name = skill_md.parent.name
        try:
            content = skill_md.read_text(encoding="utf-8")
            desc = ""
            desc_match = re.search(r'description:\s*>?\s*\n?\s*(.+)', content)
            if desc_match:
                desc = desc_match.group(1).strip()[:100]
            if not desc:
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("---") and not line.startswith("#") and not line.startswith(">"):
                        desc = line[:100]
                        break
            skills[name] = desc
        except Exception:
            skills[name] = "(unreadable)"
    return skills


def main():
    now = datetime.now()
    cutoff = now - timedelta(days=AUTO_SINK_DAYS)

    output = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "auto_sink_days": AUTO_SINK_DAYS,
    }

    # Process memory-archive
    mem_entries = read_entries(MEMORY_ARCHIVE_FILE)
    mem_old = []
    mem_pending = []
    for raw in mem_entries:
        entry = parse_entry(raw)
        if entry["timestamp"] and entry["timestamp"] < cutoff:
            mem_old.append(entry)
        else:
            mem_pending.append(entry)

    output["memory_archive"] = {
        "total": len(mem_entries),
        "old_count": len(mem_old),
        "pending_count": len(mem_pending),
        "old": [{"text": e["text"], "raw": e["raw"]} for e in mem_old],
        "pending": [{"text": e["text"], "raw": e["raw"]} for e in mem_pending],
    }

    # Process user-archive
    user_entries = read_entries(USER_ARCHIVE_FILE)
    user_old = []
    user_pending = []
    for raw in user_entries:
        entry = parse_entry(raw)
        if entry["timestamp"] and entry["timestamp"] < cutoff:
            user_old.append(entry)
        else:
            user_pending.append(entry)

    output["user_archive"] = {
        "total": len(user_entries),
        "old_count": len(user_old),
        "pending_count": len(user_pending),
        "old": [{"text": e["text"], "raw": e["raw"]} for e in user_old],
        "pending": [{"text": e["text"], "raw": e["raw"]} for e in user_pending],
    }

    # Deep archive stats
    deep_entries = read_entries(DEEP_ARCHIVE_FILE)
    output["deep_archive"] = {"total": len(deep_entries)}

    # Skills index
    output["skills"] = get_skills_index()

    # Summary
    total_actionable = len(mem_old) + len(mem_pending) + len(user_old) + len(user_pending)
    output["summary"] = {
        "total_actionable": total_actionable,
        "memory_auto_sink": len(mem_old),
        "user_auto_sink": len(user_old),
        "memory_classify": len(mem_pending),
        "user_classify": len(user_pending),
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
