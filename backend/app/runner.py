# -*- coding: utf-8 -*-
"""把 bili CLI 包成一个无状态的调用器：一次调用 = 一个进程 + 一段 JSON。"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from .paths import bili_bin


async def run_bili(argv: list[str], timeout: float = 240.0) -> dict[str, Any]:
    """执行 `bili <argv...>`，把 stdout、解析出的 JSON、耗时一起返回。"""
    if not argv:
        return {"code": 2, "json": None, "stdout": "", "stderr": "空命令", "elapsed": 0, "argv": argv}

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    exe = bili_bin()
    t0 = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            exe, *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"code": 124, "json": None, "stdout": "", "stderr": "命令超时",
                    "elapsed": round(time.time() - t0, 2), "argv": argv}
    except FileNotFoundError:
        return {"code": 127, "json": None, "stdout": "",
                "stderr": f"找不到 bili 可执行文件（{exe}）", "elapsed": 0, "argv": argv}
    except Exception as exc:  # noqa: BLE001
        return {"code": 125, "json": None, "stdout": "", "stderr": str(exc),
                "elapsed": round(time.time() - t0, 2), "argv": argv}

    stdout = out_b.decode("utf-8", "replace").strip()
    stderr = err_b.decode("utf-8", "replace").strip()
    try:
        parsed = json.loads(stdout)
    except Exception:  # noqa: BLE001
        parsed = None
    return {
        "code": proc.returncode,
        "json": parsed,
        "stdout": stdout[-20000:],
        "stderr": stderr[-4000:],
        "elapsed": round(time.time() - t0, 2),
        "argv": argv,
    }


async def bili_json(argv: list[str], timeout: float = 60.0) -> dict[str, Any] | None:
    res = await run_bili(argv, timeout=timeout)
    return res.get("json")
