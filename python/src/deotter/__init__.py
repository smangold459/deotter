"""
Copyright 2026 Shane R. Mangold

Licensed under the Apache License, Version 2.0.
See http://www.apache.org/licenses/LICENSE-2.0 or LICENSE file for details.
"""

from .wrapper import DeotterConnection


def connect(db_alias: str, autocommit: bool = True) -> DeotterConnection:
	"""Create a Deotter connection for the configured database alias."""
	return DeotterConnection(db_alias, autocommit=autocommit)


__all__ = ["connect", "DeotterConnection"]
