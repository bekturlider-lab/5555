import csv
import io
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select, or_, and_, func
from ..models import Account, User, BankTransaction


def own_ids(db, user):
    return list(db.scalars(select(Account.id).where(Account.user_id == user.id)))


def transaction_out(db, tx, user):
    source, target = db.get(Account, tx.from_account_id), db.get(Account, tx.to_account_id)
    outgoing = source.user_id == user.id
    internal = outgoing and target.user_id == user.id
    other = target if outgoing else source
    owner = db.get(User, other.user_id) if other.user_id else None
    return {"id": tx.id, "reference": tx.reference, "amount": tx.amount, "direction": "internal" if internal else "outgoing" if outgoing else "incoming", "kind": tx.kind, "description": tx.description, "category": tx.category, "counterparty": owner.full_name if owner else other.name, "from_reference": source.reference, "to_reference": target.reference, "customer_reference": tx.customer_reference, "created_at": tx.created_at, "status": "completed", "fee": 0}


def filtered(db, user, q="", direction="all", account_id="", date_from="", date_to="", category=""):
    ids = own_ids(db, user)
    query = select(BankTransaction).where(or_(BankTransaction.from_account_id.in_(ids), BankTransaction.to_account_id.in_(ids)))
    if q:
        needle = "%" + q[:100] + "%"
        matching = select(Account.id).join(User).where(User.full_name.ilike(needle))
        query = query.where(or_(BankTransaction.reference.ilike(needle), BankTransaction.description.ilike(needle), BankTransaction.category.ilike(needle), BankTransaction.from_account_id.in_(matching), BankTransaction.to_account_id.in_(matching)))
    if direction == "outgoing":
        query = query.where(BankTransaction.from_account_id.in_(ids), ~BankTransaction.to_account_id.in_(ids))
    elif direction == "incoming":
        query = query.where(BankTransaction.to_account_id.in_(ids), ~BankTransaction.from_account_id.in_(ids))
    if account_id:
        if account_id not in ids:
            raise HTTPException(404, "Счёт не найден")
        query = query.where(or_(BankTransaction.from_account_id == account_id, BankTransaction.to_account_id == account_id))
    if category:
        query = query.where(BankTransaction.category == category)
    try:
        if date_from:
            query = query.where(BankTransaction.created_at >= datetime.combine(datetime.strptime(date_from, "%Y-%m-%d").date(), time.min, ZoneInfo("Asia/Bishkek")))
        if date_to:
            query = query.where(BankTransaction.created_at < datetime.combine(datetime.strptime(date_to, "%Y-%m-%d").date() + timedelta(days=1), time.min, ZoneInfo("Asia/Bishkek")))
    except ValueError:
        raise HTTPException(422, "Дата должна быть в формате ГГГГ-ММ-ДД")
    return query


def history(db, user, page=1, page_size=10, **filters):
    query = filtered(db, user, **filters)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(BankTransaction.created_at.desc(), BankTransaction.id).offset((page - 1) * page_size).limit(page_size))
    return {"items": [transaction_out(db, tx, user) for tx in items], "total": total, "page": page, "page_size": page_size}


def detail(db, user, tx_id):
    tx = db.get(BankTransaction, tx_id)
    if not tx or not db.scalar(select(Account.id).where(Account.user_id == user.id, Account.id.in_([tx.from_account_id, tx.to_account_id]))):
        raise HTTPException(404, "Операция не найдена")
    return transaction_out(db, tx, user)


def csv_export(db, user, **filters):
    stream = io.StringIO()
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(["Номер", "Дата", "Получатель / отправитель", "Описание", "Сумма KGS", "Направление"])
    def safe(value):
        value = str(value)
        return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value
    for tx in db.scalars(filtered(db, user, **filters).order_by(BankTransaction.created_at.desc()).limit(5000)):
        item = transaction_out(db, tx, user)
        writer.writerow([safe(item['reference']), tx.created_at.isoformat(), safe(item['counterparty']), safe(tx.description), f"{tx.amount / 100:.2f}", item['direction']])
    return "\ufeff" + stream.getvalue()
