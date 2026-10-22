# -*- coding: utf-8 -*-
"""我的数据：从哪来（搬老数据）、怎么带走（导出 zip）、怎么换人（清空 / 导入）。

一条原则：**仓库里只放程序，DATA_HOME 里只放我的东西**。
所以「把文件夹发给别人」永远不会带上你的设定和历史，而「换台电脑」只需要把这份 zip 带过去。
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import (
    AGENTS_MD,
    APPDATA_HOME,
    CFG_JSON,
    DATA_HOME,
    ENV_FILE,
    LEGACY_DATA_DIRS,
    OUT_DIR,
    PORTABLE_HOME,
    PROJECT_ROOT,
    SEEN_MD,
    WORKSPACE,
    ensure_dirs,
)

# 导出时默认排除：密钥、二维码、日志里的临时产物
SKIP_NAMES = {"login-qr.png", "__pycache__"}
SECRET_NAMES = {ENV_FILE.name}


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _free_path(base: Path) -> Path:
    """同一秒里连续操作会撞名（reset 完马上 import），撞了就往后加 -2、-3。"""
    if not base.exists():
        return base
    for i in range(2, 1000):
        cand = base.with_name(f"{base.name}-{i}")
        if not cand.exists():
            return cand
    raise RuntimeError(f"备份目录名用完了：{base}")


def _backup_dir() -> Path:
    return _free_path(DATA_HOME.with_name(f"{DATA_HOME.name}.bak-{_stamp()}"))


# ───────────────────────── 老数据搬家 ─────────────────────────


def _has_data(folder: Path) -> bool:
    """这个老目录里还有没有「真数据」——空壳目录不算。"""
    if not folder.exists():
        return False
    if any((folder / n).exists() for n in ("config.json", "state.json", "seen.md")):
        return True
    for sub in ("out", "logs"):
        if any(p.is_file() for p in (folder / sub).glob("*")):
            return True
    return False


def _adopt_appdata(notes: list[str]) -> bool:
    """便携模式第一次启动：把 %APPDATA%\\bili-desk 里的旧数据搬进 data/。

    只在「数据目录就是程序目录下的 data/」且那边还空着的时候动手，
    `BILI_DESK_HOME` 覆盖的情况一律不碰，免得把用户指定的目录搞乱。
    """
    if DATA_HOME != PORTABLE_HOME:
        return False
    if DATA_HOME == APPDATA_HOME or not _has_data(APPDATA_HOME):
        return False

    moved: list[str] = []
    for name in ("config.json", "state.json", "seen.md", "menu.json", ".env"):
        src = APPDATA_HOME / name
        if src.exists() and not (DATA_HOME / name).exists():
            try:
                shutil.move(str(src), str(DATA_HOME / name))
                moved.append(name)
            except OSError:
                pass
    for sub in ("workspace", "out", "logs"):
        src, dst = APPDATA_HOME / sub, DATA_HOME / sub
        if not src.is_dir():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file() and not (dst / f.name).exists():
                try:
                    shutil.move(str(f), str(dst / f.name))
                    moved.append(f"{sub}/{f.name}")
                except OSError:
                    pass
    if moved:
        _prune_empty(APPDATA_HOME)
        notes.append(
            f"已把旧数据从 {APPDATA_HOME} 搬进 {DATA_HOME}（{len(moved)} 个文件），"
            "以后这份数据跟着程序目录走"
        )
        return True
    return False


def migrate() -> list[str]:
    """把老版本散落在仓库 / DSH 目录里的数据搬进 DATA_HOME。

    只搬一次：DATA_HOME 里已经有 config.json 或 seen.md 就认为搬过了，直接返回。
    """
    notes: list[str] = []
    DATA_HOME.mkdir(parents=True, exist_ok=True)
    if CFG_JSON.exists() or SEEN_MD.exists():
        return notes

    # 便携模式：数据目录变成了程序目录下的 data/，第一次启动把系统用户目录里的旧数据搬过来
    migrated = _adopt_appdata(notes)
    if migrated:
        return notes

    for legacy in LEGACY_DATA_DIRS:
        if not _has_data(legacy):
            continue
        moved: list[str] = []
        for name in ("config.json", "state.json", "seen.md"):
            src = legacy / name
            if src.exists() and not (DATA_HOME / name).exists():
                shutil.move(str(src), str(DATA_HOME / name))
                moved.append(name)
        for sub in ("out", "logs"):
            src, dst = legacy / sub, DATA_HOME / sub
            if not src.exists():
                continue
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file() and not (dst / f.name).exists():
                    shutil.move(str(f), str(dst / f.name))
            moved.append(f"{sub}/")
        if moved:
            notes.append(f"旧数据已从 {legacy} 搬进 {DATA_HOME}")
            _prune_empty(legacy)
            break

    # 更老的版本把 AGENTS.md 写在仓库根目录：那是最典型的「数据混在代码里」
    legacy_agents = PROJECT_ROOT / "AGENTS.md"
    if legacy_agents.exists() and not AGENTS_MD.exists():
        AGENTS_MD.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy_agents), str(AGENTS_MD))
        notes.append(f"AGENTS.md 已从仓库根目录搬进 {AGENTS_MD}")
    return notes


def _prune_empty(folder: Path) -> None:
    """搬完把空目录收掉，免得下次启动还提示"旧数据还在"。"""
    for sub in ("out", "logs"):
        try:
            (folder / sub).rmdir()
        except OSError:
            pass
    try:
        folder.rmdir()
    except OSError:
        pass


# ───────────────────────── 现状 ─────────────────────────


def info() -> dict[str, Any]:
    files = 0
    size = 0
    if DATA_HOME.exists():
        for p in DATA_HOME.rglob("*"):
            if p.is_file():
                files += 1
                try:
                    size += p.stat().st_size
                except OSError:
                    pass
    reports = len(list(OUT_DIR.glob("*.md"))) if OUT_DIR.exists() else 0
    return {
        "dir": str(DATA_HOME),
        "env_override": bool(os.environ.get("BILI_DESK_HOME")),
        "exists": DATA_HOME.exists(),
        "files": files,
        "bytes": size,
        "workspace": str(WORKSPACE),
        "agents_md": str(AGENTS_MD),
        "has_persona": AGENTS_MD.exists(),
        "has_config": CFG_JSON.exists(),
        "reports": reports,
        "legacy": [str(p) for p in LEGACY_DATA_DIRS if _has_data(p)],
    }


# ───────────────────────── 导出 / 导入 / 清空 ─────────────────────────


def export_zip(include_secrets: bool = False) -> bytes:
    """把 DATA_HOME 压成一个 zip。默认不含 API Key（.env）。"""
    skip = set(SKIP_NAMES) | (set() if include_secrets else set(SECRET_NAMES))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if DATA_HOME.exists():
            for path in sorted(DATA_HOME.rglob("*")):
                rel = path.relative_to(DATA_HOME)
                if path.is_dir() or rel.suffix == ".pyc":
                    continue
                if any(part in skip for part in rel.parts):
                    continue
                zf.write(path, rel.as_posix())
        zf.writestr(
            "README-导出说明.txt",
            "\n".join([
                "bili-desk 数据备份",
                f"导出时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
                f"来源目录：{DATA_HOME}",
                "包含：设定（config.json）、判重表（seen.md）、报告（out/）、日志（logs/）、人设（workspace/AGENTS.md）",
                f"API Key：{'已包含（.env）' if include_secrets else '未包含'}",
                "",
                "换台电脑：把本文件解压到新机器的 bili-desk 数据目录，或在面板「设置 → 导入备份」里选择它。",
            ]) + "\n",
        )
    return buf.getvalue()


def import_zip(data: bytes) -> list[str]:
    """用一份备份替换当前数据。旧数据不会删，会改名留成 .bak-时间戳。"""
    if not data:
        raise ValueError("上传的文件是空的")

    tmp = DATA_HOME.parent / f".bili-desk-import-{_stamp()}"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                pure = Path(name)
                if pure.is_absolute() or ".." in pure.parts:
                    raise ValueError(f"zip 里有可疑路径：{name}")
            zf.extractall(tmp)

        # 判断它是不是 bili-desk 的备份：应该有 config.json / seen.md / workspace 之一
        looks_like = any((tmp / n).exists() for n in ("config.json", "seen.md", "workspace"))
        if not looks_like:
            raise ValueError("这个 zip 里没有 bili-desk 的数据（找不到 config.json / seen.md）")

        backup = None
        if DATA_HOME.exists() and any(DATA_HOME.iterdir()):
            backup = _backup_dir()
            DATA_HOME.rename(backup)

        if DATA_HOME.exists():
            shutil.rmtree(DATA_HOME, ignore_errors=True)
        shutil.move(str(tmp), str(DATA_HOME))
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    finally:
        ensure_dirs()

    notes = [f"已导入到 {DATA_HOME}"]
    if backup:
        notes.append(f"原来的数据留了一份备份：{backup}")
    if not ENV_FILE.exists():
        notes.append("备份里没有 API Key（导出时没勾「连 API Key」），要用自动值班的话在设置里再填一次")
    notes.append("刷新一下页面就能看到新的设定 / 历史")
    return notes


def reset() -> list[str]:
    """清空（换人用）：当前数据改名留档，然后建一个空的。"""
    if not DATA_HOME.exists() or not any(DATA_HOME.iterdir()):
        ensure_dirs()
        return ["数据目录本来就是空的"]
    backup = _backup_dir()
    DATA_HOME.rename(backup)
    ensure_dirs()
    return [f"已清空，原数据备份在 {backup}", "重启一次面板（或刷新页面）即可从头开始"]


def open_dir() -> None:
    ensure_dirs()
    if os.name == "nt":
        os.startfile(str(DATA_HOME))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(DATA_HOME)])
    else:
        subprocess.Popen(["xdg-open", str(DATA_HOME)])
