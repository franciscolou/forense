"""Association tables for many-to-many relationships.

Kept in a dedicated module to avoid circular imports between the entity models
that reference them.
"""
from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Table

from app.core.database import Base

# A firm is composed of one or more lawyers (and a lawyer may belong to several
# firms). The business rule "a firm requires at least one lawyer" is enforced in
# the service layer, not at the schema level.
firm_lawyers = Table(
    "firm_lawyers",
    Base.metadata,
    Column("firm_id", ForeignKey("firms.id", ondelete="CASCADE"), primary_key=True),
    Column("lawyer_id", ForeignKey("lawyers.id", ondelete="CASCADE"), primary_key=True),
)

# Lawyers practise in one or more areas of law.
lawyer_practice_areas = Table(
    "lawyer_practice_areas",
    Base.metadata,
    Column("lawyer_id", ForeignKey("lawyers.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "practice_area_id",
        ForeignKey("practice_areas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# Firms advertise the areas of law they cover.
firm_practice_areas = Table(
    "firm_practice_areas",
    Base.metadata,
    Column("firm_id", ForeignKey("firms.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "practice_area_id",
        ForeignKey("practice_areas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
