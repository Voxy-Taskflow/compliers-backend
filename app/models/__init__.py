# Import every model so Base.metadata is fully populated - required for
# Alembic autogenerate and for Base.metadata.create_all() to see all tables.
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.followup import Followup
from app.models.narrative import Narrative
from app.models.patient import Patient
from app.models.staff import Staff
from app.models.summary import Summary

__all__ = ["AuditLog", "Document", "Followup", "Narrative", "Patient", "Staff", "Summary"]
