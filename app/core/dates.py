# app/core/dates.py
"""「今天」按用户所在时区算(A4.2)。

服务器跑在 UTC; 纽约晚上 8 点后 UTC 已是第二天 —— 当天到期的批次会被当成过期、
当天的晚餐会被当成「已过日期」。前端每个请求带 `X-Timezone`(浏览器 IANA 时区,
如 America/New_York), 这里据此算当地日期。

· 无状态: 不存用户资料, 换设备 / 出差自动跟着当地时区走
· 缺失或无效(拼错、伪造)一律退回 UTC, 绝不报错 —— 最坏就是旧行为
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Header


def today_in(tz_name: str | None) -> date:
    """给定 IANA 时区名的当地日期; 无效 / 缺失 → UTC 日期。"""
    if tz_name and len(tz_name) <= 64:
        try:
            return datetime.now(ZoneInfo(tz_name.strip())).date()
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return datetime.now(UTC).date()


async def get_today(
    x_timezone: str | None = Header(default=None),
) -> date:
    """FastAPI 依赖: 当前请求用户的「今天」。"""
    return today_in(x_timezone)
