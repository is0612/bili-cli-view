# -*- coding: utf-8 -*-
"""控制面板里暴露的命令清单（80+ 条里的常用集）。

一条 = 一个 bili 调用；params 决定表单长什么样：
  pos=True      → 位置参数（直接跟值）
  flag='--x'    → 选项（值跟在 flag 后面）
  type='bool'   → 勾选框（勾上才出现 flag）
  type='select' → 下拉
write=True 的命令默认带 --dry-run，要真发得手动取消。
"""
from __future__ import annotations

from typing import Any

ZONES = ["all", "anime", "music", "dance", "game", "knowledge", "tech", "sports",
         "car", "life", "food", "animal", "kichiku", "fashion", "ent", "film",
         "original", "rookie"]

VIDEO = {"key": "video_id", "label": "BV号 / 链接", "pos": True, "ph": "BV181Hh6bE27"}


def p(key: str, label: str, pos: bool = False, flag: str | None = None, ptype: str = "text",
      default: str = "", choices: list[str] | None = None, ph: str = "") -> dict[str, Any]:
    return {"key": key, "label": label, "pos": pos, "flag": flag, "type": ptype,
            "default": default, "choices": choices or [], "ph": ph}


CATALOG: list[dict[str, Any]] = [
    {"group": "刷B站", "items": [
        {"id": "duty.settings", "label": "值班设置", "argv": [], "kind": "duty"},
        {"id": "duty.dynamic", "label": "发动态", "argv": [], "kind": "dynamic"},
        {"id": "duty.seen", "label": "她看过什么", "argv": [], "kind": "seen"},
    ]},
    {"group": "账号", "items": [
        {"id": "auth.status", "label": "登录状态", "argv": ["auth", "status"]},
        {"id": "me.show", "label": "我的资料", "argv": ["me", "show"]},
        {"id": "me.stats", "label": "创作数据", "argv": ["me", "stats"]},
        {"id": "owner.show", "label": "当前主人", "argv": ["owner", "show"]},
        {"id": "owner.set", "label": "设置主人", "argv": ["owner", "set"],
         "params": [p("uid", "UID / 昵称", pos=True, ph="12345678")]},
        {"id": "me.favs", "label": "我的收藏夹", "argv": ["me", "favs"]},
    ]},
    {"group": "收件箱", "items": [
        {"id": "feed.inbox", "label": "全部新消息", "argv": ["feed", "inbox"]},
        {"id": "feed.replies", "label": "回复我的", "argv": ["feed", "replies"]},
        {"id": "feed.mentions", "label": "@ 我的", "argv": ["feed", "mentions"]},
        {"id": "feed.likes", "label": "收到的赞", "argv": ["feed", "likes"]},
        {"id": "feed.notifications", "label": "未读数", "argv": ["feed", "notifications"]},
    ]},
    {"group": "发现", "items": [
        {"id": "feed.recommend", "label": "首页推荐", "argv": ["feed", "recommend"],
         "params": [p("n", "条数", flag="-n", ptype="int", default="6")]},
        {"id": "hot.popular", "label": "综合热门", "argv": ["hot", "popular"],
         "params": [p("n", "条数", flag="-n", ptype="int", default="10")]},
        {"id": "hot.rank", "label": "分区排行", "argv": ["hot", "rank"],
         "params": [p("zone", "分区", flag="--zone", ptype="select", default="tech", choices=ZONES),
                    p("limit", "条数", flag="--limit", ptype="int", default="20"),
                    p("unseen", "只看没看过的", flag="--unseen", ptype="bool")]},
        {"id": "hot.search", "label": "热搜", "argv": ["hot", "search"]},
        {"id": "hot.weekly", "label": "每周必看", "argv": ["hot", "weekly"]},
        {"id": "search.video", "label": "搜视频", "argv": ["search", "video"],
         "params": [p("keyword", "关键词", pos=True, ph="DeepSeek"),
                    p("order", "排序", flag="--order", ptype="select", default="views",
                      choices=["default", "views", "new", "danmaku", "favorites", "comments"]),
                    p("size", "每页", flag="--size", ptype="int", default="20")]},
        {"id": "search.user", "label": "搜用户", "argv": ["search", "user"],
         "params": [p("keyword", "关键词", pos=True, ph="老番茄")]},
    ]},
    {"group": "视频", "items": [
        {"id": "video.watch", "label": "看懂视频", "argv": ["video", "watch"],
         "params": [dict(VIDEO), p("maxchars", "正文截断", flag="--max-chars", ptype="int", default="2000")]},
        {"id": "video.info", "label": "视频信息", "argv": ["video", "info"], "params": [dict(VIDEO)]},
        {"id": "video.subtitle", "label": "字幕全文", "argv": ["video", "subtitle"],
         "params": [dict(VIDEO), p("text", "纯文本输出", flag="--text", ptype="bool")]},
        {"id": "video.summary", "label": "AI 总结", "argv": ["video", "summary"], "params": [dict(VIDEO)]},
        {"id": "video.stats", "label": "单稿数据", "argv": ["video", "stats"], "params": [dict(VIDEO)]},
        {"id": "video.frames", "label": "抽帧总览", "argv": ["video", "frames"],
         "params": [dict(VIDEO),
                    p("quality", "画质", flag="-q", ptype="select", default="preview",
                      choices=["preview", "hd"]),
                    p("count", "帧数", flag="-n", ptype="int", default="9")]},
        {"id": "video.relation", "label": "我与视频", "argv": ["video", "relation"], "params": [dict(VIDEO)]},
        {"id": "video.like", "label": "点赞", "argv": ["video", "like"], "write": True, "params": [dict(VIDEO)]},
        {"id": "video.fav", "label": "收藏", "argv": ["video", "fav"], "write": True, "params": [dict(VIDEO)]},
        {"id": "video.coin", "label": "投币", "argv": ["video", "coin"], "write": True,
         "params": [dict(VIDEO), p("coins", "币数", flag="--coins", ptype="select", default="1", choices=["1", "2"])]},
        {"id": "video.triple", "label": "一键三连", "argv": ["video", "triple"], "write": True, "params": [dict(VIDEO)]},
    ]},
    {"group": "互动", "items": [
        {"id": "comment.list", "label": "看评论", "argv": ["comment", "list"],
         "params": [p("target", "BV号 / 链接", pos=True, ph="BV181Hh6bE27"),
                    p("sort", "排序", flag="--sort", ptype="select", default="hot", choices=["hot", "time"]),
                    p("unreplied", "只看没回的", flag="--unreplied", ptype="bool")]},
        {"id": "comment.post", "label": "发评论", "argv": ["comment", "post"], "write": True,
         "params": [p("target", "BV号 / 链接", pos=True),
                    p("text", "正文", pos=True, ph="谢谢！教程下周更新～")]},
        {"id": "dm.list", "label": "私信列表", "argv": ["dm", "list"],
         "params": [p("unread", "只看未读", flag="--unread", ptype="bool")]},
        {"id": "dm.send", "label": "发私信", "argv": ["dm", "send"], "write": True,
         "params": [p("uid", "UID / owner", pos=True, ph="owner"), p("text", "正文", pos=True)]},
    ]},
    {"group": "动态", "items": [
        {"id": "dynamic.list", "label": "动态列表", "argv": ["dynamic", "list"]},
        {"id": "dynamic.post", "label": "发动态", "argv": ["dynamic", "post"], "write": True,
         "params": [p("text", "正文", pos=True)]},
    ]},
    {"group": "数据", "items": [
        {"id": "user.info", "label": "UP 资料", "argv": ["user", "info"],
         "params": [p("uid", "UID / 昵称", pos=True)]},
        {"id": "user.videos", "label": "UP 投稿", "argv": ["user", "videos"],
         "params": [p("uid", "UID / 昵称", pos=True),
                    p("order", "排序", flag="--order", ptype="select", default="views",
                      choices=["views", "favorites", "new"])]},
    ]},
    {"group": "系统", "items": [
        {"id": "schema", "label": "全量命令表", "argv": ["schema"]},
        {"id": "skills.status", "label": "技能安装状态", "argv": ["skills", "status"]},
        {"id": "asr.status", "label": "语音转写状态", "argv": ["asr", "status"]},
    ]},
]


def find_item(item_id: str) -> dict[str, Any] | None:
    for group in CATALOG:
        for item in group["items"]:
            if item["id"] == item_id:
                return item
    return None
