# -*- coding: utf-8 -*-
"""自检：升级 bili-cli 之后跑一遍，确认面板依赖的命令和字段还在。

面板只用到 40 条命令里的稳定子集，但"稳定"是相对的：参数改名、JSON 字段改名都会让面板静默退化。
这里把依赖点显式列出来，逐条验证。
"""
from __future__ import annotations

from typing import Any

from .runner import bili_json, run_bili

# 面板的命令清单里真正用到的命令（catalog.py 里的 argv 前缀）
REQUIRED_COMMANDS = [
    "auth status", "me show", "me stats", "owner show", "owner set",
    "feed inbox", "feed recommend", "feed replies",
    "hot rank", "hot search", "hot popular", "hot weekly",
    "search video", "search user",
    "video watch", "video info", "video subtitle", "video summary", "video frames",
    "video like", "video fav", "video coin", "video triple", "video relation",
    "comment list", "comment post", "dm list", "dm send",
    "dynamic list", "dynamic post",
    "user info", "user videos",
]


def _ok(name: str, detail: str, passed: bool, hint: str = "") -> dict[str, Any]:
    return {"name": name, "ok": passed, "detail": detail, "hint": hint}


async def run() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1) 版本
    ver = await run_bili(["--version"], timeout=30)
    version = ((ver.get("json") or {}).get("data") or {}).get("version")
    checks.append(_ok("版本", version or "读不到", bool(version)))

    # 2) 登录态
    auth = await bili_json(["auth", "status"], timeout=40)
    user = ((auth or {}).get("data") or {}).get("user") or {}
    checks.append(_ok(
        "登录态",
        f"{user.get('name')}（Lv{user.get('level')}）" if user else "未登录",
        bool(auth and auth.get("ok")),
        "" if user else "在面板右上角扫码登录",
    ))

    # 3) 命令表：面板用到的命令是否都还在
    schema = await bili_json(["schema"], timeout=60)
    commands: set[str] = set()
    for item in (((schema or {}).get("data") or {}).get("commands") or []):
        name = item.get("command") or item.get("name") or "" if isinstance(item, dict) else str(item)
        commands.add(name[5:] if name.startswith("bili ") else name)
    missing = [c for c in REQUIRED_COMMANDS if c not in commands]
    checks.append(_ok(
        "命令表",
        "全部都在" if not missing else f"缺 {len(missing)} 条：{', '.join(missing[:6])}",
        not missing,
        "" if not missing else "bili 升级改了命令名，需要同步改 backend/app/catalog.py",
    ))

    # 4) 一次真实取数：字段形状还在不在
    rank = await bili_json(["hot", "rank", "--limit", "1"], timeout=60)
    items = ((rank or {}).get("data") or {}).get("items") or []
    first = items[0] if items else {}
    shape_ok = isinstance(first, dict) and bool(first.get("bvid")) and bool(first.get("title"))
    checks.append(_ok(
        "列表字段",
        f"items[0] = {first.get('bvid')} · {str(first.get('title'))[:24]}" if shape_ok else "列表字段不像预期",
        shape_ok,
        "" if shape_ok else "bvid/title 变了，前端 VideoCard 会缺字段",
    ))

    # 5) 单条详情：watch 的关键字段
    video = await bili_json(["video", "watch", str(first.get("bvid") or "BV1GJ411x7h7"),
                             "--frames", "0", "--comments", "0", "--max-chars", "200"],
                            timeout=120)
    data = (video or {}).get("data") or {}
    keys_ok = all(k in data for k in ("title", "owner", "stat", "ai_summary", "transcript"))
    checks.append(_ok(
        "详情字段",
        "title/owner/stat/ai_summary/transcript 都在" if keys_ok else "缺少 " + ", ".join(
            k for k in ("title", "owner", "stat", "ai_summary", "transcript") if k not in data),
        keys_ok,
        "" if keys_ok else "看 watch 的输出结构，前端 WatchView 要跟着改",
    ))

    passed = all(c["ok"] for c in checks)
    return {
        "ok": passed,
        "version": version,
        "checks": checks,
        "advice": "全部通过：可以放心用" if passed
        else "有项没过：先看 hint；面板的 catalog.py / 前端渲染可能需要跟着 bili 的新版本调整",
    }
