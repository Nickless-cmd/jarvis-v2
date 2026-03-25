from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture()
def isolated_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))

    module_names = [
        "core.runtime.config",
        "core.runtime.settings",
        "core.runtime.db",
        "core.runtime.bootstrap",
        "core.identity.workspace_bootstrap",
        "core.identity.visible_identity",
        "apps.api.jarvis_api.services.prompt_contract",
        "apps.api.jarvis_api.services.visible_model",
        "apps.api.jarvis_api.services.reflection_signal_tracking",
        "apps.api.jarvis_api.services.temporal_recurrence_signal_tracking",
        "apps.api.jarvis_api.routes.mission_control",
    ]
    modules: dict[str, object] = {}
    for name in module_names:
        module = importlib.import_module(name)
        modules[name] = importlib.reload(module)

    runtime_bootstrap = modules["core.runtime.bootstrap"]
    runtime_db = modules["core.runtime.db"]
    workspace_bootstrap = modules["core.identity.workspace_bootstrap"]

    runtime_bootstrap.ensure_runtime_dirs()
    runtime_db.init_db()
    workspace_bootstrap.ensure_default_workspace()

    return SimpleNamespace(
        config=modules["core.runtime.config"],
        settings=modules["core.runtime.settings"],
        db=runtime_db,
        bootstrap=runtime_bootstrap,
        workspace_bootstrap=workspace_bootstrap,
        visible_identity=modules["core.identity.visible_identity"],
        prompt_contract=modules["apps.api.jarvis_api.services.prompt_contract"],
        visible_model=modules["apps.api.jarvis_api.services.visible_model"],
        reflection_tracking=modules["apps.api.jarvis_api.services.reflection_signal_tracking"],
        temporal_recurrence_tracking=modules["apps.api.jarvis_api.services.temporal_recurrence_signal_tracking"],
        mission_control=modules["apps.api.jarvis_api.routes.mission_control"],
    )
