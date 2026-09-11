import uuid

from sqlalchemy import CheckConstraint, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPKMixin


class AuditLog(UUIDPKMixin, CreatedAtMixin, Base):
    """H-05: immutable log of every AI decision + human override + data access.
    actor_id is intentionally NOT a foreign key - it's polymorphic (staff.id,
    patients.id, or null for actor_type='ai'/'system') and rows here must never be
    blocked or cascaded by changes elsewhere. No updated_at column on purpose:
    application code should INSERT-only against this table. In production, REVOKE
    UPDATE/DELETE on this table from the app's DB role at the Postgres level too."""

    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('ai','staff','patient','system')", name="ck_audit_actor_type"
        ),
    )

    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB)
    after_state: Mapped[dict | None] = mapped_column(JSONB)
