"""Database package with lazy session exports.

Importing ORM models should not create an engine or require an installed async
SQLite driver. Runtime session objects are imported only when explicitly used.
"""

from importlib import import_module

__all__ = ["SessionLocal", "engine", "get_db", "init_db"]


def __getattr__(name: str):
	"""Load runtime database resources only when a caller asks for them."""
	if name not in __all__:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
	module = import_module("app.db.session")
	return getattr(module, name)
