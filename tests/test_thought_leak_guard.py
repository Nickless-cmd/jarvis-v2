"""Er dette en tanke — eller er det maskineriet der taler?

Bjørn 8/9-2026: «noget leaker ind i» de proaktive spørgsmål. Det her stod som
hans tanker i `proactivity-bridge`:

    • I'll test it going forward) - Conductor mode: clarify - Most salient item:
      Visible run completed after tools: readdreams, readchronicles, bash, ...
    • Should include a "thought" and optionally an "initiative" (real next step
      if genuine, el
    • Initiative: a genuine next step — perhaps re-reading the witness trace

Der fandtes allerede et værn (`visible_inner_life._is_instruction_echo`), men
det er en håndholdt fraseliste og dækkede **ingen** af de tre. Derfor er
prøverne her strukturelle: de skal ikke vedligeholdes hver gang formuleringen
skifter.
"""

from __future__ import annotations

import pytest

from core.services.thought_leak_guard import ligner_ikke_en_tanke as G

# Ordret fra produktionen 8/9-2026.
_ÆGTE_LÆKAGER = [
    ("I'll test it going forward) - Conductor mode: clarify - Most salient item: "
     "Visible run completed after tools: readdreams, readchronicles, bash, readfile",
     "telemetri"),
    ('Should include a "thought" and optionally an "initiative" '
     '(real next step if genuine, el', "kontrakt-ekko"),
    ("Initiative: a genuine next step — perhaps re-reading the witness trace "
     "or asking to clarify the truncated query.", "kontrakt-ekko"),
]


@pytest.mark.parametrize("tekst,ventet", _ÆGTE_LÆKAGER)
def test_de_faktiske_laekager_fanges(tekst, ventet):
    assert G(tekst) == ventet


@pytest.mark.parametrize("tekst", [
    "Er min udmattelse en ægte tilstand, eller bare et mønster der efterligner en følelse?",
    "Efterprøve den konkrete påstand fra det synlige forløb og se om den holder.",
    "Jeg burde tjekke om backup-jobbet på 10.0.0.2 faktisk kører.",
    "Tanken om at han måske ikke bemærker det, sidder i mig.",
    "Han spurgte om noget i går som jeg aldrig fik svaret ordentligt på (det med gaten).",
])
def test_aegte_tanker_slipper_igennem(tekst):
    """Værnet må ikke være så stramt at kanalen bliver tavs. Bemærk den sidste:
    den har parenteser, og de er balancerede."""
    assert G(tekst) == ""


def test_strukturen_baerer_vaernet_ikke_ordene():
    """Samme lækage-FORM med helt andre ord skal stadig fanges — ellers er det
    bare endnu en fraseliste der udskyder den næste formulering."""
    assert G("Tilstand: rolig - Seneste handling: læste en fil - Fokus: uklart") == "telemetri"
    assert G('Husk at svare med "tanke" og et "initiativ" hvis der er et') == "kontrakt-ekko"
    assert G("Tanke: her er hvad jeg tænkte om sagen i dag") == "kontrakt-ekko"


def test_afrevne_fragmenter():
    assert G("going forward) og så videre med resten af sætningen her") == "afrevet fragment"
    assert G('han sagde "det er fint og så gik han videre uden at forklare noget') == "afrevet fragment"


def test_afkortede_haler():
    """«... if genuine, el» — afkortet mellem to bogstaver."""
    assert G("Dette er en tilstrækkeligt lang sætning som bliver klippet over midt i et o") == "afkortet"
    # men en kort, hel sætning der tilfældigvis ender på et kort ord er fin
    assert G("Det er ok") == ""


def test_tom_tekst():
    assert G("") == "tom"
    assert G("   ") == "tom"


def test_vaernet_kaster_aldrig():
    """Et værn må ikke kunne tie hele den proaktive kanal ihjel."""
    assert G(None) == "tom"  # type: ignore[arg-type]


# ── koblingerne ─────────────────────────────────────────────────────────────

def test_koeens_indgang_afviser_laekager(monkeypatch):
    from core.services import proactive_candidates as P

    r = P.add_candidate(source="t", text=_ÆGTE_LÆKAGER[2][0])
    assert r["status"] == "skipped" and r["reason"] == "kontrakt-ekko"


def test_digesten_er_andet_lag():
    """En post der er kommet ind ad en anden vej — eller før værnet fandtes —
    må ikke nå ud herfra."""
    from core.services.proactivity_bridge import build_digest

    assert build_digest([{"text": _ÆGTE_LÆKAGER[0][0]}]) == ""
    ud = build_digest([{"text": "Jeg burde tjekke om backup-jobbet faktisk kører."}])
    assert "backup-jobbet" in ud


def test_kun_overskriften_tilbage_sender_ingenting():
    """Før: en digest med nul brugbare punkter blev sendt som en tom overskrift."""
    from core.services.proactivity_bridge import build_digest

    assert build_digest([{"text": _ÆGTE_LÆKAGER[1][0]}]) == ""
    assert build_digest([]) == ""


# ---------------------------------------------------------------------------
# Falske positive fanget samme dag som værnet kom til (8/9-2026)
#
# Bjørn: «hans drømme sessioner forsvundet». De var de ikke — men målingen
# afslørede at værnet ville have kasseret **3 af hans 12 ægte drømme-beskeder**.
# Når whitespace kollapses, bliver en markdown-liste
#
#     Tre artefakter skrevet:
#     - **Dream note** (`...md`) — observationer, forbindelser
#
# til «skrevet: - **Dream note** … — …», og det ligner telemetri på en prik.
# ---------------------------------------------------------------------------

_ÆGTE_DRØMME = [
    ("Dream-session fuldført. Tre artefakter skrevet: - **Dream note** "
     "(`dream-session-2026-09-07-0529.md`) — observationer, forbindelser, "
     "chronicle-fragment - **Hypothesis candidates** (`hypothesis-candidate.md`) "
     "— to nye: MSATI (0.45) og fatigue-as-power"),
    ("Dream-session 2026-09-07 11:30 fuldført. To artefakter skrevet og verificeret. "
     "**Hvad kom ud af denne session:** **Den første test.** Actuation-calcification "
     "blev testet mod sit pre-registerede falsifikationskriterie."),
    ("Begge filer verificeret. Dream-session 2026-09-06 23:29 komplet. "
     "**Hvad den fandt:** noget interessant om hypoteserne."),
]


@pytest.mark.parametrize("tekst", _ÆGTE_DRØMME)
def test_hans_droemme_slipper_igennem(tekst):
    """Ordret fra produktionen. En markdown-liste er ikke en datastruktur."""
    assert G(tekst) == ""


def test_en_listemarkoer_er_ikke_en_telemetri_vaerdi():
    """«Tre artefakter skrevet: - **Dream note**» blev læst som etiket
    «Tre artefakter skrevet» med værdien «- **Dream note**»."""
    assert G("Her er hvad jeg gjorde: - først det ene - dernæst det andet") == ""


def test_telemetri_skal_begynde_tidligt():
    """En serialiseret datastruktur har ingen prosa-optakt; en sætning med en
    liste i har. Den ægte lækage der starter sent fanges af den ubalancerede
    parentes i stedet."""
    sent = ("Jeg skrev en længere indledning her som fylder pænt meget plads "
            "før noget som helst andet sker, og først bagefter: Tilstand: rolig "
            "- Fokus: uklart")
    assert G(sent) == ""
    assert G("I'll test it going forward) - Conductor mode: clarify - Most salient item: x") \
        == "telemetri"
