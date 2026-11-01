import secrets
from fastapi import HTTPException
from sqlalchemy import select, func
from ..models import Account, Card, BankTransaction, LedgerEntry
from ..models.identity import now
from ..core.money import day_start, money
from ..core.audit import audit, notify


def post(db, source_id, target_id, amount, *, actor=None, kind="transfer", description="", category="Переводы", card_id=None, intent=None, idempotency_key=None, customer_reference="", stamp=None, send_notifications=True):
    if amount <= 0 or source_id == target_id:
        raise HTTPException(400, "Проверьте сумму и счета операции")
    card = db.scalar(select(Card).where(Card.id == card_id).with_for_update()) if card_id else None
    accounts = list(db.scalars(select(Account).where(Account.id.in_([source_id, target_id])).order_by(Account.id).with_for_update()))
    index = {a.id: a for a in accounts}
    source, target = index.get(source_id), index.get(target_id)
    if not source or not target or source.status != "active" or target.status != "active":
        raise HTTPException(400, "Один из счетов недоступен")
    if actor and source.user_id != actor.id:
        raise HTTPException(403, "Счёт списания недоступен")
    if card_id:
        if not card or card.account_id != source.id:
            raise HTTPException(404, "Карта не найдена")
        if card.status != "active":
            raise HTTPException(400, "Карта заблокирована. Выберите другой источник.")
        spent = db.scalar(select(func.coalesce(func.sum(BankTransaction.amount), 0)).where(BankTransaction.card_id == card.id, BankTransaction.created_at >= day_start()))
        if spent + amount > card.daily_limit:
            raise HTTPException(400, "Превышен дневной лимит карты")
    if source.user_id and source.balance < amount:
        raise HTTPException(400, "На счёте недостаточно средств")
    source.balance -= amount
    target.balance += amount
    tx = BankTransaction(reference="CP-" + secrets.token_hex(5).upper(), initiator_id=actor.id if actor else None, from_account_id=source.id, to_account_id=target.id, amount=amount, kind=kind, description=description, category=category, card_id=card_id, intent_id=intent.id if intent else None, idempotency_key=idempotency_key, customer_reference=customer_reference, created_at=stamp or now())
    db.add(tx)
    db.flush()
    db.add_all([LedgerEntry(transaction_id=tx.id, account_id=source.id, delta=-amount), LedgerEntry(transaction_id=tx.id, account_id=target.id, delta=amount)])
    if intent:
        intent.consumed = True
    if send_notifications:
        notify(db, source.user_id, "Платёж выполнен" if kind == "payment" else "Перевод отправлен", money(amount) + ". " + description, "/bank/history/" + tx.id)
        if target.user_id != source.user_id:
            notify(db, target.user_id, "Поступление на счёт", money(amount), "/bank/history/" + tx.id)
        audit(db, actor, "money." + kind, tx.id, amount=amount, reference=tx.reference)
    db.flush()
    return tx
