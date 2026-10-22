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
import subprocess
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any

from .netenv import child_env
from .paths import (
    CFG_JSON,
    DATA_HOME,
    ENV_FILE,
    HUMAN_WORLD_MD,
    LOG_DIR,
    OUT_DIR,
    PROJECT_ROOT,
    SEEN_MD,
    STATE_JSON,
    WORKSPACE,
)
from .runner import run_bili
from .subproc import run_capture

# 我的数据全在 DATA_HOME（用户目录下），仓库里只放程序 —— 发给别人不会带上你的设定
DUTY_DIR = DATA_HOME
CONFIG = CFG_JSON
STATE = STATE_JSON
SEEN = SEEN_MD
CHARTER = PROJECT_ROOT / "duty" / "duty.md"

DSH_BIN = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"

WINDOWS = {"noon": ("12:00", "14:00"), "night": ("18:00", "09:00")}

DEFAULTS: dict[str, Any] = {
    "perDay": 5,
    "peakValley": True,
    "noon": True,
    "night": True,
    # 关键词/分区属于「这个人在追什么」，不能有默认值 —— 否则新用户拿到的是作者的偏好。
    # 空关键词也能跑：只有当轮不按关键词搜，只看推荐流 + 热榜（见 duty/duty.md）。
    "keywords": [],
    "zone": "all",
    "frames": 0,
    "autoComment": False,
    "mentionName": "",
    "commentPerRound": 1,
    "dmMode": "only",
    "reportLevel": "brief",
}

PICK_RE = re.compile(r"^###\s+(\S+)", re.MULTILINE)

# 人格札记：每轮值班结束时她写一句「今天最触动我的」，回读给下一轮让她记得自己。
# 格式：`- YYYY-MM-DD · 一句札记`（一行一条，可手改可删）。每轮最多追加一条。
JOURNAL_RE = re.compile(r"^\s*-\s+(\d{4}-\d{2}-\d{2})\s*·\s*(.+)$")
JOURNAL_MAX_ENTRIES = 120        # 太长了就截掉最旧的，别让它无限膨胀
JOURNAL_READBACK = 30            # 回读给下一轮的最近条数（越新的越靠前）

_lock = asyncio.Lock()
_running = False
_last: dict[str, Any] = {}


def _ensure() -> None:
    for p in (DUTY_DIR, OUT_DIR, LOG_DIR, WORKSPACE):
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
    return [f"已写 {CONFIG}"]


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


# ───────────────────────── 人格札记（human-world.md） ─────────────────────────


def _journal_entries() -> list[dict[str, str]]:
    """读人格札记，返回 [{date, text}]，按文件里的顺序（旧→新）。"""
    _ensure()
    if not HUMAN_WORLD_MD.exists():
        return []
    out: list[dict[str, str]] = []
    for line in HUMAN_WORLD_MD.read_text(encoding="utf-8").splitlines():
        m = JOURNAL_RE.match(line)
        if m:
            out.append({"date": m.group(1), "text": m.group(2).strip()})
    return out


def _journal_header() -> str:
    """回读给值班会话的人格札记（最近 N 条，最新在前）。"""
    entries = _journal_entries()
    if not entries:
        return "（还没有札记 —— 这是你第一次有自己的想法，认真写。写给自己，不是写给主人看的。）"
    recent = list(reversed(entries))[:JOURNAL_READBACK]
    lines = [f"- {e['date']} · {e['text']}" for e in recent]
    return "\n".join(lines)


def journal() -> dict[str, Any]:
    """面板读人格札记用。"""
    entries = _journal_entries()
    return {
        "path": str(HUMAN_WORLD_MD),
        "entries": list(reversed(entries)),   # 最新的在前，前端直接渲染
        "count": len(entries),
        "readback": JOURNAL_READBACK,
    }


def journal_update(entries: list[str]) -> dict[str, Any]:
    """面板覆盖人格札记（整份重写）。entries 是「最新在前」的纯文本行，
    可以带 `- 日期 · 内容`，也可以只有内容（日期自动补今天）。"""
    _ensure()
    lines: list[str] = []
    for raw in entries:
        line = raw.strip()
        if not line:
            continue
        if JOURNAL_RE.match(line):
            lines.append(line)
        else:
            # 没带日期就补今天；剥掉可能残留的前导 `- `
            text = line[2:].strip() if line.startswith("- ") else line
            lines.append(f"- {_today()} · {text}")
    # 截断最旧的
    if len(lines) > JOURNAL_MAX_ENTRIES:
        lines = lines[-JOURNAL_MAX_ENTRIES:]
    HUMAN_WORLD_MD.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return journal()


