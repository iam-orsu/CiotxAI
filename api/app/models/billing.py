"""CIOTX API — Billing Models"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")
    billing_period: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scans_used: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    razorpay_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
