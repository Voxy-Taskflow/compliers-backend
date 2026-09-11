# add_migration.ps1 — creates the initial Alembic migration (0001)

@'
"""initial schema: staff, patients, narratives, summaries, documents, followups, audit_log

Revision ID: 0001
Revises:
Create Date: 2026-09-11
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staff",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), unique=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.CheckConstraint("role IN (''reviewer'',''admin'',''super_admin'')", name="ck_staff_role"),
    )

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(200)),
        sa.Column("preferred_language", sa.String(10)),
        sa.Column("consent_given_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "narratives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("transcript_original", sa.Text),
        sa.Column("transcript_english", sa.Text),
        sa.Column("detected_language", sa.String(10)),
        sa.Column("confidence", sa.Float),
        sa.Column("audio_ref", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="captured"),
        sa.CheckConstraint(
            "status IN (''captured'',''confirmed'',''discarded'')", name="ck_narrative_status"
        ),
    )
    op.create_index("ix_narratives_patient_id", "narratives", ["patient_id"])

    op.create_table(
        "summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "narrative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("narratives.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("facts_json", postgresql.JSONB, nullable=False),
        sa.Column("interpretation_text", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.Column("flagged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("flag_reasons", postgresql.JSONB),
        sa.Column(
            "reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL")
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN (''pending_review'',''reviewed'',''actioned'',''rejected'')", name="ck_summary_status"
        ),
    )
    op.create_index("ix_summaries_narrative_id", "summaries", ["narrative_id"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_image_ref", sa.String(500), nullable=False),
        sa.Column("extracted_text", sa.Text),
        sa.Column("bounding_boxes", postgresql.JSONB),
        sa.Column("simplified_text", sa.Text),
        sa.Column("translated_text", sa.Text),
        sa.Column("target_language", sa.String(10)),
        sa.Column("audio_output_ref", sa.String(500)),
        sa.Column("hallucination_flagged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.CheckConstraint(
            "status IN (''pending_review'',''reviewed'',''actioned'',''rejected'')", name="ck_document_status"
        ),
    )
    op.create_index("ix_documents_patient_id", "documents", ["patient_id"])

    op.create_table(
        "followups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_text", sa.Text),
        sa.Column("rag_context", postgresql.JSONB),
        sa.Column("proposal_text", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_approval"),
        sa.Column(
            "approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL")
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("calendar_event_id", sa.String(200)),
        sa.CheckConstraint(
            "status IN (''pending_approval'',''approved'',''rejected'',''scheduled'')", name="ck_followup_status"
        ),
    )
    op.create_index("ix_followups_patient_id", "followups", ["patient_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_state", postgresql.JSONB),
        sa.Column("after_state", postgresql.JSONB),
        sa.CheckConstraint(
            "actor_type IN (''ai'',''staff'',''patient'',''system'')", name="ck_audit_actor_type"
        ),
    )
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("followups")
    op.drop_table("documents")
    op.drop_table("summaries")
    op.drop_table("narratives")
    op.drop_table("patients")
    op.drop_table("staff")
'@ | Set-Content -Path "migrations\versions\0001_initial_schema.py" -Encoding utf8

Write-Host "Done. migrations/versions/0001_initial_schema.py created." -ForegroundColor Green