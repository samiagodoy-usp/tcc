"""Connection requests and messaging models.

Messaging is unlocked only after a connection request is ``accepted`` (FR-CONN-2,
FR-MSG-1). Enforcement lives in the service layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ConnectionStatus


class ConnectionRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connection_requests"

    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, name="connection_status"),
        default=ConnectionStatus.PENDING,
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[Message]] = relationship(
        back_populates="connection", cascade="all, delete-orphan"
    )

    def involves(self, user_id: uuid.UUID) -> bool:
        return user_id in (self.sender_id, self.recipient_id)


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connection_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Soft delete: the sender may delete their own message. The row is kept (so the
    # thread order is stable) but the body is redacted and it renders as a
    # "message deleted" tombstone for everyone.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    connection: Mapped[ConnectionRequest] = relationship(back_populates="messages")
