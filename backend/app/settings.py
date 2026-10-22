# -*- coding: utf-8 -*-
"""人设 / 工作区 / API Key 的读写 —— 面板上那三个输入框落到哪儿，全在这里。

三处目标：
  config.json       插件的配置（workspace 字段）
  cordis.patch.yml  DSH profile 的用户层（再写一份，插件读哪一层都一致）
  AGENTS.md         人设正文（写进“工作区”目录）
  .credentials.yaml + 用户环境变量   DeepSeek API Key
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .paths import CFG_JSON, CREDS_YAML, DUTY_HOME, PATCH_YML, PROJECT_ROOT


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


def _creds_key() -> str:
    m = re.search(r"DEEPSEEK_API_KEY:\s*(\S+)", read_text(CREDS_YAML))
    return m.group(1) if m else ""


def _set_creds_key(key: str) -> bool:
    text = read_text(CREDS_YAML)
    if not text:
        return False
    new, n = re.subn(r"(DEEPSEEK_API_KEY:\s*)\S+", lambda m: m.group(1) + key, text, count=1)
    if n == 0:
        new = text.rstrip() + ("\n  DEEPSEEK_API_KEY: " + key + "\n"
                               if "refs:" in text else "\nrefs:\n  DEEPSEEK_API_KEY: " + key + "\n")
    try:
        CREDS_YAML.write_text(new, encoding="utf-8")
        return True
    except OSError:
        return False


def _set_user_env(name: str, value: str) -> bool:
    try:
        subprocess.run(["setx", name, value], capture_output=True, timeout=20,
                       creationflags=0x08000000 if os.name == "nt" else 0)   # 不弹黑窗
        return True
    except Exception:  # noqa: BLE001
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
    base = Path(workspace) if workspace else PROJECT_ROOT
    agents_path = base / "AGENTS.md"
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    cred_key = _creds_key()
    return {
        "workspace": workspace,
        "workspace_default": str(PROJECT_ROOT),
        "agents_path": str(agents_path),
        "agents_md": read_text(agents_path),
        "api_key_set": bool(env_key or cred_key),
        "api_key_mask": mask(env_key or cred_key),
        "api_key_in_env": bool(env_key),
        "duty_home": str(DUTY_HOME),
    }


def save(workspace: str | None, agents_md: str | None, api_key: str | None,
         sync_plugin: bool = True) -> list[str]:
    notes: list[str] = []
    workspace = (workspace or "").strip()

    if workspace:
        Path(workspace).mkdir(parents=True, exist_ok=True)
        cfg = read_json(CFG_JSON, {})
        cfg["workspace"] = workspace
        try:
            CFG_JSON.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            notes.append("已写 config.json 的 workspace")
        except OSError as exc:
            notes.append(f"config.json 写失败：{exc}")
        if sync_plugin:
            notes.append("已同步 cordis.patch.yml" if _patch_workspace_in_yaml(workspace)
                         else "cordis.patch.yml 里没找到 bili-scroll 段，未同步")

    if agents_md is not None:
        target = Path(workspace or PROJECT_ROOT) / "AGENTS.md"
        try:
            target.write_text(agents_md, encoding="utf-8")
            notes.append(f"已写 {target}")
        except OSError as exc:
            notes.append(f"AGENTS.md 写失败：{exc}")

    if api_key:
        if not api_key.startswith("sk-"):
            notes.append("⚠️ 这串不像 DeepSeek 的 key（应以 sk- 开头）")
        os.environ["DEEPSEEK_API_KEY"] = api_key
        notes.append("已 setx 到用户环境变量" if _set_user_env("DEEPSEEK_API_KEY", api_key)
                     else "setx 失败，可用手动方式设置")
        notes.append("已更新 .credentials.yaml" if _set_creds_key(api_key)
                     else ".credentials.yaml 未更新")
        notes.append("⚠️ 重启一次 DSH，子进程才会继承新 key")

    return notes
