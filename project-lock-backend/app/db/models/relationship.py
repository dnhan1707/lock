import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Relationship(Base):
    """One row per lock. Who is in it lives in RelationshipMember."""

    __tablename__ = "relationships"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'ended')", name="status_valid"),
        # Active locks have no end time; ended locks must have one.
        CheckConstraint("(status = 'active') = (ended_at IS NULL)", name="ended_at_matches_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    status: Mapped[str] = mapped_column(server_default="active")
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RelationshipMember(Base):
    """Two rows per relationship, one per person."""

    __tablename__ = "relationship_members"
    __table_args__ = (
        # The "one active lock per user" guarantee, enforced by Postgres.
        Index("uq_relationship_members_one_active", "user_id", unique=True, postgresql_where=text("active")),
    )

    relationship_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("relationships.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    # Copy of relationships.status = 'active', so the partial index above can use it.
    active: Mapped[bool]
