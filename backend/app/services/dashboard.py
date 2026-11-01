from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from sqlalchemy import select, or_
from ..models import Account, User, BankTransaction, Notification
from .accounts import list_accounts
from .cards import list_cards
from .statements import own_ids, history


def overview(db, user):
    ids = own_ids(db, user)
    zone = ZoneInfo("Asia/Bishkek")
    local = datetime.now(zone)
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    transactions = list(db.scalars(select(BankTransaction).where(or_(BankTransaction.from_account_id.in_(ids), BankTransaction.to_account_id.in_(ids)), BankTransaction.created_at >= start - timedelta(days=32)).order_by(BankTransaction.created_at.desc())))
    income, spent, categories, daily = 0, 0, defaultdict(int), defaultdict(int)
    contacts, contact_ids = [], set()
    for tx in transactions:
        outgoing = tx.from_account_id in ids
        incoming = tx.to_account_id in ids
        stamp = tx.created_at.astimezone(zone)
        if stamp >= start:
            if outgoing and not incoming:
                spent += tx.amount
                categories[tx.category] += tx.amount
                daily[stamp.date().isoformat()] += tx.amount
            if incoming and not outgoing:
                income += tx.amount
        other_id = tx.to_account_id if outgoing else tx.from_account_id
        if len(contacts) < 5:
            account = db.get(Account, other_id)
            if account.user_id and account.user_id != user.id and account.user_id not in contact_ids:
                other = db.get(User, account.user_id)
                contacts.append({"reference": account.reference, "full_name": other.full_name})
                contact_ids.add(account.user_id)
    dates = [(local - timedelta(days=i)).date() for i in range(6, -1, -1)]
    accounts = list_accounts(db, user)
    return {"balance": sum(a['balance'] for a in accounts), "income": income, "spent": spent, "accounts": accounts, "cards": list_cards(db, user), "transactions": history(db, user, page_size=5)['items'], "categories": [{"name": name, "amount": value} for name, value in sorted(categories.items(), key=lambda x: -x[1])], "daily": [{"date": d.isoformat(), "amount": daily[d.isoformat()]} for d in dates], "contacts": contacts, "unread": len(list(db.scalars(select(Notification.id).where(Notification.user_id == user.id, Notification.is_read.is_(False)))))}
