from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base
from .identity import uid, now


class ConsentReceipt(Base):
    __tablename__ = "consent_receipts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version: Mapped[str] = mapped_column(String(40))
    documents: Mapped[list] = mapped_column(JSON)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ai_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConsentAcceptance(Base):
    __tablename__ = "consent_acceptances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("consent_receipts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AiConversation(Base):
    __tablename__ = "ai_conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("consent_receipts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    pending_key: Mapped[str | None] = mapped_column(String(80))
    pending_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalation_reason: Mapped[str] = mapped_column(String(40), default="")
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
