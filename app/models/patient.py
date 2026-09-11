from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPKMixin


class Patient(UUIDPKMixin, CreatedAtMixin, Base):
    """F-04: patient auth is OTP/phone-based, so phone is the unique identifier.
    F-06: consent_given_at is null until the consent flow completes - services that
    touch PII should check this before proceeding."""

    __tablename__ = "patients"

    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(200))
    preferred_language: Mapped[str | None] = mapped_column(String(10))  # e.g. 'hi', 'ta', 'bn'
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
