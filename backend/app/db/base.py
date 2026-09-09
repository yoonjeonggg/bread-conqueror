"""Import target for Alembic autogenerate — pulls every model into the registry."""

from app.db.base_class import Base
from app.models import *  # noqa: F401,F403

__all__ = ["Base"]
