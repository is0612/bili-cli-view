# -*- coding: utf-8 -*-
"""路径与运行环境：把散落在各处的“哪个文件说了算”收敛到一处。"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]          # bili-cli-view/
DSH_HOME = Path(os.environ.get("DSH_HOME") or (Path.home() / ".dsh"))
DUTY_HOME = DSH_HOME / "bili-duty"
CFG_JSON = DUTY_HOME / "config.json"
PATCH_YML = DSH_HOME / "profiles" / "desktop" / "cordis.patch.yml"
CREDS_YAML = DSH_HOME / ".credentials.yaml"
QR_PATH = PROJECT_ROOT / "runtime" / "login-qr.png"
BILI_CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "bili-cli"


def bili_bin() -> str:
    """找 `bili` 可执行文件。

    顺序：BILI_BIN 环境变量 > **项目自己的 .venv** > PATH > uv tool 的默认位置。
    项目 venv 优先，是为了「换台电脑 clone 下来就能用」—— 把 bili-agent 装进同一个 venv，
    不再需要全局 `uv tool install`（见 scripts/install.ps1）。
    """
    env = os.environ.get("BILI_BIN")
    if env and Path(env).exists():
        return env
    for cand in (
        PROJECT_ROOT / ".venv" / "Scripts" / "bili.exe",
        PROJECT_ROOT / ".venv" / "Scripts" / "bili",
        PROJECT_ROOT / ".venv" / "bin" / "bili",
    ):
        if cand.exists():
            return str(cand)
    found = shutil.which("bili")
    if found:
        return found
    for cand in (
        Path.home() / ".local" / "bin" / "bili.exe",
        Path.home() / ".local" / "bin" / "bili",
    ):
        if cand.exists():
            return str(cand)
    return "bili"


def ensure_dirs() -> None:
    QR_PATH.parent.mkdir(parents=True, exist_ok=True)
