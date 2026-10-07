"""Steer-beskeder skal ligge i HISTORIKKEN — ikke i halen (Bjørn 7/10-2026).

Fejlen der blev maalt: én followup-besked sendt midt i en tur blev leveret som
en frisk brugerbesked i HVER efterfoelgende runde. Modellen svarede den 12
gange for én besked. Aarsagen var ikke koeen — `consume_visible_run_steers`
markerer beskeden consumed og giver den kun ÉN gang. Aarsagen var levetiden:
`tilfoej_vedvarende` betyder «resten af turen», og halen genopbygges hver
runde som `base_messages + exchanges + trailing`.

Her staar styringen i stedet i historikken (`exchanges`). Den vokser
append-only, saa styringen faar en FAST position og bliver en del af det
cachelagrede praefiks fra naeste runde. DeepSeeks praefiks-cache roeres derfor
ikke — det er hele grunden til at den ikke ligger i halen. I halen var den
ALDRIG cachelagret: den blev genopbygget og gensendt hver runde.

`run_trailing.py` dokumenterer selv prisen for den modsatte vej: da
vedvarende beskeder aendrede hvilken besked der er den sidste user-besked, gik
ét run fra hale 5.859 til 26.838 tegn og tabte 120.704 tokens genkendelse paa
én runde.
"""
from core.services.visible_followup_adapters import OllamaFollowupAdapter
from core.services.visible_followup_events import ToolExchange
from core.services.visible_run_steers import append_real_user_steers


def test_styringen_lander_i_historikken_som_user():
    exchanges: list[ToolExchange] = []
    accepted, stopped = append_real_user_steers(
        exchanges, [{"content": "  tjek filen  ", "at": "nu"}]
    )
    assert accepted == [{"content": "tjek filen", "at": "nu"}]
    assert not stopped
    assert len(exchanges) == 1
    assert exchanges[0].user_message == "tjek filen"
    assert exchanges[0].tool_calls == [] and exchanges[0].results == []


def test_afbrydelses_styring_stopper_resten():
    exchanges: list[ToolExchange] = []
    accepted, stopped = append_real_user_steers(
        exchanges, [{"content": "stop nu"}, {"content": "skal ikke naa frem"}]
    )
    assert stopped
    assert [s["content"] for s in accepted] == ["stop nu"]
    assert len(exchanges) == 1


def test_tom_styring_lægges_ikke():
    exchanges: list[ToolExchange] = []
    accepted, stopped = append_real_user_steers(exchanges, [{"content": "   "}])
    assert accepted == []
    assert not stopped
    assert exchanges == []


def test_styringen_staar_EEN_gang_i_prompten():
    """Det Bjørn ramte: én besked, mange svar. Den maa kun staa én gang."""
    adapter = OllamaFollowupAdapter()
    exchanges = [ToolExchange(text="arbejde", tool_calls=[], results=[])]
    append_real_user_steers(exchanges, [{"content": "skift retning"}])
    msgs = adapter._serialize_exchanges(exchanges)
    assert [m.get("content") for m in msgs].count("skift retning") == 1


def test_ren_styring_efterlader_ikke_tomt_assistant_turn():
    adapter = OllamaFollowupAdapter()
    exchanges: list[ToolExchange] = []
    append_real_user_steers(exchanges, [{"content": "skift retning"}])
    msgs = adapter._serialize_exchanges(exchanges)
    assert msgs == [{"role": "user", "content": "skift retning"}]


def test_positionen_er_append_only_saa_praefikset_holdes():
    """Kernen i cache-garantien.

    Naar nye runder lægges EFTER styringen, staar den paa praecis samme indeks.
    Alt op til og med den er derfor byte-identisk mellem runderne — det er
    praecis det DeepSeeks praefiks-cache genkender.
    """
    adapter = OllamaFollowupAdapter()
    exchanges = [ToolExchange(text="a", tool_calls=[], results=[])]
    append_real_user_steers(exchanges, [{"content": "skift retning"}])
    foer = adapter._serialize_exchanges(exchanges)
    idx = [m.get("content") for m in foer].index("skift retning")

    exchanges.append(ToolExchange(text="b", tool_calls=[], results=[]))
    efter = adapter._serialize_exchanges(exchanges)

    assert [m.get("content") for m in efter].index("skift retning") == idx
    assert efter[: idx + 1] == foer[: idx + 1]


def test_aldringen_dropper_ikke_styringen():
    """Aldrings-transformen bygger nye ToolExchange-objekter. Baerer den ikke
    `user_message` med, forsvinder styringen fra prompten naar gamle
    tool-resultater komprimeres."""
    from core.services.tool_result_aging import age_tool_results
    from core.services.visible_followup_events import ToolResult

    def _ex(tekst: str, *, um: str = "") -> ToolExchange:
        return ToolExchange(
            text=tekst, tool_calls=[],
            results=[ToolResult(tool_call_id="t", tool_name="bash", content="x" * 400)],
            user_message=um,
        )

    exchanges = [_ex("r0", um="skift retning")] + [_ex(f"r{i}") for i in range(1, 7)]

    aldret, _metrics = age_tool_results(
        exchanges, keep_full=5, mode="active", strength="strong", round_index=10,
    )
    assert any(ex.user_message == "skift retning" for ex in aldret)
    # Og den er faktisk blevet ombygget — ellers beviser testen intet.
    assert aldret[0] is not exchanges[0]
