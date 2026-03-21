from pathlib import Path

JARVIS_HOME = Path.home() / ".jarvis-v2"
CONFIG_DIR = JARVIS_HOME / "config"
SETTINGS_FILE = CONFIG_DIR / "runtime.json"
PROVIDER_ROUTER_FILE = CONFIG_DIR / "provider_router.json"
STATE_DIR = JARVIS_HOME / "state"
LOG_DIR = JARVIS_HOME / "logs"
CACHE_DIR = JARVIS_HOME / "cache"
SESSIONS_DIR = JARVIS_HOME / "sessions"
AUTH_DIR = JARVIS_HOME / "auth"
AUTH_PROFILES_DIR = AUTH_DIR / "profiles"
WORKSPACES_DIR = JARVIS_HOME / "workspaces"
