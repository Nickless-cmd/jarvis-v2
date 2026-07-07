from core.services.tool_catalog import (
    _CORE_TOOLS,
    build_catalog_text,
    catalog_token_estimate,
    invalidate_cache,
)


def test_catalog_lists_core_tools():
    # 2026-06-22/23 redesign: the full ~445-tool "TOOL CATALOG" was 59% of the
    # visible system prompt and fully redundant with the native tool defs sent
    # every turn. It was replaced by a compact grouped "KERNE-VÆRKTØJER" core
    # set + a load_more_tools() pointer. The catalog now lists only the curated
    # core tools (those that are actually registered), not every tool.
    invalidate_cache()
    text = build_catalog_text()
    assert "KERNE-VÆRKTØJER" in text
    from core.tools.simple_tools import get_tool_definitions
    registered = {
        (d.get("function") or {}).get("name") or d.get("name")
        for d in get_tool_definitions()
    }
    core_registered = [n for n in _CORE_TOOLS if n in registered]
    assert core_registered, "expected at least some core tools to be registered"
    for name in core_registered:
        assert name in text, f"Missing core tool {name!r} in catalog"


def test_catalog_format_is_one_line_per_tool():
    invalidate_cache()
    text = build_catalog_text()
    lines = [ln for ln in text.splitlines() if ln.startswith("- ")]
    # Compact core catalog: a handful of grouped core tools, not the old 200+.
    assert lines, "expected at least one tool line"
    bad = [ln for ln in lines if ":" not in ln]
    assert not bad, f"Lines without name:desc separator: {bad[:3]}"


def test_catalog_points_to_load_more_tools():
    invalidate_cache()
    text = build_catalog_text()
    assert "load_more_tools" in text


def test_catalog_caches_until_tools_change():
    invalidate_cache()
    a = build_catalog_text()
    b = build_catalog_text()
    assert a is b, "Catalog text should be cached identity-equal between calls"


def test_catalog_token_estimate_reasonable():
    invalidate_cache()
    n = catalog_token_estimate()
    # Compact core catalog is intentionally small (~hundreds of tokens), far
    # below the old ~7.5k-token full catalog. Guard against accidental regression
    # back to the bloated form while keeping a non-trivial lower bound.
    assert 100 < n < 3000, f"Catalog tokens out of expected band: {n}"
