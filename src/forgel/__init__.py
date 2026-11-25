"""Forgel — an open-source autonomous software studio."""

__all__ = ["__version__"]


def __getattr__(name: str) -> str:
    """``forgel.__version__`` is the released version, not a second copy."""

    if name == "__version__":
        from .engine_version import engine_version

        return engine_version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
