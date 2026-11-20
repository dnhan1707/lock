import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Invite(Base):
    """One row per invite link.

    "Expired" is not stored: an invite is expired when status = 'pending' and expires_at < now().
    """

    __tablename__ = "invites"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'cancelled', 'superseded')",
            name="status_valid",
        ),
        CheckConstraint("status = 'pending' OR resolved_at IS NOT NULL", name="resolved_at_when_closed"),
        CheckConstraint(
            "status <> 'accepted' OR (responder_id IS NOT NULL AND relationship_id IS NOT NULL)",
            name="accepted_has_responder_and_relationship",
        ),
        CheckConstraint("responder_id IS NULL OR responder_id <> sender_id", name="not_own_invite"),
        # At most one open invite per sender.
        Index("uq_invites_one_pending_per_sender", "sender_id", unique=True, postgresql_where=text("status = 'pending'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # SHA-256 of the random token in the link. The link itself is never stored.
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    status: Mapped[str] = mapped_column(server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    relationship_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("relationships.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
