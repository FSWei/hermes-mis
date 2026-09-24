#!/usr/bin/env python3
"""MIS plugin test suite (2026-09-24) — tests for all fixes + registry.

Run: python3 tests/test_mis.py   (from the repo root, or anywhere)
Exits non-zero on any failure.

⚠️ Lives in tests/, NEVER in plugin/ — Hermes' memory provider loader
execs every *.py inside the plugin dir (plugins/memory/__init__.py
`provider_dir.glob("*.py")`), so module-level test code would run inside
the gateway process and hijack HERMES_HOME / call sys.exit().
"""
import json
import os
import sys
import tempfile
from pathlib import Path

PLUGIN_FILE = Path(__file__).resolve().parent.parent / "plugin" / "__init__.py"

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def main():
    global PASS, FAIL

    # Make hermes internals importable
    sys.path.insert(0, "/usr/local/lib/hermes-agent")

    # Redirect registry/access-log into a temp dir before importing the plugin
    tmpdir = tempfile.mkdtemp(prefix="mis_test_")
    os.environ["HERMES_HOME"] = tmpdir

    import importlib.util
    spec = importlib.util.spec_from_file_location("mis_plugin", str(PLUGIN_FILE))
    mis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mis)

    print("== 1. Unified violation scan (P0-2) ==")
    # create a real skill so dead-reference check passes
    skdir = Path(tmpdir) / "skills" / "bar"
    skdir.mkdir(parents=True, exist_ok=True)
    (skdir / "SKILL.md").write_text("---\nname: bar\n---\n# bar\n")
    # index line → allowed
    v = mis.scan_memory_violations(["§foo：详见 skill bar"])
    check("index line not flagged", len(v) == 0, str(v))
    # short entry → allowed (write policy allows it)
    v = mis.scan_memory_violations(["short pref entry"])
    check("short entry not flagged", len(v) == 0, str(v))
    # long structured → flagged with fp
    long_entry = "- point one\n- point two\n" + "x" * 120
    v = mis.scan_memory_violations([long_entry])
    check("long structured flagged", len(v) == 1, str(v))
    check("violation has fp", v and "fp" in v[0], str(v))
    # >200 chars → flagged
    v = mis.scan_memory_violations(["y" * 250])
    check("too-long flagged", len(v) == 1, str(v))

    print("== 2. Index regex accepts no-space 详见skill (P0-2) ==")
    check("with space", bool(mis._INDEX_LINE_RE.match("§模型配置：详见 skill model-config")))
    check("no space", bool(mis._INDEX_LINE_RE.match("§火焰识别项目：详见skill esp32-cam-pc-vision")))

    print("== 3. Similarity ratio (P1) ==")
    r = mis._similarity_ratio("偏好中文界面，偏好可视化面板显示", "偏好中文界面，偏好可视化面板展示")
    check("near-duplicate >0.6", r > 0.6, f"{r:.2f}")
    r2 = mis._similarity_ratio("偏好中文界面", "Minecraft多版本共存目录清理方案")
    check("unrelated <0.4", r2 < 0.4, f"{r2:.2f}")

    print("== 4. Priority classification & evict ordering (P0-1) ==")
    check("P0 by 偏好", mis._classify_priority("封面偏好：极简纯黑") == "P0")
    check("P2 index", mis._classify_priority("§chips-town：详见 skill chips-town") == "P2")
    check("P3 temp", mis._classify_priority("临时缓存条目 Cron jobs") == "P3")
    entries = ["偏好A", "普通B", "§索引C：详见 skill x", "临时D Cron jobs"]
    ranked = sorted(entries, key=lambda e: -mis._priority_rank(e))
    check("evict order P3→P1→P0", ranked[0].startswith("临时") and ranked[-1].startswith("偏好"), str(ranked))

    print("== 5. Persistent access log ==")
    log = {"entry1": {"last_seen": "2026-09-01T00:00:00", "count": 3}}
    mis._save_access_log(log)
    loaded = mis._load_access_log()
    check("save/load roundtrip", loaded == log, str(loaded))
    check("access log path in tmp", str(mis._access_log_path()).startswith(tmpdir), mis._access_log_path())

    print("== 6. Registry CRUD + dashboard (P2-6/7) ==")
    reg = mis._Registry()
    r = reg.add({"name": "chips-town", "type": "project", "path": "/mnt/d/Proj/chips-town",
                 "skill": "chips-town"})
    check("add ok", r.get("success") is True, str(r))
    r = reg.add({"name": "chips-town", "type": "project"})
    check("dup name rejected", r.get("success") is False, str(r))
    r = reg.add({"name": "aliyun-47", "type": "server", "server": "47.108.94.248"})
    check("second add ok", r.get("success") is True, str(r))
    check("default type", reg.list()[0].get("type") == "project")
    check("default status", all(e.get("status") == "active" for e in reg.list()))
    r = reg.update({"name": "chips-town", "status": "paused"})
    check("update ok", r.get("success") is True and r["entry"]["status"] == "paused", str(r))
    r = reg.update({"name": "nonexistent", "status": "x"})
    check("update missing fails", r.get("success") is False, str(r))
    check("keyword filter", len(reg.list("aliyun")) == 1)
    check("keyword filter miss", len(reg.list("zzz")) == 0)
    dash = reg.dashboard()
    check("dashboard file exists", Path(dash).exists(), dash)
    html = Path(dash).read_text(encoding="utf-8")
    check("dashboard has name", "chips-town" in html)
    check("dashboard has badge", "badge" in html and "paused" in html)
    r = reg.remove({"name": "aliyun-47"})
    check("remove ok", r.get("success") is True, str(r))
    check("count now 1", len(reg.list()) == 1)
    reg2 = mis._Registry()
    check("reload from disk", len(reg2.list()) == 1 and reg2.list()[0]["name"] == "chips-town")

    print("== 7. Store duplicate detection (P1-4) ==")
    store = mis.MISMemoryStore(memory_char_limit=2200, user_char_limit=1375)
    try:
        store.add("memory", "§测试条目：一段用于测试的普通短内容")
        check("first add ok", any("测试条目" in e for e in store._entries_for("memory")))
        res = store.add("memory", "§测试条目：完全不同的另一段内容，端口8080服务器部署")
        check("dup topic blocked", res.get("success") is False and res.get("reason") == "duplicate_topic", str(res))
        a = "容器方案A：使用Docker容器化部署，端口8080，Nginx反向代理，HTTPS证书自动续期，日志轮转保留30天，健康检查每分钟"
        b = "镜像方案B：使用Docker容器化部署，端口9090，Nginx反向代理，HTTPS证书自动续期，日志轮转保留60天，健康检查每两分"
        store.add("memory", a)
        res = store.add("memory", b)
        check("similar blocked", res.get("success") is False and res.get("reason") == "similar_entry", str(res))
        res = store.replace("memory", "§测试条目", "§测试条目：更新后的索引内容")
        check("self-replace not dup-blocked", res.get("reason") != "duplicate_topic", str(res))
    except Exception as e:
        check("store dup test ran", False, repr(e))

    print("== 8. Policy suggestions include registry for entity content ==")
    sug = mis._build_suggestions("服务器部署：Docker容器化，端口8080，Nginx反代配置", "domain_details")
    check("registry suggestion present", any(s.get("action") == "registry" for s in sug), str(sug))

    print("== 9. Provider wiring ==")
    p = mis.MISProvider()
    check("registry attached", hasattr(p, "_registry") and isinstance(p._registry, mis._Registry))
    check("access persist is dict", isinstance(p._access_persist, dict))
    schema = mis.MIS_MEMORY_SCHEMA
    check("schema has registry action", "registry" in schema["parameters"]["properties"]["action"]["enum"])
    check("schema has op param", "op" in schema["parameters"]["properties"])
    check("schema has entry param", "entry" in schema["parameters"]["properties"])
    res = json.loads(p.handle_tool_call("mis", {"action": "registry", "op": "add",
        "entry": json.dumps({"name": "wired-test", "type": "device"})}))
    check("handler add works", res.get("success") is True, str(res))
    res = json.loads(p.handle_tool_call("mis", {"action": "registry"}))
    check("handler list works", res.get("success") is True and res.get("count", 0) >= 1, str(res))

    print(f"\n{'='*40}\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
