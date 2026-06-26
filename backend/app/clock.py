"""应用时钟:统一的当前时间入口(借鉴 FBA 的集中式 timezone 工具,但只取集中这一点)。

存储一律 UTC(tz-aware):业界推荐,多用户/多 agent/将来多区都正确;展示侧本地化交给前端
(前端 new Date(iso).toLocaleString() 自动转浏览器时区)。集中成一个函数 = 一个旋钮 + 好 mock,
免去 datetime.now(timezone.utc) 散落各处。
ponytail: 不抄 FBA 的「存 Asia/Shanghai」和自定义 TimeZone 列类型——PG 的 timestamptz 经 psycopg
本就返回 tz-aware,那层 TypeDecorator 是为 MySQL/返回 naive 的驱动准备的,我们用不上。
"""

from datetime import datetime, timezone


def now() -> datetime:
    """当前时间(tz-aware UTC)。"""
    return datetime.now(timezone.utc)
