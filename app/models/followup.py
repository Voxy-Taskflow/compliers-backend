import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPKMixin


class Followup(UUIDPKMixin, CreatedAtMixin, Base):
    """A workstream. A-04 (non-negotiable hard gate): calendar_event_id is only ever
    populated AFTER status flips to 'approved' by a staff member - the Calendar
    Service must refuse to execute against a row that isn't 'approved' yet."""

    __tablename__ = "followups"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_approval','approved','rejected','scheduled')",
            name="ck_followup_status",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_text: Mapped[str | None] = mapped_column(Text)
    rag_context: Mapped[dict | None] = mapped_column(JSONB)
    proposal_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_approval")

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calendar_event_id: Mapped[str | None] = mapped_column(String(200))
