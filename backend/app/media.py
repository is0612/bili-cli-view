# -*- coding: utf-8 -*-
"""封面 / 图片：B站的图有防盗链，必须带 Referer 代取；顺手做内存缓存。"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .netenv import system_proxy_usable
from .paths import BILI_CONFIG_DIR, DATA_HOME, PROJECT_ROOT

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

_pic_cache: dict[str, str] = {}
_img_cache: dict[str, tuple[bytes, str]] = {}

# 系统代理不可用（代理软件没开）时强制直连 —— 否则封面上全是 502
_OPENER_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_OPENER_DEFAULT = urllib.request.build_opener()


def _open(req: urllib.request.Request, timeout: float):
    opener = _OPENER_DEFAULT if system_proxy_usable() else _OPENER_DIRECT
    return opener.open(req, timeout=timeout)


def cover_url(bvid: str) -> str | None:
    """bvid -> 封面地址（走 B站公开 view 接口，带缓存）。"""
    if bvid in _pic_cache:
        return _pic_cache[bvid]
    pic = None
    try:
        req = urllib.request.Request(
            "https://api.bilibili.com/x/web-interface/view?bvid=" + urllib.parse.quote(bvid),
            headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
        )
        with _open(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        if data.get("code") == 0:
            pic = (data.get("data") or {}).get("pic")
    except Exception:  # noqa: BLE001
        pic = None
    if pic and pic.startswith("//"):
        pic = "https:" + pic
    if pic:
        if len(_pic_cache) > 800:
            _pic_cache.clear()
        _pic_cache[bvid] = pic
    return pic


def fetch_remote(url: str, referer: str = "https://www.bilibili.com/") -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": referer,
        "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
    })
    with _open(req, timeout=20) as resp:
        return resp.read(), resp.headers.get("Content-Type", "image/jpeg")


def cover_bytes(bvid: str) -> tuple[bytes, str] | None:
    cached = _img_cache.get(bvid)
    if cached:
        return cached
    pic = cover_url(bvid)
    if not pic:
        return None
    data, ctype = fetch_remote(pic)
    if len(_img_cache) > 300:
        _img_cache.clear()
    _img_cache[bvid] = (data, ctype)
    return data, ctype


def allowed_local(path: str) -> bool:
    """只允许读项目目录 / bili-cli 配置目录下的图片（防路径穿越）。"""
    from pathlib import Path

    try:
        target = Path(path).resolve()
    except Exception:  # noqa: BLE001
        return False
    roots = [PROJECT_ROOT.resolve(), DATA_HOME.resolve(), BILI_CONFIG_DIR.resolve(),
             (BILI_CONFIG_DIR / "frames").resolve()]
    return any(str(target).startswith(str(r)) for r in roots) and target.is_file()
