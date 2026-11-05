"""Jarvis' egen Linux-desktop (Xvfb + window manager) til visning i en fane."""
from __future__ import annotations

from core.desktop.x_session import XSession, bygg_input, mangler_pakker

__all__ = ["XSession", "bygg_input", "mangler_pakker"]
