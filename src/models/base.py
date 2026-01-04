"""Base SQLAlchemy models and mixins."""

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the record was last updated",
    )

    def __repr__(self) -> str:
        """Return string representation of the model."""
        attrs = []
        for column in self.__table__.columns:  # type: ignore[attr-defined]
            attrs.append(f"{column.name}={getattr(self, column.name)!r}")
        return f"{self.__class__.__name__}({', '.join(attrs)})"
