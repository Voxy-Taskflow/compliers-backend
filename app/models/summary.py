import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPKMixin

VALID_REVIEW_STATUSES = ("pending_review", "reviewed", "actioned", "rejected")


class Summary(UUIDPKMixin, CreatedAtMixin, Base):
    """N workstream. facts_json comes from the fact-extraction prompt (N-02);
    interpretation_text comes from the SEPARATE interpretation prompt (N-03).
    These are two distinct LLM calls and MUST stay in two distinct columns - never
    concatenate them into one field, since S-01's split-pane UI depends on this
    separation being structural, not just visual.

    H-03 (non-negotiable): status defaults to 'pending_review' for every row, no
    exceptions - there is no code path that inserts a summary as already 'reviewed'."""

    __tablename__ = "summaries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review','reviewed','actioned','rejected')",
            name="ck_summary_status",
        ),
    )

    narrative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("narratives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    facts_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    interpretation_text: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flag_reasons: Mapped[dict | None] = mapped_column(JSONB)

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
