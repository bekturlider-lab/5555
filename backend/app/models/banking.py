from datetime import datetime
from sqlalchemy import String, ForeignKey, BigInteger, DateTime, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base
from .identity import uid, now


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(16), default="current")
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("user_id IS NULL OR balance >= 0", name="client_balance_nonnegative"),)


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(50), default="B Black")
    last4: Mapped[str] = mapped_column(String(4))
    color: Mapped[str] = mapped_column(String(16), default="graphite")
    status: Mapped[str] = mapped_column(String(16), default="active")
    daily_limit: Mapped[int] = mapped_column(BigInteger, default=10000000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("daily_limit >= 100 AND daily_limit <= 100000000"), CheckConstraint("status IN ('active','frozen')"))


class Provider(Base):
    __tablename__ = "providers"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))
    color: Mapped[str] = mapped_column(String(16))
    icon: Mapped[str] = mapped_column(String(30))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))


class TransferIntent(Base):
    __tablename__ = "transfer_intents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    from_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    card_id: Mapped[str | None] = mapped_column(ForeignKey("cards.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(180), default="")
    kind: Mapped[str] = mapped_column(String(16), default="transfer")
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    customer_reference: Mapped[str] = mapped_column(String(80), default="")
    consumed: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BankTransaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reference: Mapped[str] = mapped_column(String(30), unique=True)
    initiator_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    from_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    to_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    card_id: Mapped[str | None] = mapped_column(ForeignKey("cards.id"))
    intent_id: Mapped[str | None] = mapped_column(ForeignKey("transfer_intents.id"), unique=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    amount: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(180), default="")
    category: Mapped[str] = mapped_column(String(40), default="Переводы")
    customer_reference: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    __table_args__ = (UniqueConstraint("initiator_id", "idempotency_key"), CheckConstraint("amount > 0"), CheckConstraint("from_account_id <> to_account_id"))


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    delta: Mapped[int] = mapped_column(BigInteger)
    __table_args__ = (UniqueConstraint("transaction_id", "account_id"), CheckConstraint("delta <> 0"))
