import secrets
from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import Account, Card, User
from ..core.audit import audit


def account_out(a):
    return {"id": a.id, "reference": a.reference, "name": a.name, "kind": a.kind, "balance": a.balance, "currency": "KGS", "status": a.status, "created_at": a.created_at}


def owned_account(db, user, account_id, lock=False):
    q = select(Account).where(Account.id == account_id, Account.user_id == user.id)
    a = db.scalar(q.with_for_update() if lock else q)
    if not a:
        raise HTTPException(404, "Счёт не найден")
    return a


def list_accounts(db, user):
    return [account_out(a) for a in db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.created_at))]


def open_account(db, user, payload):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    if db.scalar(select(func.count()).select_from(Account).where(Account.user_id == user.id)) >= 5:
        raise HTTPException(400, "Можно открыть не более пяти учебных счетов")
    a = Account(user_id=user.id, reference="CB" + secrets.token_hex(5).upper(), name=payload.name, kind=payload.kind)
    db.add(a)
    db.flush()
    audit(db, user, "account.created", a.id)
    return account_out(a)


def recipient(db, user, reference):
    a = db.scalar(select(Account).where(func.upper(Account.reference) == reference.strip().upper(), Account.user_id.is_not(None), Account.status == "active"))
    if not a:
        raise HTTPException(404, "Получатель не найден. Проверьте номер счёта.")
    owner = db.get(User, a.user_id)
    return {"reference": a.reference, "full_name": owner.full_name, "own": owner.id == user.id}
