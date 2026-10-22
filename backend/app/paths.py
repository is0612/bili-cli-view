# -*- coding: utf-8 -*-
"""路径与运行环境：把散落在各处的"哪个文件说了算"收敛到一处。

这里严格分两类，别混：

* **程序**（跟着仓库走，只读）：代码、`dist/`、`duty/duty.md` 章程；
* **我的数据**（跟着人走，可备份可搬走）：`DATA_HOME`，默认在用户目录下，**不在仓库里**。

分这一刀的原因：
  把仓库整个拷给别人时，你的设定、判重表、报告不会跟过去（新人是干净的）；
  换台电脑时，把这个目录带走（或导出成 zip）就还是你自己的数据。

`DATA_HOME` 可以用环境变量 `BILI_DESK_HOME` 覆盖 —— 指到 OneDrive / 坚果云 里就等于自动同步。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]          # bili-desk/

# 便携模式的数据目录：程序目录下的 data/。存在就用它，数据跟着文件夹走。
PORTABLE_HOME = PROJECT_ROOT / "data"


def _appdata_home() -> Path:
    """系统默认位置（非便携模式）。"""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "bili-desk"


def _data_home() -> Path:
    """数据目录三档：环境变量 > 程序目录下的 data/（便携） > 系统用户目录。"""
    env = os.environ.get("BILI_DESK_HOME")
    if env:
        return Path(env).expanduser()
    if PORTABLE_HOME.is_dir():
        return PORTABLE_HOME
    return _appdata_home()


# ── 我的数据（会被导出/导入/搬走） ─────────────────────────────
DATA_HOME = _data_home()
# 系统默认位置（非便携模式下与 DATA_HOME 相同）。便携模式下用来把旧数据搬过来。
APPDATA_HOME = _appdata_home()

WORKSPACE = DATA_HOME / "workspace"        # 值班会话的 cwd，放 AGENTS.md
AGENTS_MD = WORKSPACE / "AGENTS.md"
CFG_JSON = DATA_HOME / "config.json"
MENU_JSON = DATA_HOME / "menu.json"
STATE_JSON = DATA_HOME / "state.json"
SEEN_MD = DATA_HOME / "seen.md"
HUMAN_WORLD_MD = DATA_HOME / "human-world.md"   # 人格札记：她每次值班后写一句，随时间沉淀
OUT_DIR = DATA_HOME / "out"                # 每轮报告
LOG_DIR = DATA_HOME / "logs"               # 每轮日志
ENV_FILE = DATA_HOME / ".env"              # DeepSeek Key（导出时默认不含）
QR_PATH = DATA_HOME / "login-qr.png"
DUTY_HOME = DATA_HOME                      # 旧名字，保留给已有调用方

# ── DSH 相关（属于本机，不归面板管） ──────────────────────────
DSH_HOME = Path(os.environ.get("DSH_HOME") or (Path.home() / ".dsh"))
CREDS_YAML = DSH_HOME / ".credentials.yaml"
PATCH_YML = DSH_HOME / "profiles" / "desktop" / "cordis.patch.yml"
BILI_CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) / "bili-cli"

# 老版本把数据写在仓库里 / DSH 目录里，启动时搬一次
LEGACY_DATA_DIRS = [
    PROJECT_ROOT / "runtime" / "duty",
    DSH_HOME / "bili-duty",
]


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
    for p in (DATA_HOME, WORKSPACE, OUT_DIR, LOG_DIR):
        p.mkdir(parents=True, exist_ok=True)
