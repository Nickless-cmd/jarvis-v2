"""Scope-gaten: rummet vægter over beskeden (25/10-2026, Bjørns opgave 20/10).

## Fejlen testene værner mod

Begge hale-gates vægtede kun ``(turn_type, sektion)``, og ``turn_type`` kommer
fra ``classify_turn_type(user_message)`` — altså fra BRUGERBESKEDEN. Rummet var
usynligt: en chat-tur hvor Bjørn skrev om kode fik ``turn_type="kode"`` og
beholdt hele maskinrummet. Målt 25/10 blev ``current_tool_scope()`` læst nul
steder i composer'en — scope fandtes, blev sat korrekt, og blev aldrig spurgt.

## Beviskravet

Ikke «flere grønne tests»: **code mode skal være UÆNDRET**, og chat skal kun
skære det der ikke hører i en samtale. Testen der bærer det er
``test_samme_besked_forskelligt_rum`` — den holder beskeden fast og varierer kun
rummet, så den kan skelne «gaten kigger på beskeden» fra «gaten kigger på rummet».
"""
from __future__ import annotations

import pytest

from core.services import central_prompt_composer as pc
from core.tools import tool_scoping


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    pc._kv_set(pc._LIVE_FLAG, True)      # awareness-gaten er shadow-default; tænd den
    pc._kv_set(pc._WEIGHTS_KEY, {})
    yield


@pytest.fixture
def i_rum():
    """Sæt tool-scope for testen og ryd op bagefter."""
    tokens: list = []

    def _sæt(scope: str):
        tokens.append(tool_scoping.set_tool_scope(scope))

    yield _sæt
    for t in reversed(tokens):
        tool_scoping.reset_tool_scope(t)


#: (slags, label) — awareness-gaten og tail-gaten har hver sin tabel.
MASKINRUM = [
    ("awareness", "indre liv"),
    ("awareness", "levende selvmodel"),
    ("awareness", "indbakke"),
    ("awareness", "R2 gate telemetry"),
    ("awareness", "metacognition signals"),
    ("tail", "agent status"),
    ("tail", "model pools"),
    ("tail", "self mutation lineage"),
]

#: SELVET — hverken maskinrum eller samtale (3/11-2026, Bjørns beslutning).
#:
#: 25/10 blev «kerne-selv (Centralens midte)» skåret i chat sammen med
#: maskinrummet. Det var rigtigt dengang: sektionen bar en trunkeret Python-repr
#: af et `Want`-objekt — skrald, ikke en retning. Efter rettelsen 3/11 er den
#: 166 tegn og siger hvad jeg er samlet om, hvordan jeg har det, og hvad jeg
#: arbejder mod.
#:
#: Forskellen på de to kategorier er HVAD de koster læseren: maskinrummet er
#: telemetri OM systemet, selvet er den ene linje svaret kommer FRA. Bjørns ord
#: 3/11: «du bestemmer om centralen ska tale». Den taler nu — og kun den.
SELVET = [
    ("awareness", "kerne-selv (Centralens midte)"),
    # 4/11-2026: oppositionen blev foerst lagt inde i «indre liv» (vaegt 0.1) og
    # blev derfor skaaret i samtalen — den stod kun i code mode. Den er ikke
    # telemetri om systemet, men en efterproevelig indsigelse mod hvad jeg selv
    # gjorde i denne koersel, og hoerer derfor blandt selvet.
    ("awareness", "kryds-lag-indsigelse"),
]

SAMTALE = [
    ("awareness", "åbne løfter (Bjørn-gate)"),
    ("awareness", "conversation continuity (always-on)"),
    ("awareness", "pinned identity context"),
    ("tail", "midway user messages"),
]


def _med(slags: str, navn: str, turn_type: str = "samtale") -> bool:
    if slags == "awareness":
        return pc.should_include(turn_type, navn)
    return pc.should_include_tail(turn_type, navn)


