from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base
from .identity import uid, now


class ProductOrder(Base):
    __tablename__ = "product_orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reference: Mapped[str] = mapped_column(String(30), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(String(30))
    request_key: Mapped[str] = mapped_column(String(80))
    note: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(20), default="new")
    staff_note: Mapped[str] = mapped_column(String(1000), default="")
    fulfilled_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("user_id", "request_key"), CheckConstraint("status IN ('new','in_review','completed','declined','cancelled')"))
