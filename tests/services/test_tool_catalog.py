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


def test_catalog_text_does_not_depend_on_how_many_tools_are_registered(monkeypatch):
    """Tallet i «+ N flere værktøjer» fulgte live-tilstand og brød cache-præfikset.

    Kataloget står i systemprompten før historikken; en ændring af antallet af
    registrerede værktøjer (bro/telefon/connector kobler til eller fra) må ikke
    ændre en eneste byte af teksten, så længe de kuraterede kerneværktøjer er
    de samme.
    """
    from core.services import tool_catalog
    from core.tools.simple_tools import get_tool_definitions

    base = list(get_tool_definitions())

    def extra(i):
        return {"type": "function", "function": {
            "name": f"__ekstra_{i}", "description": "x", "parameters": {}}}

    texts = []
    for n_extra in (1, 2, 12):
        monkeypatch.setattr(tool_catalog, "get_tool_definitions",
                            lambda n=n_extra: base + [extra(i) for i in range(n)])
        invalidate_cache()
        texts.append(tool_catalog._render_catalog_text())
    invalidate_cache()

    assert texts[0] == texts[1] == texts[2]
    assert "flere værktøjer" in texts[0]
    assert not any(ch.isdigit() for ch in texts[0].split("flere værktøjer")[0].split("\n")[-1])