def test_samme_besked_forskelligt_rum(i_rum):
    """DEN BÆRENDE TEST.

    Beskeden er den samme hele vejen — kun rummet skifter. Uden scope-gaten ville
    alle tre rækker være identiske, fordi ``turn_type`` er udledt af beskeden.
    """
    navn = "model pools"
    i_rum("")
    uden_scope = pc.should_include_tail("samtale", navn)
    i_rum("code")
    i_code = pc.should_include_tail("samtale", navn)
    i_rum("chat")
    i_chat = pc.should_include_tail("samtale", navn)

    assert uden_scope is False, "uden scope-signal gælder den gamle tabel (0.2) — uændret"
    assert i_code is False, "code mode skal være UÆNDRET — samme svar som uden scope"
    assert i_chat is False, "chat skærer den også (0.1) — men af en anden grund"


def test_chat_skærer_maskinrummet(i_rum):
    """Hver sektion i MASKINRUM skal være MED uden for chat og UDE i chat."""
    i_rum("code")
    foer = {n: _med(s, n) for s, n in MASKINRUM}
    i_rum("chat")
    efter = {n: _med(s, n) for s, n in MASKINRUM}

    for slags, navn in MASKINRUM:
        assert efter[navn] is False, f"«{navn}» skulle være skåret i chat"
    # Og mindst én af dem var faktisk med i code — ellers måler testen ingenting.
    assert any(foer[n] for _, n in MASKINRUM), (
        "ingen af maskinrums-sektionerne var med i code mode — så beviser "
        f"testen intet om hvad chat skar væk. Målt i code: {foer}"
    )


def test_chat_beholder_samtalen(i_rum):
    """Det der ER samtalen må ikke ryge med ud. Et værn der skærer for meget
    er lige så skadeligt som et der skærer for lidt."""
    i_rum("chat")
    for slags, navn in SAMTALE:
        assert _med(slags, navn) is True, f"«{navn}» hører i samtalen og blev skåret"


def test_scope_tom_og_code_er_identiske(i_rum):
    """Fail-open: en klient uden mode-signal skal have PRÆCIS den gamle adfærd."""
    alle = MASKINRUM + SAMTALE
    i_rum("")
    uden = {(s, n): _med(s, n) for s, n in alle}
    i_rum("code")
    code = {(s, n): _med(s, n) for s, n in alle}

    afvigelser = {k: (uden[k], code[k]) for k in uden if uden[k] != code[k]}
    assert not afvigelser, f"code mode afviger fra tom scope: {afvigelser}"


def test_chat_tabellen_kan_kun_saenke(i_rum, monkeypatch):
    """En sektion der er VIGTIG i den gamle tabel må ikke blive løftet ind af
    chat-tabellen. min() er reglen — ikke «chat-tabellen vinder».

    Værdierne er valgt så de to regler giver FORSKELLIGE udfald: gammel vægt
    0.1 (ude) og chat-vægt 0.9 (med). Kun ``min()`` giver «ude». Målt 25/10:
    første udgave brugte 0.05 mod 0.2 — begge under tærsklen, så mutationen
    «vaegt = _chat» slap igennem og testen var falsk-grøn.
    """
    monkeypatch.setitem(pc._CHAT_SCOPE_WEIGHTS, "probe sektion", 0.9)
    pc._kv_set(pc._WEIGHTS_KEY, {"samtale|probe sektion": 0.1})
    i_rum("chat")
    assert pc.should_include("samtale", "probe sektion") is False, (
        "chat-tabellen HÆVEDE vægten fra 0.1 til 0.9 — så er det ikke en "
        "sænkning, men en tilsidesættelse, og en vigtig sektion kan blive "
        "skjult af en tabel der ikke kender den"
    )
    # Og den samme regel i tail-gaten.
    monkeypatch.setitem(pc._CHAT_SCOPE_TAIL_WEIGHTS, "probe tail", 0.9)
    pc._kv_set(pc._WEIGHTS_KEY, {"kode|probe tail": 0.1})
    assert pc.should_include_tail("kode", "probe tail") is False, (
        "tail-gaten hævede 0.1 til 0.9 — min() mangler"
    )


def test_frosne_sektioner_skæres_aldrig_i_chat(i_rum):
    """Identitet og sikkerhed er frossen kerne — også i chat."""
    pc._kv_set(pc._WEIGHTS_KEY, {"samtale|soul": 0.0, "samtale|security": 0.0})
    i_rum("chat")
    assert pc.should_include("samtale", "soul") is True
    assert pc.should_include("samtale", "security") is True