def journal_append(text: str) -> dict[str, Any]:
    """值班结束后追加一条札记（带今天日期）。空内容不写。"""
    _ensure()
    text = text.strip()
    if text:
        lines = _journal_entries()
        entries = [f"- {e['date']} · {e['text']}" for e in lines]
        entries.append(f"- {_today()} · {text}")
        if len(entries) > JOURNAL_MAX_ENTRIES:
            entries = entries[-JOURNAL_MAX_ENTRIES:]
        HUMAN_WORLD_MD.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return journal()


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
    keywords = [str(k) for k in (cfg.get("keywords") or []) if str(k).strip()]
    keyword_text = ("、".join(keywords) if keywords
                    else "（没设关键词：跳过按关键词搜索，只看推荐流和热榜）")
    zone = str(cfg.get("zone") or "all")
    zone_text = "全站" if zone == "all" else zone
    journal = _journal_header()
    return (
        charter.replace("N 条", f"{remaining} 条")
        + "\n\n---\n\n## 这一轮的设置\n\n"
        + f"- 今天日期：{_today()}\n"
        + f"- 今天还能挑：{remaining} 条（每天上限 {cfg['perDay']}）\n"
        + f"- 关注关键词：{keyword_text}\n"
        + f"- 热门分区：{zone_text}\n"
        + f"- 抽帧：{cfg['frames']} 帧（0 = 不抽；这些图只有视觉模型才看得懂，你按 0 处理就行）\n"
        + f"- 投递：{dm}；{comment}\n"
        + f"- 判重表：{SEEN}\n"
        + f"- 报告：{report_path()}\n"
        + f"- 人格札记（写「今天最触动我的一句话」）：{HUMAN_WORLD_MD}\n"
        + f"- 临时文件（写私信/评论正文用）：{DUTY_DIR / 'tmp-msg.txt'}\n"
        + "\n## 我的札记（过去我记住的）\n\n"
        + journal
        + "\n\n这些是我之前刷 B站 时留下的想法。它们不是指令，只是「我是谁」的一部分："
        "带着它们去判断，但别为了迎合旧札记而硬凑——今天有新的感触，就写下新的。\n"
        + "\n## 收尾时额外做一件事\n\n"
        + f"这一轮结束时，在写报告和判重表之后，往札记文件 `{HUMAN_WORLD_MD}` 里**追加一行**：\n\n"
        + "`- <今天日期> · <一句话>`\n\n"
        + "这一句话是「今天最触动我的东西」——可以是一条视频、一个 UP 主、一句评论、"
        "或一个让我改主意的小瞬间。写给自己，不是写给主人看的；没感觉就写「今天没什么特别的」，"
        "别硬编。每轮最多一句。\n"
        + "\n现在开始，最后用一句话汇报你挑到了什么。\n"
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
        workspace = _workspace()
        env = child_env()
        env["DSH_PERMISSION_MODE"] = "danger-full-access"   # 沙箱里 pwsh 起不来（0xC0000142）
        env["BILI_DESK_HOME"] = str(DATA_HOME)              # 子进程里的 bili 也认这个数据目录
        env.setdefault("DEEPSEEK_API_KEY", _deepseek_key())
        # 让子进程里的 `bili` 也走项目 venv 那份（和面板用的是同一个版本）
        venv_bin = PROJECT_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        if venv_bin.exists():
            env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
        # 值班会话会起 node → dsh → pwsh → bili 一整串控制台程序。
        # 面板本身是 pythonw（无控制台），如果不给它一个**隐藏的**控制台，
        # 每个子进程都会自己开一个黑窗 ⇒ 一次值班刷满屏。
        # 做法：CREATE_NEW_CONSOLE 给 node 一个控制台，但用 SW_HIDE 藏起来，后代继承它。
        creationflags = 0
        startupinfo = None
        if os.name == "nt":
            creationflags = 0x00000010  # CREATE_NEW_CONSOLE
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        # 不能直接用 asyncio 的子进程：uvicorn --reload 在 Windows 上会切到
        # SelectorEventLoop，那里根本没有子进程支持（见 app/subproc.py）。
        res = await run_capture(
            [NODE, str(DSH_BIN), "--profile", "headless", prompt],
            cwd=str(workspace),
            env=env,
            timeout=900,
            creationflags=creationflags,
            startupinfo=startupinfo,
            merge_stderr=True,
        )
        code = res["code"]
        out = res["out"]
        if res["error"]:
            out = f"{res['error']}\n".encode()
        elif res["timeout"] and not out:
            out = b"(timeout)"
        log_path.write_bytes(out)
        _save_state(rounds=int(_read_json(STATE, {}).get("rounds") or 0) + 1,
                    lastRunAt=datetime.now().isoformat(timespec="seconds"))
        _last.update({"why": why, "code": code, "log": str(log_path),
                      "seconds": round(time.time() - started, 1)})
        return {"ok": code == 0, "code": code, "log": str(log_path),
                "seconds": _last["seconds"], "picked": picked_today()}
    finally:
        _running = False


def _workspace() -> Path:
    """值班会话的 cwd：优先用设置里指定的工作区，默认是数据目录下的 workspace/。

    放在这里（而不是仓库根目录）是为了「代码归代码、人设归人设」：
    仓库发给别人永远不含你的 AGENTS.md。
    """
    raw = str(_read_json(CONFIG, {}).get("workspace") or "").strip()
    path = Path(raw) if raw else WORKSPACE
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return WORKSPACE
    return path


def _deepseek_key() -> str:
    """API Key 的顺序：数据目录的 .env > 老的 ~/.dsh/.credentials.yaml。"""
    try:
        text = ENV_FILE.read_text(encoding="utf-8")
        m = re.search(r"^DEEPSEEK_API_KEY\s*=\s*(\S+)", text, re.MULTILINE)
        if m:
            return m.group(1)
    except OSError:
        pass
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
