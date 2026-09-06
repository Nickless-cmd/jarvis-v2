"""Pixels skal overleve HELE kaeden — ikke bare blive sat.

`ToolResult` er frozen og bliver rekonstrueret fire steder. Et nyt felt der
ikke foeres med paa hver kopi doer tavst: objektet findes, men billedet naar
aldrig modellen. Det er praecis det moenster der kostede os ni fejl i nat, saa
det er kaeden der testes her, ikke feltet.
"""
from core.services.visible_followup_events import ToolExchange, ToolResult

_URL = "data:image/png;base64,AAAA"


def _exchange(url: str = _URL) -> ToolExchange:
    return ToolExchange(
        text="kigger",
        tool_calls=[{"id": "c1", "function": {"name": "read_attachment"}}],
        results=[ToolResult(tool_call_id="c1", tool_name="read_attachment",
                            content="[skaerm.png — billede vedlagt nedenfor]",
                            image_data_url=url)],
    )


def _billedblokke(messages: list[dict]) -> list[dict]:
    ud = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, list):
            ud += [b for b in c if b.get("type") == "image_url"]
    return ud


def test_billedet_naar_modellen_som_egen_besked():
    from core.services.visible_followup_adapters import _append_image_message
    messages: list[dict] = [{"role": "tool", "content": "x"}]
    _append_image_message(messages, _exchange().results[0])
    blokke = _billedblokke(messages)
    assert len(blokke) == 1
    assert blokke[0]["image_url"]["url"] == _URL
    # Billedet maa ikke ligge i tool-beskeden — protokollen tillader det ikke.
    assert messages[-1]["role"] == "user"


def test_uden_billede_er_stroemmen_uroert():
    """Standardmodellen er blind. Saa skal beskederne vaere byte-identiske."""
    from core.services.visible_followup_adapters import _append_image_message
    messages: list[dict] = [{"role": "tool", "content": "x"}]
    foer = list(messages)
    _append_image_message(messages, _exchange(url="").results[0])
    assert messages == foer


def test_ollama_komprimering_taber_ikke_billedet():
    """Komprimeringen klipper tekst — den maa ikke smide pixels vaek."""
    from core.services.visible_followup_adapters import OllamaFollowupAdapter
    komp = OllamaFollowupAdapter()._compact_exchanges([_exchange()])
    assert komp[0].results[0].image_data_url == _URL


def test_aldring_rydder_billedet_med_vilje():
    """Gamle billeder SKAL falde ud, ellers hober pixels sig op i konteksten."""
    from core.services.tool_result_aging import age_tool_results
    ude, _metrics = age_tool_results(
        [_exchange(), _exchange()],
        keep_full=1, mode="live", strength="strong", round_index=9,
    )
    # foerste udveksling er aldret ud → dens pixels skal vaere vaek
    assert ude[0].results[0].image_data_url == ""
    # den nyeste beholder sit billede
    assert ude[-1].results[0].image_data_url == _URL
