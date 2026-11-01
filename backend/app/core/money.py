from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo


def day_start():
    local = datetime.now(ZoneInfo("Asia/Bishkek"))
    return datetime.combine(local.date(), time.min, local.tzinfo).astimezone(timezone.utc)


def money(amount):
    return f"{amount / 100:,.2f}".replace(",", " ") + " сом"
