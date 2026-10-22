# -*- coding: utf-8 -*-
"""命令表同步：直接读 `bili schema`，把 bili 的全部命令映射成面板的侧栏结构。

这样 bili-cli 增删命令、改参数、改必填，面板不用改代码 —— 每次请求按 schema 现算（带缓存）。
`schema` 挂了或结构变了，就退回手写的 catalog.CATALOG（保证面板还能用）。
"""
from __future__ import annotations

import time
from typing import Any

from .catalog import CATALOG as STATIC_CATALOG
from .runner import bili_json

_CACHE: dict[str, Any] = {"at": 0.0, "version": None, "groups": None}
_TTL = 300  # 5 分钟内复用

# 一级命令 → 中文分组名（没列到的用原名）
GROUP_NAMES = {
    "auth": "账号", "me": "账号", "owner": "账号", "user": "用户",
    "feed": "发现", "hot": "发现", "search": "发现",
    "video": "视频", "comment": "评论", "dm": "私信", "dynamic": "动态",
    "upload": "投稿", "danmaku": "弹幕", "asr": "转写", "season": "合集",
    "skills": "系统", "mcp": "系统", "schema": "系统",
}
GROUP_ORDER = ["账号", "发现", "视频", "评论", "私信", "动态", "投稿", "合集", "弹幕", "转写", "用户", "系统"]

# 会往 B站 写东西的命令（默认加 --dry-run）
WRITE_VERBS = {
    "post", "reply", "delete", "pin", "like", "fav", "coin", "triple", "send",
    "recall", "set", "logout", "login", "upload", "edit", "install", "uninstall",
    "clear", "use", "vote", "rating", "reserve", "link", "follow", "remove",
}


def _is_write(path: str) -> bool:
    return any(part in WRITE_VERBS for part in path.split()[1:])


def _param(spec: dict[str, Any]) -> dict[str, Any] | None:
    name = spec.get("name") or ""
    if not name:
        return None
    kind = spec.get("kind")
    ptype = str(spec.get("type") or "str")
    flags = spec.get("flags") or []
    help_text = str(spec.get("help") or "")
    default = spec.get("default")

    if kind == "argument":
        return {
            "key": name, "label": name, "pos": True, "flag": None,
            "type": "int" if ptype == "int" else "text",
            "default": "" if default is None else str(default),
            "choices": [], "ph": help_text[:40] or name,
        }

    flag = flags[0] if flags else None
    if not flag:
        return None
    if ptype in ("bool",) or isinstance(default, bool):
        return {"key": name, "label": flag.lstrip("-"), "pos": False, "flag": flag,
                "type": "bool", "default": "", "choices": [], "ph": help_text[:40]}
    return {
        "key": name, "label": flag.lstrip("-"), "pos": False, "flag": flag,
        "type": "int" if ptype == "int" else "text",
        "default": "" if default is None else str(default),
        "choices": [], "ph": help_text[:40],
    }


async def build() -> tuple[list[dict[str, Any]], str | None, bool]:
    """返回 (groups, version, from_schema)。"""
    now = time.time()
    if _CACHE["groups"] and now - _CACHE["at"] < _TTL:
        return _CACHE["groups"], _CACHE["version"], True

    schema = await bili_json(["schema"], timeout=60)
    data = (schema or {}).get("data") or {}
    commands = data.get("commands") or []
    if not commands:
        return STATIC_CATALOG, None, False

    version = data.get("version")
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in commands:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("command") or "")
        if raw.startswith("bili "):
            raw = raw[5:]
        if not raw:
            continue
        argv = raw.split()
        group = GROUP_NAMES.get(argv[0], argv[0])
        params = [p for p in (_param(s) for s in (item.get("params") or [])) if p]
        buckets.setdefault(group, []).append({
            "id": raw.replace(" ", "."),
            "label": raw,
            "argv": argv,
            "desc": str(item.get("help") or "")[:80],
            "write": _is_write(raw),
            "params": params,
        })

    ordered = sorted(buckets, key=lambda g: (GROUP_ORDER.index(g) if g in GROUP_ORDER else 99, g))
    groups = [{"group": g, "items": buckets[g]} for g in ordered]
    _CACHE.update({"at": now, "version": version, "groups": groups})
    return groups, version, True
