from core.services.tool_catalog import build_catalog_text, catalog_token_estimate, invalidate_cache


def test_catalog_lists_all_tools():
    invalidate_cache()
    text = build_catalog_text()
    assert "TOOL CATALOG" in text
    from core.tools.simple_tools import get_tool_definitions
    defs = get_tool_definitions()
    for d in defs:
        name = (d.get("function") or {}).get("name") or d.get("name")
        assert name and name in text, f"Missing {name!r} in catalog"


def test_catalog_format_is_one_line_per_tool():
    invalidate_cache()
    text = build_catalog_text()
    lines = [ln for ln in text.splitlines() if ln.startswith("- ")]
    assert len(lines) >= 200, f"Expected at least 200 tool lines, got {len(lines)}"
    bad = [ln for ln in lines if ":" not in ln]
    assert not bad, f"Lines without name:desc separator: {bad[:3]}"


def test_catalog_caches_until_tools_change():
    invalidate_cache()
    a = build_catalog_text()
    b = build_catalog_text()
    assert a is b, "Catalog text should be cached identity-equal between calls"


def test_catalog_token_estimate_reasonable():
    invalidate_cache()
    n = catalog_token_estimate()
    assert 3000 < n < 15000, f"Catalog tokens out of expected band: {n}"
