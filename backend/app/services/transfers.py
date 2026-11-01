from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Account, User, Provider, TransferIntent, BankTransaction
from ..models.identity import now
from .accounts import owned_account
from .cards import owned_card
from .ledger import post


def intent_out(db, intent):
    target = db.get(Account, intent.to_account_id)
    owner = db.get(User, target.user_id) if target.user_id else None
    provider = db.get(Provider, intent.provider_id) if intent.provider_id else None
    return {"id": intent.id, "amount": intent.amount, "fee": 0, "description": intent.description, "recipient": owner.full_name if owner else provider.name if provider else target.name, "to_reference": target.reference, "customer_reference": intent.customer_reference, "expires_at": intent.expires_at, "kind": intent.kind}


def preview(db, user, payload, payment=False):
    source = owned_account(db, user, payload.from_account_id)
    if source.status != "active" or source.balance < payload.amount:
        raise HTTPException(400, "Недостаточно средств или счёт недоступен")
    if payload.card_id:
        card = owned_card(db, user, payload.card_id)
        if card.account_id != source.id or card.status != "active":
            raise HTTPException(400, "Карта недоступна для этого счёта")
    if payment:
        provider = db.get(Provider, payload.provider_id)
        if not provider:
            raise HTTPException(404, "Услуга не найдена")
        target = db.get(Account, provider.account_id)
        description = provider.name
    else:
        target = db.scalar(select(Account).where(Account.reference == payload.to_reference.strip().upper(), Account.user_id.is_not(None)))
        if not target or target.status != "active":
            raise HTTPException(404, "Получатель не найден")
        description = payload.description or "Перевод в B bank"
    if source.id == target.id:
        raise HTTPException(400, "Выберите другой счёт получателя")
    intent = TransferIntent(user_id=user.id, from_account_id=source.id, to_account_id=target.id, card_id=payload.card_id, amount=payload.amount, description=description, kind="payment" if payment else "transfer", provider_id=provider.id if payment else None, customer_reference=payload.customer_reference if payment else "", expires_at=now() + timedelta(minutes=5))
    db.add(intent)
    db.flush()
    return intent_out(db, intent)


def confirm(db, user, payload, payment=False):
    existing = db.scalar(select(BankTransaction).where(BankTransaction.initiator_id == user.id, BankTransaction.idempotency_key == payload.idempotency_key))
    if existing:
        if existing.intent_id != payload.intent_id or existing.kind != ("payment" if payment else "transfer"):
            raise HTTPException(409, "Этот ключ уже использован для другой операции")
        return existing
    intent = db.scalar(select(TransferIntent).where(TransferIntent.id == payload.intent_id, TransferIntent.user_id == user.id).with_for_update())
    if not intent:
        raise HTTPException(404, "Подтверждение не найдено")
    if intent.consumed:
        tx = db.scalar(select(BankTransaction).where(BankTransaction.intent_id == intent.id))
        if tx and tx.idempotency_key == payload.idempotency_key:
            return tx
        raise HTTPException(409, "Операция уже выполнена")
    if intent.expires_at <= now() or intent.kind != ("payment" if payment else "transfer"):
        raise HTTPException(400, "Подтверждение истекло. Проверьте данные ещё раз.")
    provider = db.get(Provider, intent.provider_id) if payment else None
    return post(db, intent.from_account_id, intent.to_account_id, intent.amount, actor=user, kind=intent.kind, description=intent.description, category=provider.category if provider else "Переводы", card_id=intent.card_id, intent=intent, idempotency_key=payload.idempotency_key, customer_reference=intent.customer_reference)
