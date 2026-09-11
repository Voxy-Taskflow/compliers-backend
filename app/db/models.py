"""SQLAlchemy ORM models - must mirror migrations/versions/0001_initial_schema.py exactly.
If you change a table here, you also need a new Alembic migration - these two files
drift apart silently otherwise, and that is a hard bug to catch later."""
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Staff(Base):
    __tablename__ = "staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20), unique=True)
    role = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (CheckConstraint("role IN ('reviewer','admin','super_admin')", name="ck_staff_role"),)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    phone = Column(String(20), nullable=False, unique=True)
    name = Column(String(200))
    preferred_language = Column(String(10))
    consent_given_at = Column(DateTime(timezone=True))

    narratives = relationship("Narrative", back_populates="patient")
    documents = relationship("Document", back_populates="patient")
    followups = relationship("Followup", back_populates="patient")


class Narrative(Base):
    __tablename__ = "narratives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    transcript_original = Column(Text)
    transcript_english = Column(Text)
    detected_language = Column(String(10))
    confidence = Column(Float)
    audio_ref = Column(String(500))
    status = Column(String(20), nullable=False, default="captured")

    __table_args__ = (
        CheckConstraint("status IN ('captured','confirmed','discarded')", name="ck_narrative_status"),
    )

    patient = relationship("Patient", back_populates="narratives")
    summaries = relationship("Summary", back_populates="narrative")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    narrative_id = Column(UUID(as_uuid=True), ForeignKey("narratives.id", ondelete="CASCADE"), nullable=False)
    facts_json = Column(JSONB, nullable=False)
    interpretation_text = Column(Text)
    status = Column(String(20), nullable=False, default="pending_review")
    flagged = Column(Boolean, nullable=False, default=False)
    flag_reasons = Column(JSONB)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review','reviewed','actioned','rejected')", name="ck_summary_status"
        ),
    )

    narrative = relationship("Narrative", back_populates="summaries")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    source_image_ref = Column(String(500), nullable=False)
    extracted_text = Column(Text)
    bounding_boxes = Column(JSONB)
    simplified_text = Column(Text)
    translated_text = Column(Text)
    target_language = Column(String(10))
    audio_output_ref = Column(String(500))
    hallucination_flagged = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="pending_review")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review','reviewed','actioned','rejected')", name="ck_document_status"
        ),
    )

    patient = relationship("Patient", back_populates="documents")


class Followup(Base):
    __tablename__ = "followups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    query_text = Column(Text)
    rag_context = Column(JSONB)
    proposal_text = Column(Text)
    status = Column(String(20), nullable=False, default="pending_approval")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"))
    approved_at = Column(DateTime(timezone=True))
    calendar_event_id = Column(String(200))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_approval','approved','rejected','scheduled')", name="ck_followup_status"
        ),
    )

    patient = relationship("Patient", back_populates="followups")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(UUID(as_uuid=True))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    before_state = Column(JSONB)
    after_state = Column(JSONB)

    __table_args__ = (
        CheckConstraint("actor_type IN ('ai','staff','patient','system')", name="ck_audit_actor_type"),
    )
