# -*- coding: utf-8 -*-
"""子进程的环境变量：主要处理「代理残留」这个坑。

现象：机器上开着代理软件时，环境变量里会留着 `http_proxy=http://127.0.0.1:54454`。
代理一关，端口就不监听了，但变量还在。`bili` 子进程继承它，于是所有请求都往
死代理上撞 —— bili 抛出 `ProxyError: 502 Bad Gateway`，面板上看起来就像
「生成二维码 502 了」，其实跟二维码一点关系都没有。

做法：起子进程前先探一下代理端口，连不上就把代理变量摘掉让它直连；
代理真在跑就原样保留，尊重用户设置。探测结果缓存 30 秒，不拖慢每次调用
（B站 全在国内，直连通常比走代理还快）。
"""
from __future__ import annotations

import os
import socket
import time
import urllib.request
from urllib.parse import urlsplit

PROXY_KEYS = (
    "http_proxy", "https_proxy", "all_proxy",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
)
PROBE_TTL = 30.0
_CONNECT_TIMEOUT = 0.4        # 本地代理端口，0.4 秒连不上基本就是没开
_TUNNEL_TIMEOUT = 1.5         # 再问一句「能不能给我开条到 B站 的隧道」

# 光看端口通不通不够：端口活着也可能是个 SOCKS 口、或者代理自己连不上上游
# （那正是 `ProxyError: 502 Bad Gateway` 的来源）。所以再发一次 CONNECT 探针，
# 代理真能建立到 B站 的隧道才认为可用。
_PROBE_TARGET = ("api.bilibili.com", 443)
_PROBE_REQUEST = (
    f"CONNECT {_PROBE_TARGET[0]}:{_PROBE_TARGET[1]} HTTP/1.1\r\n"
    f"Host: {_PROBE_TARGET[0]}:{_PROBE_TARGET[1]}\r\n"
    "Proxy-Connection: keep-alive\r\n\r\n"
).encode()

_cache: dict[str, tuple[bool, float]] = {}
_warned = False


def _host_port(value: str) -> tuple[str, int] | None:
    """把 `http://user:pass@127.0.0.1:54454` 这种值拆成 (host, port)。"""
    raw = (value or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "http://" + raw
    try:
        parts = urlsplit(raw)
        host = parts.hostname
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        return None
    return (host, port) if host else None


def _probe(hp: tuple[str, int]) -> bool:
    """代理到底能不能用：端口通 + 愿意为我们开一条到 B站 的隧道。"""
    try:
        with socket.create_connection(hp, timeout=_CONNECT_TIMEOUT):
            pass
    except OSError:
        return False          # 代理软件没开，最常见的那个情况

    try:
        with socket.create_connection(hp, timeout=_CONNECT_TIMEOUT) as sock:
            sock.sendall(_PROBE_REQUEST)
            sock.settimeout(_TUNNEL_TIMEOUT)
            head = sock.recv(128)
    except OSError:
        return False          # 不是 HTTP 代理（比如 SOCKS 口），bili 用不了

    status = head.split(b"\r\n", 1)[0]
    # 200 = 隧道通了；407 = 要认证但代理本身是好的。5xx = 代理自己连不上上游，不能信
    return status.startswith(b"HTTP/1.") and (b" 200" in status or b" 407" in status)


def proxy_alive(value: str) -> bool:
    """代理是否真的可用（带 30 秒缓存）。"""
    hp = _host_port(value)
    if not hp:
        return False
    key = f"{hp[0]}:{hp[1]}"
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[1] < PROBE_TTL:
        return cached[0]
    ok = _probe(hp)
    _cache[key] = (ok, now)
    return ok


def system_proxy_usable() -> bool:
    """系统里配置的代理是否可用；压根没配代理也算 True（本来就直连）。

    给 urllib 用：代理是死的而我们又照默认走它，封面图、抽帧全都会 502。
    """
    try:
        proxies = urllib.request.getproxies()
    except Exception:  # noqa: BLE001 - 读注册表失败就当没代理
        return True
    urls = {v for k, v in proxies.items() if k in ("http", "https", "all") and v}
    if not urls:
        return True
    return all(proxy_alive(u) for u in urls)


# ── IPv4 优先 ────────────────────────────────────────────────
# 有些机器 IPv6 是"有地址但不通"的（运营商给了 AAAA，路由却没通）。
# DNS 会把 IPv6 排在前面，`socket.create_connection` 就一个地址一个地址地试，
# 每个都要等满超时 —— 表现是「封面图 / 接口卡住几十秒然后失败」。
# 把 IPv4 排到前面、IPv6 留在后面兜底，连通性和顺序都正常。
_ORIG_GETADDRINFO = socket.getaddrinfo
_ipv4_preferred = False


def _getaddrinfo_ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
    infos = _ORIG_GETADDRINFO(host, port, family, type, proto, flags)
    if family == socket.AF_INET6:
        return infos
    v4 = [i for i in infos if i[0] == socket.AF_INET]
    if not v4:
        return infos
    return v4 + [i for i in infos if i[0] != socket.AF_INET]


def prefer_ipv4() -> None:
    """进程内让 DNS 结果 IPv4 优先（幂等）。"""
    global _ipv4_preferred
    if _ipv4_preferred:
        return
    socket.getaddrinfo = _getaddrinfo_ipv4_first
    _ipv4_preferred = True


def child_env(**extra: str) -> dict[str, str]:
    """给 bili / dsh 子进程用的环境变量副本（不动本进程的环境）。

    `extra` 里的键值会覆盖，值是空串的忽略。
    """
    global _warned
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    dropped: set[str] = set()
    for key in PROXY_KEYS:
        val = env.get(key)
        if val and not proxy_alive(val):
            env.pop(key, None)
            dropped.add(key)

    if dropped and not _warned:
        _warned = True
        # 只提示一次，免得每条命令刷一行
        print(f"[netenv] 系统代理不可用，已对子进程改用直连（忽略 {', '.join(sorted(dropped))}）")

    for k, v in extra.items():
        if v:
            env[k] = v
    return env
