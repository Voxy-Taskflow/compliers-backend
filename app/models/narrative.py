import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPKMixin

VALID_NARRATIVE_STATUSES = ("captured", "confirmed", "discarded")


class Narrative(UUIDPKMixin, CreatedAtMixin, Base):
    """V workstream. transcript_original is the raw-language STT output,
    transcript_english is the translated-to-English STT output (V-03).
    audio_ref points at object storage, not a blob - C-02 deletes the raw audio
    post-confirmation, so this column may become null over time by design."""

    __tablename__ = "narratives"
    __table_args__ = (
        CheckConstraint(
            "status IN ('captured','confirmed','discarded')", name="ck_narrative_status"
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transcript_original: Mapped[str | None] = mapped_column(Text)
    transcript_english: Mapped[str | None] = mapped_column(Text)
    detected_language: Mapped[str | None] = mapped_column(String(10))
    confidence: Mapped[float | None] = mapped_column(Float)
    audio_ref: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="captured")
