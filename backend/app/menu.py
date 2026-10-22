# -*- coding: utf-8 -*-
"""菜单显隐配置：把「侧栏里不想看到的组/命令」记下来。

存在 DATA_HOME/menu.json（跟人走、可备份），结构：

    {
      "hidden_groups": ["投稿", "弹幕", ...],      # 整组藏掉
      "hidden_items": ["video.coin", "dm.send", ...] # 单条藏掉
    }

只存「隐藏了什么」，不存「显示清单」—— 因为菜单本体来自 `bili schema`，
每次请求现算，新增命令默认显示，省得配置里留一堆过期 id。
"""
from __future__ import annotations

from typing import Any

from .paths import MENU_JSON
from .settings import read_json

DEFAULT: dict[str, Any] = {"hidden_groups": [], "hidden_items": []}


def state() -> dict[str, Any]:
    cfg = read_json(MENU_JSON, DEFAULT)
    return {
        "hidden_groups": list(cfg.get("hidden_groups") or []),
        "hidden_items": list(cfg.get("hidden_items") or []),
    }


def save(hidden_groups: list[str] | None, hidden_items: list[str] | None) -> dict[str, Any]:
    """写入并返回归一化后的最新状态（顺带去重、清空串）。"""
    clean = lambda xs: sorted({str(x).strip() for x in (xs or []) if str(x).strip()})  # noqa: E731
    cfg = {"hidden_groups": clean(hidden_groups), "hidden_items": clean(hidden_items)}
    try:
        MENU_JSON.write_text(
            __import__("json").dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
    return cfg


def filter_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按隐藏配置过滤命令表：整组藏掉 + 组内逐条藏掉，空组一并移除。"""
    cfg = state()
    hidden_groups = set(cfg["hidden_groups"])
    hidden_items = set(cfg["hidden_items"])
    out: list[dict[str, Any]] = []
    for g in groups:
        if g.get("group") in hidden_groups:
            continue
        items = [it for it in (g.get("items") or []) if it.get("id") not in hidden_items]
        if not items:
            continue
        out.append({**g, "items": items})
    return out
