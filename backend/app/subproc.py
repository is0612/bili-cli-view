# -*- coding: utf-8 -*-
"""跨事件循环的子进程调用。

面板每点一次按钮都要起一个 `bili` 子进程，但 Windows 上的事件循环分两种：

- ProactorEventLoop（默认）：`asyncio.create_subprocess_exec` 可以用；
- SelectorEventLoop：**不支持**子进程，`create_subprocess_exec` 直接抛
  `NotImplementedError`（消息还是空的），于是所有 bili 调用都变成
  `code=125, stderr=""`，面板看起来像「命令全挂了」。

坑在于 uvicorn 只要开了 `--reload`（或 `--workers`），就会把 Windows 上的
循环换成 Selector —— 代码本身完全正常，是运行方式把它弄坏的。

所以这里统一走「线程里跑阻塞版 subprocess.run」：哪种循环下都成立，
代价只是每次调用占一个工作线程（这个面板的并发量完全够）。
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import time
from typing import Any

# 面板可能用 pythonw 起（没有控制台），子进程再起控制台程序会新开黑窗户
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _run_blocking(
    argv: list[str],
    cwd: str | None,
    env: dict[str, str] | None,
    timeout: float,
    creationflags: int,
    startupinfo: Any,
    merge_stderr: bool,
) -> dict[str, Any]:
    """阻塞地跑一个子进程，把「正常退出 / 超时 / 找不到 / 其他异常」都收成一个 dict。"""
    t0 = time.time()

    def done(**kwargs: Any) -> dict[str, Any]:
        out = {
            "code": None, "out": b"", "err": b"", "timeout": False, "error": None,
            "elapsed": round(time.time() - t0, 2),
        }
        out.update(kwargs)
        return out

    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        return done(
            code=proc.returncode,
            out=proc.stdout or b"",
            err=b"" if merge_stderr else (proc.stderr or b""),
        )
    except subprocess.TimeoutExpired as exc:
        # subprocess.run 超时会先 kill 再抛，这里只有已经收到的部分输出
        return done(
            code=124,
            out=exc.output or b"",
            err=b"" if merge_stderr else (exc.stderr or b""),
            timeout=True,
        )
    except FileNotFoundError:
        return done(code=127, error="not_found")
    except Exception as exc:  # noqa: BLE001 - 起进程失败的原因五花八门，原样带回去
        return done(code=125, error=f"{type(exc).__name__}: {exc}")


async def run_capture(
    argv: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 240.0,
    creationflags: int = 0,
    startupinfo: Any = None,
    merge_stderr: bool = False,
) -> dict[str, Any]:
    """跑子进程并返回 {code, out, err, timeout, error, elapsed}。

    `out` / `err` 是原始 bytes，由调用方决定怎么解码；`error` 为 None 表示进程起得来
    （返回码可能非 0，那是业务错误，不是调用失败）。
    """
    return await asyncio.to_thread(
        _run_blocking, argv, cwd, env, timeout, creationflags, startupinfo, merge_stderr
    )
