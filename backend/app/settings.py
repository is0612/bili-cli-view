# -*- coding: utf-8 -*-
"""人设 / 工作区 / API Key 的读写 —— 面板上那三个输入框落到哪儿，全在这里。

原则和内建数据一样：**写进 DATA_HOME，不往仓库、不往 DSH 全局配置里塞**。

  AGENTS.md   人设正文，写在「工作区」目录（默认 DATA_HOME/workspace）
  .env        DeepSeek API Key（面板自己给值班子进程用，不 setx、不改用户环境变量）
  config.json workspace 字段（值日/面板共用一份）
  cordis.patch.yml  仅在你勾选「同步到 DSH 插件」时才写 —— 那是本机全局配置
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .paths import CFG_JSON, DATA_HOME, ENV_FILE, PATCH_YML, WORKSPACE


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return default


def mask(secret: str) -> str:
    if not secret:
        return ""
    return f"{secret[:7]}…{secret[-4:]}" if len(secret) > 14 else "***"


def _env_key() -> str:
    """面板自己存的 key（DATA_HOME/.env）。"""
    m = re.search(r"^DEEPSEEK_API_KEY\s*=\s*(\S+)", read_text(ENV_FILE), re.MULTILINE)
    return m.group(1) if m else ""


def _set_env_key(key: str) -> bool:
    try:
        DATA_HOME.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text(f"DEEPSEEK_API_KEY={key}\n", encoding="utf-8")
        try:                                   # 只有本用户能读，Windows 上不支持就算了
            ENV_FILE.chmod(0o600)
        except OSError:
            pass
        return True
    except OSError:
        return False


def _patch_workspace_in_yaml(workspace: str) -> bool:
    """把 cordis.patch.yml 里 bili-scroll 那段的 workspace 换掉（找不到就插在 config: 后）。"""
    text = read_text(PATCH_YML)
    if not text:
        return False
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if re.match(r"^\s*-\s*id:\s*bili-scroll\s*$", ln)), None)
    if start is None:
        return False
    end = next((j for j in range(start + 1, len(lines))
                if re.match(r"^\s*-\s*id:", lines[j])), len(lines))
    indent = "    "
    value = "workspace: '" + workspace.replace("'", "''") + "'"
    for j in range(start, end):
        if re.match(r"^\s+workspace:", lines[j]):
            lines[j] = indent + value
            PATCH_YML.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
    for j in range(start, end):
        if re.match(r"^\s+config:\s*$", lines[j]):
            lines.insert(j + 1, indent + value)
            PATCH_YML.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
    return False


def state() -> dict[str, Any]:
    cfg = read_json(CFG_JSON, {})
    workspace = str(cfg.get("workspace") or "").strip()
    base = Path(workspace) if workspace else WORKSPACE
    agents_path = base / "AGENTS.md"
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    key = env_key or _env_key()
    return {
        "workspace": workspace,
        "workspace_default": str(WORKSPACE),
        "agents_path": str(agents_path),
        "agents_md": read_text(agents_path),
        "api_key_set": bool(key),
        "api_key_mask": mask(key),
        "api_key_in_env": bool(env_key),
        "api_key_source": "环境变量" if env_key else ("数据目录 .env" if key else ""),
        "duty_home": str(DATA_HOME),
        "data_home": str(DATA_HOME),
    }


def save(workspace: str | None, agents_md: str | None, api_key: str | None,
         sync_plugin: bool = False) -> list[str]:
    notes: list[str] = []
    workspace = (workspace or "").strip()

    if workspace:
        Path(workspace).mkdir(parents=True, exist_ok=True)
        cfg = read_json(CFG_JSON, {})
        cfg["workspace"] = workspace
        try:
            CFG_JSON.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            notes.append("已记下工作区")
        except OSError as exc:
            notes.append(f"config.json 写失败：{exc}")
        if sync_plugin:
            notes.append("已同步 DSH 插件配置" if _patch_workspace_in_yaml(workspace)
                         else "DSH 配置里没找到 bili-scroll 段，未同步")

    if agents_md is not None:
        target = Path(workspace or WORKSPACE) / "AGENTS.md"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(agents_md, encoding="utf-8")
            notes.append(f"已写 {target}")
        except OSError as exc:
            notes.append(f"AGENTS.md 写失败：{exc}")

    if api_key:
        if not api_key.startswith("sk-"):
            notes.append("⚠️ 这串不像 DeepSeek 的 key（应以 sk- 开头）")
        os.environ["DEEPSEEK_API_KEY"] = api_key
        notes.append("Key 已存进数据目录（.env），只给面板起的子进程用" if _set_env_key(api_key)
                     else ".env 写失败，检查数据目录权限")

    return notes
