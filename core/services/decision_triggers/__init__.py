"""Decision triggers — importing this package registers all triggers.

Each trigger module calls decision_signals.register() at import time, so
simply importing the package populates the registry.
"""
from . import loop_nudge  # noqa: F401