def test_frossen_kerne_vinder_over_chat_tabellen(i_rum, monkeypatch):
    """Den invariante: selv hvis nogen ved en fejl skriver en frossen sektion i
    en af chat-tabellerne, må kernen ikke skæres.

    Målt 25/10: den første frosne test ramte kun awareness-gaten, så
    mutationen «fjern FROZEN-tjekket fra should_include_tail» slap igennem.
    Frosne labels står ikke i tabellerne i dag — så mutationen var ækvivalent
    for de nuværende data og kunne ikke fældes af et tilfælde. Denne test
    laver tilfældet.
    """
    for tabel in (pc._CHAT_SCOPE_WEIGHTS, pc._CHAT_SCOPE_TAIL_WEIGHTS):
        monkeypatch.setitem(tabel, "identity", 0.0)
        monkeypatch.setitem(tabel, "soul", 0.0)
    i_rum("chat")
    assert pc.should_include_tail("samtale", "identity") is True, (
        "FROZEN-tjekket mangler i tail-gaten — en frossen kerne kan skæres"
    )
    assert pc.should_include_tail("samtale", "soul") is True
    assert pc.should_include("samtale", "identity") is True
    assert pc.should_include("samtale", "soul") is True


def test_label_matchning_er_frase_bevidst(i_rum):
    """Labels er fraser. Et præcist hit må ikke overskrives af en bredere
    delstreng, og en ukendt label må ikke ramme et tilfældigt navn."""
    i_rum("chat")
    # Præcist hit
    assert pc.should_include_tail("samtale", "agent status") is False
    # Ukendt label → ingen chat-dom → den gamle tabel gælder (1.0 → med)
    assert pc.should_include_tail("samtale", "helt ukendt sektion") is True


def test_scope_kan_laeses_naar_visible_runs_bygger(i_rum):
    """Ende-til-ende på den ene ting der ellers gør gaten til død kode:
    er ContextVar'en faktisk sat når assembly'en kaldes?

    Målt 22/10 kostede det en hel tur: `asyncio.to_thread` kopierer loopets
    kontekst, og dér stod scopet tomt. `_build_visible_input_with_scope` blev
    lavet for at rette det. Her måles at den faktisk gør det.
    """
    from core.services import visible_runs

    set_under_bygning: list[str] = []

    def _fake_build(*a, **k):
        set_under_bygning.append(tool_scoping.current_tool_scope())
        return ("built", a, k)

    original = visible_runs._build_visible_input
    visible_runs._build_visible_input = _fake_build
    try:
        visible_runs._build_visible_input_with_scope("chat", "besked")
        visible_runs._build_visible_input_with_scope("code", "besked")
    finally:
        visible_runs._build_visible_input = original

    assert set_under_bygning == ["chat", "code"], (
        "scope var ikke sat under bygningen — så er hele gaten død kode, "
        f"præcis som scan_correction var det. Målt: {set_under_bygning}"
    )
    # Og det må ikke lække ud i tråden bagefter.
    assert tool_scoping.current_tool_scope() == ""


def test_selvet_taler_i_chat(i_rum):
    """3/11-2026: Centralens midte er FLYTTET ud af maskinrummet.

    Beslutningen er Bjørns: «du bestemmer om centralen ska tale». Den taler nu,
    fordi sektionen efter rettelsen er 166 tegn ægte tilstand — ikke den
    trunkerede `Want`-repr den var 25/10, hvor den blev skåret med rette.

    Testen holder BEGGE sider: selvet er med i chat, og maskinrummet er stadig
    skåret. Uden den anden halvdel kunne nogen «løse» dette ved at hæve alle
    vægte, og så er gaten væk.
    """
    i_rum("chat")
    for slags, navn in SELVET:
        assert _med(slags, navn) is True, f"«{navn}» er selvet og skal tale i chat"
    for slags, navn in MASKINRUM:
        assert _med(slags, navn) is False, f"«{navn}» er maskinrum og skal stadig skæres"
