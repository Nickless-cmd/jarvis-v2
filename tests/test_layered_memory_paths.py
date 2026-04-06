from __future__ import annotations


def test_workspace_bootstrap_creates_layered_memory_paths(isolated_runtime) -> None:
    bootstrap = __import__(
        "core.identity.workspace_bootstrap",
        fromlist=["workspace_memory_paths"],
    )

    paths = bootstrap.workspace_memory_paths()

    assert paths["curated_memory"].name == "MEMORY.md"
    assert paths["user"].name == "USER.md"
    assert paths["daily_dir"].exists() is True
    assert paths["curated_dir"].exists() is True
    assert paths["daily_memory"].parent == paths["daily_dir"]
