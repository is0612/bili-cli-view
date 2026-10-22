# -*- coding: utf-8 -*-
"""FastAPI 后端：把 bili CLI 变成一组 HTTP 接口，供 Vue 前端调用。"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from . import agent, duty, media, schema_catalog, selfcheck, settings
from .catalog import CATALOG
from .paths import CREDS_YAML, PROJECT_ROOT, QR_PATH, bili_bin, ensure_dirs
from .runner import bili_json, run_bili


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()
    task = asyncio.create_task(agent.scheduler_loop())   # 谷时定时器
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="bili-desk", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunBody(BaseModel):
    argv: list[str]


class SettingsBody(BaseModel):
    workspace: str | None = None
    agents_md: str | None = None
    api_key: str | None = None
    sync_plugin: bool = True


# ───────────────────────── 基础信息 ─────────────────────────


@app.get("/api/ping")
async def get_ping() -> Any:
    """给脚本用的轻量探活：不碰 bili，立刻返回。"""
    return {"ok": True}


SPECIAL_GROUPS: list[dict[str, Any]] = [
    {"group": "刷B站", "items": [
        {"id": "duty.settings", "label": "值班设置", "argv": [], "kind": "duty"},
        {"id": "duty.dynamic", "label": "发动态", "argv": [], "kind": "dynamic"},
        {"id": "duty.seen", "label": "她看过什么", "argv": [], "kind": "seen"},
    ]},
    {"group": "面板", "items": [
        {"id": "selfcheck", "label": "升级自检", "argv": [], "kind": "selfcheck"},
    ]},
]


@app.get("/api/catalog")
async def get_catalog() -> Any:
    """侧栏命令表：以 `bili schema` 为准（新增/改名自动跟上），失败才退回手写清单。"""
    groups, version, from_schema = await schema_catalog.build()
    if not from_schema:
        return {"groups": CATALOG, "source": "static"}
    return {"groups": SPECIAL_GROUPS + groups, "source": "schema", "version": version}


@app.get("/api/meta")
async def get_meta() -> Any:
    ver_json = await bili_json(["--version"], timeout=30)
    auth_json = await bili_json(["auth", "status"], timeout=40)
    owner_json = await bili_json(["owner", "show"], timeout=40)

    auth_data = (auth_json or {}).get("data") or {}
    return {
        "version": ((ver_json or {}).get("data") or {}).get("version"),
        "auth": {
            "ok": bool((auth_json or {}).get("ok")),
            "user": auth_data.get("user"),
            "error": (auth_json or {}).get("error"),
        },
        "owner": (((owner_json or {}).get("data") or {}).get("owner")),
        "bili": bili_bin(),
    }


# ───────────────────────── 执行命令 ─────────────────────────


@app.post("/api/run")
async def post_run(body: RunBody) -> Any:
    argv = [a for a in body.argv if isinstance(a, str) and a != ""]
    if not argv:
        raise HTTPException(status_code=400, detail="空命令")
    return await run_bili(argv)


# ───────────────────────── 登录 ─────────────────────────


@app.post("/api/login")
async def post_login() -> Any:
    ensure_dirs()
    return await run_bili(["auth", "login", "--qr-out", str(QR_PATH)])


@app.get("/api/qr.png")
async def get_qr() -> Response:
    if not QR_PATH.exists():
        raise HTTPException(status_code=404, detail="还没有二维码")
    return FileResponse(str(QR_PATH), media_type="image/png",
                        headers={"Cache-Control": "no-store"})


@app.post("/api/cancel-login")
async def cancel_login() -> Any:
    """把待扫码状态挪走 —— 否则 `auth status` 会一直回「待扫码」，看起来像掉登录。"""
    pending = Path(CREDS_YAML).parent / "bili-cli" / "pending_login.json"
    moved = None
    if pending.exists():
        bak = pending.with_suffix(".json.bak")
        try:
            pending.replace(bak)
            moved = str(bak)
        except OSError:
            pass
    status = await bili_json(["auth", "status"], timeout=40)
    return {"moved": moved, "status": status}


@app.get("/api/selfcheck")
async def get_selfcheck() -> Any:
    return await selfcheck.run()


# ───────────────────────── 自动值班（bili-cli 版） ─────────────────────────


@app.get("/api/agent")
async def get_agent() -> Any:
    return agent.status()


@app.post("/api/agent/save")
async def post_agent_save(body: dict[str, Any]) -> Any:
    notes = agent.save(body)
    return {"ok": True, "notes": notes, "agent": agent.status()}


@app.post("/api/agent/reset")
async def post_agent_reset() -> Any:
    return {"ok": True, **agent.reset_today()}


@app.post("/api/agent/run")
async def post_agent_run() -> Any:
    return await agent.run_round("manual")


@app.get("/api/agent/report")
async def get_agent_report(day: str | None = None) -> Any:
    return agent.report(day)


@app.get("/api/agent/seen")
async def get_agent_seen() -> Any:
    return agent.seen()


# ───────────────────────── 刷B站值班（旧插件） ─────────────────────────


@app.get("/api/duty")
async def get_duty() -> Any:
    return duty.snapshot()


@app.post("/api/duty")
async def post_duty(body: dict[str, Any]) -> Any:
    patch = {k: v for k, v in body.items() if k in duty.SCALARS or k == "keywords"}
    if not patch:
        raise HTTPException(status_code=400, detail="没有可写字段")
    notes = duty.save(patch)
    return {"ok": True, "notes": notes, "duty": duty.snapshot()}


@app.post("/api/duty/reset")
async def post_duty_reset() -> Any:
    return {"ok": True, **duty.reset_today()}


@app.get("/api/duty/report")
async def get_duty_report(day: str | None = None) -> Any:
    return duty.report(day)


@app.get("/api/duty/seen")
async def get_duty_seen() -> Any:
    return duty.seen()


class DynamicBody(BaseModel):
    text: str
    images: list[str] = []
    at: list[str] = []
    dry_run: bool = True


@app.post("/api/duty/dynamic")
async def post_duty_dynamic(body: DynamicBody) -> Any:
    """代她发图文动态：先 dry-run 预览，确认了再真发。"""
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="动态正文不能为空")
    argv = ["dynamic", "post", text]
    for image in body.images:
        if image.strip():
            argv += ["--image", image.strip()]
    for name in body.at:
        if name.strip():
            argv += ["--at", name.strip()]
    if body.dry_run:
        argv.append("--dry-run")
    return await run_bili(argv)


# ───────────────────────── 人设 / Key ─────────────────────────


@app.get("/api/settings")
async def get_settings() -> Any:
    return settings.state()

@app.post("/api/settings")
async def post_settings(body: SettingsBody) -> Any:
    notes = settings.save(body.workspace, body.agents_md, body.api_key, body.sync_plugin)
    return {"ok": True, "notes": notes, "state": settings.state()}


# ───────────────────────── 图片 ─────────────────────────


@app.get("/api/cover")
async def get_cover(bvid: str = Query(...)) -> Response:
    got = await run_in_threadpool(media.cover_bytes, bvid)
    if not got:
        raise HTTPException(status_code=404, detail="没有封面")
    data, ctype = got
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "max-age=600"})


@app.get("/api/img")
async def get_img(p: str = Query(...)) -> Response:
    if not media.allowed_local(p):
        raise HTTPException(status_code=403, detail="不允许的路径")
    path = Path(p)
    ctype = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return Response(content=path.read_bytes(), media_type=ctype)


@app.get("/api/proxy")
async def get_proxy(u: str = Query(...)) -> Response:
    if not u.startswith("http"):
        raise HTTPException(status_code=400, detail="只支持 http(s) 图片地址")
    try:
        data, ctype = await run_in_threadpool(media.fetch_remote, u)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"取图失败：{exc}") from exc
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "max-age=600"})


# ───────────────────────── 生产模式：直接喂 dist ─────────────────────────

DIST = PROJECT_ROOT / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="static")
