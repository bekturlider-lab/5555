import secrets
from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import Account, Card
from .accounts import owned_account
from ..core.audit import audit
from ..branding import product_label


def card_out(db, c):
    a = db.get(Account, c.account_id)
    return {"id": c.id, "account_id": c.account_id, "account_name": a.name, "account_reference": a.reference, "balance": a.balance, "label": product_label(c.label), "last4": c.last4, "color": c.color, "status": c.status, "daily_limit": c.daily_limit}


def owned_card(db, user, card_id, lock=False):
    q = select(Card).join(Account).where(Card.id == card_id, Account.user_id == user.id)
    c = db.scalar(q.with_for_update(of=Card) if lock else q)
    if not c:
        raise HTTPException(404, "Карта не найдена")
    return c


def list_cards(db, user):
    cards = db.scalars(select(Card).join(Account).where(Account.user_id == user.id).order_by(Card.created_at))
    return [card_out(db, c) for c in cards]


def issue(db, user, payload):
    a = owned_account(db, user, payload.account_id, lock=True)
    if a.status != "active":
        raise HTTPException(400, "Счёт недоступен")
    if db.scalar(select(func.count()).select_from(Card).where(Card.account_id == a.id)) >= 3:
        raise HTTPException(400, "На один счёт можно выпустить до трёх карт")
    c = Card(account_id=a.id, last4=f"{secrets.randbelow(10000):04d}", color=payload.color)
    db.add(c)
    db.flush()
    audit(db, user, "card.created", c.id)
    return card_out(db, c)
