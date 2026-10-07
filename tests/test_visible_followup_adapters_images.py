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
    """`_append_image_message` blev 29/9-2026 delt i to: `_billed_besked`
    laver beskeden, `_billeder_efter_tool_svarene` placerer dem. Delingen ER
    rettelsen — placeringen kunne ikke aendres saa laenge den var bundet til
    det enkelte resultat."""
    from core.services.visible_followup_adapters import _billed_besked
    besked = _billed_besked(_exchange().results[0])
    assert besked is not None
    assert besked["role"] == "user"
    blokke = _billedblokke([besked])
    assert len(blokke) == 1
    assert blokke[0]["image_url"]["url"] == _URL


def test_uden_billede_er_stroemmen_uroert():
    """Standardmodellen er blind. Saa skal beskederne vaere byte-identiske."""
    from core.services.visible_followup_adapters import (
        _billed_besked, _billeder_efter_tool_svarene)
    assert _billed_besked(_exchange(url="").results[0]) is None
    messages: list[dict] = [{"role": "tool", "content": "x"}]
    foer = list(messages)
    _billeder_efter_tool_svarene(messages, [])
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


# ── Billedet maa ikke staa MELLEM tool-svarene (29/9-2026) ──────────────────
#
# OpenAI-protokollen kraever at ALLE tool-svar foelger umiddelbart efter
# assistent-beskeden. Billedet blev appendet lige efter DET resultat der bar
# det, saa en runde med flere vaerktoejskald fik:
#
#     assistant (2 tool_calls) -> tool c1 -> user (billedet) -> tool c2
#
# DeepSeek afviste med HTTP 400: «An assistant message with 'tool_calls' must
# be followed by tool messages responding to each 'tool_call_id'.»
#
# Maalt paa CT105: 28 afbrudte ture over to doegn, foerste gang 28/9 kl. 12:50
# — da billederne begyndte at naa modellen. Det ramte kun naar han LAESTE et
# billede OG kaldte mindst ét vaerktoej mere i samme runde, og lignede derfor
# et udbyder-udfald.


def _to_kald_hvor_det_foerste_bar_et_billede():
    from core.services.visible_followup_events import ToolExchange, ToolResult
    return ToolExchange(
        text="", reasoning_content="",
        tool_calls=[
            {"id": "c1", "type": "function",
             "function": {"name": "read_attachment", "arguments": "{}"}},
            {"id": "c2", "type": "function",
             "function": {"name": "bash", "arguments": "{}"}},
        ],
        results=[
            ToolResult(tool_call_id="c1", tool_name="read_attachment",
                       content="et billede", image_data_url=_URL),
            ToolResult(tool_call_id="c2", tool_name="bash", content="ok"),
        ],
    )


def _adaptere():
    from core.services.visible_followup_adapters import (
        OllamaFollowupAdapter, OpenAICompatFollowupAdapter)
    for K in (OpenAICompatFollowupAdapter, OllamaFollowupAdapter):
        yield K.__name__, K.__new__(K)


def test_alle_tool_svar_kommer_UBRUDT_efter_assistenten():
    """Selve protokol-kravet. Et enkelt `user` imellem giver HTTP 400."""
    for navn, a in _adaptere():
        ud = a._serialize_exchanges([_to_kald_hvor_det_foerste_bar_et_billede()])
        roller = [m["role"] for m in ud]
        assert roller == ["assistant", "tool", "tool", "user"], f"{navn}: {roller}"


def test_hvert_tool_call_id_faar_sit_svar_INDEN_noget_andet():
    """Det er praecis det DeepSeek klager over: «insufficient tool messages
    following tool_calls». Testen taeller svarene FOER foerste ikke-tool."""
    for navn, a in _adaptere():
        ud = a._serialize_exchanges([_to_kald_hvor_det_foerste_bar_et_billede()])
        kald_ids = {t["id"] for t in ud[0]["tool_calls"]}
        svaret = set()
        for m in ud[1:]:
            if m["role"] != "tool":
                break
            svaret.add(m["tool_call_id"])
        assert svaret == kald_ids, f"{navn}: {svaret} mod {kald_ids}"


def test_modellen_SER_stadig_billedet():
    """Rettelsen maa ikke loese protokollen ved at smide pixels vaek — det var
    hele grunden til at beskeden findes."""
    for navn, a in _adaptere():
        ud = a._serialize_exchanges([_to_kald_hvor_det_foerste_bar_et_billede()])
        billeder = [m for m in ud if m["role"] == "user"]
        assert len(billeder) == 1, navn
        dele = billeder[0]["content"]
        assert any(d.get("image_url", {}).get("url") == _URL for d in dele), navn


def test_FLERE_billeder_i_samme_runde_kommer_alle_med_og_i_raekkefoelge():
    from core.services.visible_followup_events import ToolExchange, ToolResult
    ex = ToolExchange(
        text="", reasoning_content="",
        tool_calls=[{"id": f"c{i}", "type": "function",
                     "function": {"name": "read_attachment", "arguments": "{}"}}
                    for i in (1, 2, 3)],
        results=[
            ToolResult(tool_call_id="c1", tool_name="read_attachment",
                       content="a", image_data_url=_URL + "1"),
            ToolResult(tool_call_id="c2", tool_name="bash", content="b"),
            ToolResult(tool_call_id="c3", tool_name="read_attachment",
                       content="c", image_data_url=_URL + "3"),
        ],
    )
    for navn, a in _adaptere():
        ud = a._serialize_exchanges([ex])
        assert [m["role"] for m in ud] == \
            ["assistant", "tool", "tool", "tool", "user", "user"], navn
        urls = [d["image_url"]["url"] for m in ud if m["role"] == "user"
                for d in m["content"] if "image_url" in d]
        assert urls == [_URL + "1", _URL + "3"], f"{navn}: {urls}"


def test_uden_billeder_er_stroemmen_UROERT():
    """Den almindelige runde maa ikke aendre sig af rettelsen."""
    from core.services.visible_followup_events import ToolExchange, ToolResult
    ex = ToolExchange(
        text="", reasoning_content="",
        tool_calls=[{"id": "c1", "type": "function",
                     "function": {"name": "bash", "arguments": "{}"}}],
        results=[ToolResult(tool_call_id="c1", tool_name="bash", content="ok")],
    )
    for navn, a in _adaptere():
        ud = a._serialize_exchanges([ex])
        assert [m["role"] for m in ud] == ["assistant", "tool"], navn


def test_billeder_blandes_ikke_paa_tvaers_af_UDVEKSLINGER():
    """Hver runde har sin egen liste. Deltes den, ville runde 2 faa runde 1's
    billeder med igen — og historikken ville aendre sig mellem kald."""
    for navn, a in _adaptere():
        ud = a._serialize_exchanges([_to_kald_hvor_det_foerste_bar_et_billede()] * 2)
        assert [m["role"] for m in ud] == [
            "assistant", "tool", "tool", "user",
            "assistant", "tool", "tool", "user"], navn
