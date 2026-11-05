import pytest

from core.services import mcp_apps


def test_resource_uri_foretraekker_nested_og_accepterer_legacy():
    assert mcp_apps.resource_uri({"_meta": {
        "ui": {"resourceUri": "ui://ny/app"},
        "ui/resourceUri": "ui://gammel/app",
    }}) == "ui://ny/app"
    assert mcp_apps.resource_uri({"_meta": {"ui/resourceUri": "ui://gammel/app"}}) \
        == "ui://gammel/app"
    assert mcp_apps.resource_uri({"_meta": {"ui": {"resourceUri": "https://forkert"}}}) == ""


def test_tool_visibility_er_begge_som_standard_og_ellers_eksplicit():
    assert mcp_apps.tool_visible_to({"name": "x"}, "model") is True
    assert mcp_apps.tool_visible_to({"name": "x"}, "app") is True
    app_only = {"_meta": {"ui": {"visibility": ["app"]}}}
    assert mcp_apps.tool_visible_to(app_only, "app") is True
    assert mcp_apps.tool_visible_to(app_only, "model") is False
    assert mcp_apps.tool_visible_to(app_only, "ukendt") is False


def test_extract_html_kraever_html_tekst():
    html, meta = mcp_apps.extract_html({"contents": [{
        "uri": "ui://x", "mimeType": mcp_apps.MCP_APP_MIME,
        "text": "<html><body>ok</body></html>", "_meta": {"ui": {"x": 1}},
    }]})
    assert "<body>ok" in html
    assert meta["ui"]["x"] == 1
    with pytest.raises(ValueError):
        mcp_apps.extract_html({"contents": [{"mimeType": "application/json", "text": "{}"}]})


def test_harden_html_lukker_netvaerk_og_bevarer_dokumentet():
    out = mcp_apps.harden_html("<html><head><title>x</title></head><body>hej</body></html>")
    assert "Content-Security-Policy" in out
    assert "connect-src 'none'" in out
    assert out.index("Content-Security-Policy") < out.index("<title>")
