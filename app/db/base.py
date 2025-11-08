"""SQLAlchemy declarative base with typing-friendly API.

Use the SQLAlchemy 2.0 DeclarativeBase which is properly typed for static
type checkers. This avoids "Base has type Any" errors from mypy when
subclassing the ORM base in models.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
	pass
