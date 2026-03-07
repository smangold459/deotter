from .wrapper import DeotterConnection


def connect(db_alias: str, autocommit: bool = True) -> DeotterConnection:
	"""Create a Deotter connection for the configured database alias."""
	return DeotterConnection(db_alias, autocommit=autocommit)


__all__ = ["connect", "DeotterConnection"]
