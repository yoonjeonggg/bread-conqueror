"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-09

The first revision builds every table straight from the SQLAlchemy metadata so
the schema can never drift from the models. Subsequent revisions should be
generated with ``alembic revision --autogenerate``.
"""

from __future__ import annotations

from alembic import op
from app.db.base import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
