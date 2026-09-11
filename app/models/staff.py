from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPKMixin

VALID_STAFF_ROLES = ("reviewer", "admin", "super_admin")


class Staff(UUIDPKMixin, CreatedAtMixin, Base):
    """F-04: role-based staff auth. C-03 (role-based data access) is enforced in the
    service layer using `role`, not here - this table just records identity + role."""

    __tablename__ = "staff"
    __table_args__ = (
        CheckConstraint("role IN ('reviewer','admin','super_admin')", name="ck_staff_role"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
