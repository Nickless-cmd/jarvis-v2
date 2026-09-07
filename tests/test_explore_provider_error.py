"""En udbyder-fejl er ikke et fund (Bjørn 7/9-2026).

`explore` returnerede «lægeerklæringsskabelon» og «Hi! How can I assist you
today?» som research. Målt var det ikke hallucination og ikke manglende
værktøjer — det var udbyderens egen kvote-besked leveret som modellens indhold
med HTTP 200, gemt som `result` og markeret `completed`.
"""
from unittest.mock import patch

from core.tools.simple_tools_native import _exec_explore

KVOTE = ("Sorry, to prevent abuse of free resources, accounts that have not been "
         "recharged can only try 10 times. You can increase the free quota after "
         "recharging; https://console.aihubmix.com/topup")


def _spawn(messages, **extra):
    svar = {"agent_id": "agent-1", "messages": messages}
    svar.update(extra)
    return patch("core.services.agent_runtime.spawn_agent_task", return_value=svar)


def test_kvotebesked_er_en_fejl_ikke_et_fund():
    with _spawn([{"direction": "agent->jarvis", "kind": "provider-error", "content": KVOTE}],
                status="failed"):
        r = _exec_explore({"query": "hvor bor explore?"})
    assert r["status"] == "error"
    assert "kom ikke igennem" in r["error"]
    assert "findings" not in r


def test_et_aegte_fund_kommer_stadig_igennem():
    with _spawn([{"direction": "agent->jarvis", "kind": "result",
                  "content": "Defineret i simple_tools_definitions.py:257"}]):
        r = _exec_explore({"query": "hvor bor explore?"})
    assert r["status"] == "ok"
    assert "257" in r["findings"]


def test_fund_vinder_over_en_senere_udbyderfejl():
    """Kom der et rigtigt svar, må en efterfølgende fejlbesked ikke slette det."""
    with _spawn([
        {"direction": "agent->jarvis", "kind": "result", "content": "fundet i X.py:12"},
        {"direction": "agent->jarvis", "kind": "provider-error", "content": KVOTE},
    ]):
        r = _exec_explore({"query": "q"})
    assert r["status"] == "ok"
    assert "X.py:12" in r["findings"]


def test_beskeder_uden_kind_regnes_stadig_som_fund():
    """Bagudkompatibilitet: ældre agent-beskeder har ingen `kind`."""
    with _spawn([{"direction": "agent->jarvis", "content": "gammelt svar"}]):
        r = _exec_explore({"query": "q"})
    assert r["status"] == "ok"
    assert r["findings"] == "gammelt svar"


def test_tomt_query_afvises_foer_der_spawnes():
    assert _exec_explore({"query": "   "})["status"] == "error"


def test_vaernet_genkender_den_aegte_streng():
    from core.services.provider_error_guard import looks_like_provider_error
    assert looks_like_provider_error(KVOTE)
    assert not looks_like_provider_error("Defineret i simple_tools_definitions.py:257")
