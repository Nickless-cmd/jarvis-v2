from pathlib import Path

JARVIS_HOME = Path.home() / ".jarvis-v2"
CONFIG_DIR = JARVIS_HOME / "config"
SETTINGS_FILE = CONFIG_DIR / "runtime.json"
STATE_DIR = JARVIS_HOME / "state"
LOG_DIR = JARVIS_HOME / "logs"
CACHE_DIR = JARVIS_HOME / "cache"
SESSIONS_DIR = JARVIS_HOME / "sessions"
AUTH_DIR = JARVIS_HOME / "auth"
WORKSPACES_DIR = JARVIS_HOME / "workspaces"
