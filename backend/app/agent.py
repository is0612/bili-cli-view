# -*- coding: utf-8 -*-
"""bili-cli 版的「自动值班」：定时起一个 headless 会话，让它用 bili 命令刷一轮。

和插件那套的区别：只有一套工具（bili CLI）、一份凭证、能力全（抽帧/转写/动态/投稿都能用）。
缺的"大脑"由 headless 会话提供，"闹钟"由这里的 asyncio 调度器提供。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any

from .paths import PROJECT_ROOT
from .runner import run_bili

RUNTIME = PROJECT_ROOT / "runtime"
DUTY_DIR = RUNTIME / "duty"
OUT_DIR = DUTY_DIR / "out"
LOG_DIR = DUTY_DIR / "logs"
CONFIG = DUTY_DIR / "config.json"
STATE = DUTY_DIR / "state.json"
SEEN = DUTY_DIR / "seen.md"
CHARTER = PROJECT_ROOT / "duty" / "duty.md"

DSH_BIN = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"

WINDOWS = {"noon": ("12:00", "14:00"), "night": ("18:00", "09:00")}

DEFAULTS: dict[str, Any] = {
    "perDay": 5,
    "peakValley": True,
    "noon": True,
    "night": True,
    "keywords": ["原神", "崩坏星穹铁道", "绝区零", "星布谷地", "米哈游", "DeepSeek", "AI", "萌宠"],
    "zone": "tech",
    "frames": 0,
    "autoComment": False,
    "mentionName": "",
    "commentPerRound": 1,
    "dmMode": "only",
    "reportLevel": "brief",
}

PICK_RE = re.compile(r"^###\s+(\S+)", re.MULTILINE)

_lock = asyncio.Lock()
_running = False
_last: dict[str, Any] = {}


def _ensure() -> None:
    for p in (DUTY_DIR, OUT_DIR, LOG_DIR):
        p.mkdir(parents=True, exist_ok=True)
    if not STATE.exists():
        STATE.write_text(json.dumps({"day": date.today().isoformat(), "picked": 0,
                                     "rounds": 0, "windows": {}}, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    if not SEEN.exists():
        SEEN.write_text("# 刷B站 · 判重表\n\n## 看过的视频\n\n", encoding="utf-8")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def config() -> dict[str, Any]:
    _ensure()
    cfg = {**DEFAULTS, **_read_json(CONFIG, {})}
    return cfg


def save(patch: dict[str, Any]) -> list[str]:
    _ensure()
    cfg = config()
    for key, value in patch.items():
        if key not in DEFAULTS:
            continue
        if key == "perDay":
            value = max(0, min(int(value or 0), 50))
        if key == "frames":
            value = max(0, min(int(value or 0), 30))
        if key == "commentPerRound":
            value = max(0, min(int(value or 0), 20))
        if key == "keywords":
            value = [str(k).strip() for k in value if str(k).strip()]
        cfg[key] = value
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return ["已写 runtime/duty/config.json"]


def _today() -> str:
    return date.today().isoformat()


def report_path(day: str | None = None) -> Path:
    return OUT_DIR / f"{day or _today()}.md"


def picked_today() -> int:
    st = _read_json(STATE, {})
    from_state = int(st.get("picked") or 0) if st.get("day") == _today() else 0
    text = ""
    try:
        text = report_path().read_text(encoding="utf-8")
    except OSError:
        pass
    return max(from_state, len({m.group(1) for m in PICK_RE.finditer(text)}))


def _save_state(**kw: Any) -> None:
    st = {**_read_json(STATE, {}), **kw}
    st["day"] = st.get("day") or _today()
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def _in_window(now: datetime, window: str) -> bool:
    start, end = WINDOWS[window]
    t = now.strftime("%H:%M")
    return (start <= t < end) if start < end else (t >= start or t < end)


def status() -> dict[str, Any]:
    _ensure()
    cfg = config()
    st = _read_json(STATE, {})
    picked = picked_today()
    return {
        "config": cfg,
        "state": {
            "day": _today(),
            "picked": picked,
            "perDay": cfg["perDay"],
            "remaining": max(0, cfg["perDay"] - picked),
            "rounds": int(st.get("rounds") or 0) if st.get("day") == _today() else 0,
            "running": _running,
            "last": _last or None,
            "report": str(report_path()),
            "seen": str(SEEN),
        },
        "windows": {k: {"start": v[0], "end": v[1]} for k, v in WINDOWS.items()},
        "engine": {"dsh": str(DSH_BIN), "node": NODE, "ready": DSH_BIN.exists() and bool(NODE)},
    }


def seen() -> dict[str, Any]:
    _ensure()
    text = SEEN.read_text(encoding="utf-8")
    videos, comments, rounds = [], [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        parts = [p.strip() for p in line.split("·")]
        if len(parts) >= 5 and re.match(r"^BV[0-9A-Za-z]+$", parts[1]):
            videos.append({"date": parts[0], "bvid": parts[1], "title": parts[2],
                           "author": parts[3], "result": " · ".join(parts[4:])})
        elif len(parts) == 2 and parts[0][:4].isdigit():
            rounds.append({"date": parts[0], "note": parts[1]})
    picked = sum(1 for v in videos if v["result"].startswith("收"))
    return {"path": str(SEEN), "videos": list(reversed(videos)), "comments": comments,
            "rounds": list(reversed(rounds)),
            "stats": {"total": len(videos), "picked": picked,
                      "skipped": len(videos) - picked, "rounds": len(rounds)}}


def _prompt(cfg: dict[str, Any]) -> str:
    charter = CHARTER.read_text(encoding="utf-8") if CHARTER.exists() else ""
    remaining = max(0, int(cfg["perDay"]) - picked_today())
    dm = {
        "only": "只发私信，不要发公开评论",
        "both": "私信 + 公开评论都发",
        "off": "不发私信，也不发评论（只写报告）",
    }.get(str(cfg["dmMode"]), "只发私信")
    comment = ""
    if cfg["autoComment"] and cfg["dmMode"] != "only":
        comment = (f"公开评论：开着，这一轮最多 {cfg['commentPerRound']} 条，"
                   + (f"每条正文里用纯文本 @ {cfg['mentionName']}" if cfg["mentionName"]
                      else "正文里一个 @ 都别写，别提主人"))
    else:
        comment = "公开评论：关着，一条都别发"
    return (
        charter.replace("N 条", f"{remaining} 条")
        + "\n\n---\n\n## 这一轮的设置\n\n"
        + f"- 今天日期：{_today()}\n"
        + f"- 今天还能挑：{remaining} 条（每天上限 {cfg['perDay']}）\n"
        + f"- 关注关键词：{'、'.join(cfg['keywords'])}\n"
        + f"- 热门分区：{cfg['zone']}\n"
        + f"- 抽帧：{cfg['frames']} 帧（0 = 不抽；这些图只有视觉模型才看得懂，你按 0 处理就行）\n"
        + f"- 投递：{dm}；{comment}\n"
        + f"- 判重表：{SEEN}\n"
        + f"- 报告：{report_path()}\n"
        + f"- 临时文件（写私信/评论正文用）：{DUTY_DIR / 'tmp-msg.txt'}\n\n"
        + "现在开始，最后用一句话汇报你挑到了什么。\n"
    )


async def run_round(why: str = "manual") -> dict[str, Any]:
    """起一个 headless 会话跑一轮；返回执行结果。"""
    global _running
    if _running:
        return {"ok": False, "error": "上一轮还没跑完"}
    if not DSH_BIN.exists():
        return {"ok": False, "error": f"找不到 dsh：{DSH_BIN}（先 npm i -g @deepseek-ai/dsh）"}

    cfg = config()
    _running = True
    _ensure()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"round-{datetime.now():%Y%m%d-%H%M%S}.log"
    started = time.time()
    try:
        prompt = _prompt(cfg)
        env = dict(os.environ)
        env["DSH_PERMISSION_MODE"] = "danger-full-access"   # 沙箱里 pwsh 起不来（0xC0000142）
        env["PYTHONIOENCODING"] = "utf-8"
        env.setdefault("DEEPSEEK_API_KEY", _deepseek_key())
        proc = await asyncio.create_subprocess_exec(
            NODE, str(DSH_BIN), "--profile", "headless", prompt,
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=900)
            code = proc.returncode
        except asyncio.TimeoutError:
            proc.kill()
            out = b"(timeout)"
            code = 124
        log_path.write_bytes(out)
        _save_state(rounds=int(_read_json(STATE, {}).get("rounds") or 0) + 1,
                    lastRunAt=datetime.now().isoformat(timespec="seconds"))
        _last.update({"why": why, "code": code, "log": str(log_path),
                      "seconds": round(time.time() - started, 1)})
        return {"ok": code == 0, "code": code, "log": str(log_path),
                "seconds": _last["seconds"], "picked": picked_today()}
    finally:
        _running = False


def _deepseek_key() -> str:
    try:
        text = (Path(os.environ.get("DSH_HOME", Path.home() / ".dsh")) / ".credentials.yaml").read_text(encoding="utf-8")
        m = re.search(r"DEEPSEEK_API_KEY:\s*(\S+)", text)
        return m.group(1) if m else ""
    except OSError:
        return ""


def reset_today() -> dict[str, Any]:
    """今天额度清零：报告归档、state 归零、seen 不动。"""
    _ensure()
    path = report_path()
    archived = None
    if path.exists() and path.stat().st_size:
        archived = path.with_name(f"{_today()}.{time.strftime('%H%M%S')}.bak.md")
        path.rename(archived)
    st = _read_json(STATE, {})
    windows = {k: v for k, v in (st.get("windows") or {}).items() if not str(k).startswith(_today())}
    STATE.write_text(json.dumps({"day": _today(), "picked": 0, "rounds": 0, "windows": windows},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    return {"archived": str(archived) if archived else None, "state": status()}


def report(day: str | None = None) -> dict[str, Any]:
    _ensure()
    path = report_path(day)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    return {"day": day or _today(), "path": str(path), "exists": path.exists(),
            "picks": len({m.group(1) for m in PICK_RE.finditer(text)}), "text": text}


async def scheduler_loop() -> None:
    """每 30 秒看一眼：谷时窗口内、还有额度、没在跑 ⇒ 跑一轮。"""
    while True:
        try:
            await asyncio.sleep(30)
            cfg = config()
            if not cfg["peakValley"] or _running:
                continue
            if picked_today() >= int(cfg["perDay"]):
                continue
            now = datetime.now()
            st = _read_json(STATE, {})
            windows = st.get("windows") or {}
            for key in ("noon", "night"):
                if not cfg.get(key):
                    continue
                if not _in_window(now, key):
                    continue
                mark = f"{_today()}:{key}"
                if windows.get(mark):
                    continue
                windows[mark] = True
                _save_state(windows=windows)
                await run_round(f"window:{key}")
                break
        except Exception:  # noqa: BLE001
            # 调度线程绝不能把进程带走
            continue
