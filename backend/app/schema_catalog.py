# -*- coding: utf-8 -*-
"""命令表同步：直接读 `bili schema`，把 bili 的全部命令映射成面板的侧栏结构。

这样 bili-cli 增删命令、改参数、改必填，面板不用改代码 —— 每次请求按 schema 现算（带缓存）。
`schema` 挂了或结构变了，就退回手写的 catalog.CATALOG（保证面板还能用）。
"""
from __future__ import annotations

import re
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


def _label(help_text: str, raw: str) -> str:
    """中文短标签：去掉括号说明，取第一句，超长截断加省略号。"""
    text = (help_text or "").strip().replace("\n", " ")
    if not text:
        return raw
    text = re.sub(r"[（(][^）)]*[）)]", "", text)          # 去掉"（不会使服务器登出）"这类补充
    first = re.split(r"[。；;：:，,]", text)[0].strip(" 　·-")
    if len(first) > 12:
        first = first[:12] + "…"
    return first or raw


PARAM_LABELS = {
    "engine": "引擎", "kind": "类型", "status": "状态", "style": "样式",
    "provider": "服务商", "base-url": "接口地址", "base_url": "接口地址",
    "model": "模型", "device": "设备", "who": "谁", "uid": "UID",
    "bvid": "BV 号", "keyword": "关键词", "text": "正文", "num": "条数",
    "page": "页码", "pn": "页码", "ps": "每页条数", "order": "排序",
}


def _plabel(help_text: str, fallback: str) -> str:
    """参数的中文标签：取 help 第一句，去掉括号说明，最多 14 个字。"""
    fb = PARAM_LABELS.get(fallback, fallback)
    text = (help_text or "").strip().replace("\n", " ")
    if not text:
        return fb
    text = re.sub(r"[（(][^）)]*[）)]", "", text)
    # "auto 字幕…" 这类开头是取值枚举，把枚举词去掉；"BV 号" 这种要留着
    text = re.sub(r"^(auto|hd|preview|all|default|both)[ 　：:]*", "", text, flags=re.I)
    first = re.split(r"[。；;：:，,]", text)[0].strip(" 　·-")
    # 还是纯英文就别用它，退回参数名更有辨识度
    if first.isascii():
        return fb
    if len(first) > 14:
        first = first[:14] + "…"
    return first or fb


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
            "key": name, "label": _plabel(help_text, name), "pos": True, "flag": None,
            "type": "int" if ptype == "int" else "text",
            "default": "" if default is None else str(default),
            "choices": [], "ph": help_text[:40] or name,
        }

    flag = flags[0] if flags else None
    if not flag:
        return None
    label = _plabel(help_text, flag.lstrip("-"))
    if ptype in ("bool",) or isinstance(default, bool):
        return {"key": name, "label": label, "pos": False, "flag": flag,
                "type": "bool", "default": "", "choices": [], "ph": help_text[:40]}
    return {
        "key": name, "label": label, "pos": False, "flag": flag,
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
            "label": _label(str(item.get("help") or ""), raw),
            "cmd": raw,
            "argv": argv,
            "desc": str(item.get("help") or "").replace("\n", " ")[:120],
            "write": _is_write(raw),
            "params": params,
        })

    ordered = sorted(buckets, key=lambda g: (GROUP_ORDER.index(g) if g in GROUP_ORDER else 99, g))
    groups = [{"group": g, "items": buckets[g]} for g in ordered]
    _CACHE.update({"at": now, "version": version, "groups": groups})
    return groups, version, True
