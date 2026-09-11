import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPKMixin


class Document(UUIDPKMixin, CreatedAtMixin, Base):
    """D workstream. bounding_boxes stored alongside extracted_text for the D-03
    audit trail and the D-06 OCR-overlay UI. hallucination_flagged is set by D-05's
    diff between LLM-generated entities and the raw OCR text - reuses the same
    pending_review/reviewed/actioned/rejected lifecycle as summaries."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review','reviewed','actioned','rejected')",
            name="ck_document_status",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_image_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    bounding_boxes: Mapped[dict | None] = mapped_column(JSONB)
    simplified_text: Mapped[str | None] = mapped_column(Text)
    translated_text: Mapped[str | None] = mapped_column(Text)
    target_language: Mapped[str | None] = mapped_column(String(10))
    audio_output_ref: Mapped[str | None] = mapped_column(String(500))
    hallucination_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
