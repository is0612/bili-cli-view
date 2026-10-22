# -*- coding: utf-8 -*-
"""「刷B站」值班设置：每天几条、谷时窗口、私信投递、日报档位、今日额度。

数据源和插件一致：
  config.json        插件自己的配置
  cordis.patch.yml   DSH profile 用户层（同一套字段，两边都要写）
  state.json         今天挑了几条 / 跑了几个窗口
  out/<date>.md      报告，`### BV…` 的条数才是「今天挑到的」权威计数
"""
from __future__ import annotations

import json
import re
import shutil
import time
from datetime import date
from pathlib import Path
from typing import Any

from .paths import CFG_JSON, DUTY_HOME, PATCH_YML

STATE_JSON = DUTY_HOME / "state.json"
OUT_DIR = DUTY_HOME / "out"

SCALARS = ["perDay", "peakValley", "noon", "night", "autoComment", "dmMode", "dmUid",
           "reportLevel", "workspace", "replyToComments", "replyPerRound",
           "commentPerRound", "mentionName"]

PICK_RE = re.compile(r"^###\s+(\S+)", re.MULTILINE)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def _today() -> str:
    return date.today().isoformat()


def _report_path(day: str | None = None) -> Path:
    return OUT_DIR / f"{day or _today()}.md"


def _picked_from_report(day: str | None = None) -> int:
    path = _report_path(day)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    return len({m.group(1) for m in PICK_RE.finditer(text)})


def _state() -> dict[str, Any]:
    st = _read_json(STATE_JSON, {})
    today = _today()
    picked_state = int(st.get("picked") or 0) if st.get("day") == today else 0
    # 和插件同一个口径：报告是事实来源，state 兜底，取大的
    picked = max(picked_state, _picked_from_report(today))
    return {
        "day": st.get("day") or today,
        "picked": picked,
        "count": int(st.get("count") or 0) if st.get("day") == today else 0,
        "windows": st.get("windows") or {},
    }


def _write_state(day: str, picked: int, count: int, windows: dict[str, Any]) -> None:
    STATE_JSON.write_text(
        json.dumps({"day": day, "count": count, "picked": picked, "windows": windows},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ───────────────────────── 读写配置 ─────────────────────────


def _patch_yml_block() -> tuple[list[str], int, int]:
    """返回 (行列表, bili-scroll 段起点, 段终点)。"""
    text = PATCH_YML.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if re.match(r"^\s*-\s*id:\s*bili-scroll\s*$", ln))
    end = next((j for j in range(start + 1, len(lines)) if re.match(r"^\s*-\s*id:", lines[j])), len(lines))
    return lines, start, end


def _yaml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or re.search(r"[:#\[\]{}&*!|>'\"%@`]", text) or text.strip() != text:
        return "'" + text.replace("'", "''") + "'"
    return text


def _write_yaml(patch: dict[str, Any]) -> bool:
    if not PATCH_YML.exists():
        return False
    lines, start, end = _patch_yml_block()
    block = lines[start:end]

    for key in SCALARS:
        if key not in patch:
            continue
        value = _yaml_value(patch[key])
        hit = None
        for i, ln in enumerate(block):
            if re.match(rf"^\s+{re.escape(key)}:", ln):
                hit = i
                break
        if hit is None:
            block.append(f"    {key}: {value}")
        else:
            block[hit] = f"    {key}: {value}"

    if "keywords" in patch:
        keywords = [str(k) for k in patch["keywords"] if str(k).strip()]
        head = next((i for i, ln in enumerate(block) if re.match(r"^\s+keywords:\s*$", ln)), None)
        if head is None:
            block.append("    keywords:")
            head = len(block) - 1
        idx = head + 1
        while idx < len(block) and re.match(r"^\s+-\s", block[idx]):
            block.pop(idx)
        for offset, keyword in enumerate(keywords):
            block.insert(head + 1 + offset, f"      - {_yaml_value(keyword)}")

    lines[start:end] = block
    PATCH_YML.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def snapshot() -> dict[str, Any]:
    cfg = _read_json(CFG_JSON, {})
    st = _state()
    per_day = int(cfg.get("perDay") or 0)
    return {
        "config": {k: cfg.get(k) for k in [
            "perDay", "peakValley", "noon", "night", "autoComment", "dmMode", "dmUid",
            "reportLevel", "workspace", "keywords", "transcribe", "asrModel",
        ]},
        "state": {
            "day": st["day"],
            "picked": st["picked"],
            "rounds": st["count"],
            "perDay": per_day,
            "remaining": max(0, per_day - st["picked"]),
            "report": str(_report_path()),
        },
        "windows": {
            "noon": {"label": "中午谷时", "start": "12:00", "end": "14:00"},
            "night": {"label": "夜间谷时", "start": "18:00", "end": "09:00"},
        },
    }


def save(patch: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    cfg = _read_json(CFG_JSON, {})

    if "perDay" in patch:
        patch["perDay"] = max(0, min(int(patch["perDay"] or 0), 50))
    if "dmUid" in patch:
        patch["dmUid"] = max(0, int(patch["dmUid"] or 0))

    cfg.update({k: v for k, v in patch.items() if k in SCALARS or k == "keywords"})
    CFG_JSON.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    notes.append("已写 config.json")

    if _write_yaml(patch):
        notes.append("已同步 cordis.patch.yml")
    else:
        notes.append("没找到 cordis.patch.yml，只改了 config.json")
    notes.append("DSH 里那套设置页要下次重启后才显示新值，但下一轮值班会按这里的值跑")
    return notes


def report(day: str | None = None) -> dict[str, Any]:
    """今天（或指定日期）的报告原文 —— 面板里直接看，不用去翻文件。"""
    path = _report_path(day)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    return {
        "day": day or _today(),
        "path": str(path),
        "exists": path.exists(),
        "picks": _picked_from_report(day),
        "text": text,
    }


def reset_today() -> dict[str, Any]:
    """把今天的额度清零：报告改名归档 + state 归零（判重表 seen.md 不动）。"""
    today = _today()
    report = _report_path(today)
    archived = None
    if report.exists() and report.stat().st_size > 0:
        archived = report.with_name(f"{today}.{time.strftime('%H%M%S')}.bak.md")
        shutil.move(str(report), str(archived))

    # 今天这个日期的窗口标记清掉，否则定时器会以为"今天这个窗口跑过了"
    st = _read_json(STATE_JSON, {})
    windows = {k: v for k, v in (st.get("windows") or {}).items() if not str(k).startswith(today)}
    _write_state(today, 0, 0, windows)

    return {"archived": str(archived) if archived else None, "state": snapshot()}
