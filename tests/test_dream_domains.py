"""Det faelles emne-ordforraad for droemme-kaeden.

Kaeden foejer paa EMNE: hvert hop slaar op paa sidste segment af
`canonical_key` og leder efter et maal eller et fokus i samme emne. Maalt
25/9-2026: `danish-concise-calibration` fandtes 15.–25. maj som hypotese, som
fokus OG som 123 maal-raekker — og det er praecis derfor den sidste
adoptions-kandidat er fra 15. maj.

Navnene er derfor ikke frit valgte. Aendres et, holder det op med at moede det
der allerede baerer det.
"""
from __future__ import annotations

from core.services.dream_domains import DOMAENER, er_gyldigt_domaene


def test_de_otte_domaener_er_dem_der_staar_i_basen():
    """`capability`, `creativity`, `memory` og `identity` er i basen fra 24/9."""
    for navn in ("identity", "memory", "capability", "creativity",
                 "curiosity", "relational", "boundary", "resilience"):
        assert navn in DOMAENER, navn
    assert len(DOMAENER) == 8


def test_hvert_domaene_har_en_beskrivelse():
    """Beskrivelsen er det `dream_hypothesis_forced` skriver som summary."""
    for navn, tekst in DOMAENER.items():
        assert tekst.strip(), navn


def test_den_tvungne_producent_bruger_DETTE_ordforraad():
    """Foer 25/9 stod listen kun i `dream_hypothesis_forced`, og den var derfor
    den eneste producent der skrev et emne kaeden kunne bruge."""
    from core.services.dream_hypothesis_forced import _DOMAINS
    assert dict(_DOMAINS) == DOMAENER


def test_et_ukendt_navn_er_ikke_gyldigt():
    assert er_gyldigt_domaene("identity")
    assert not er_gyldigt_domaene("vis-mig-de-to-nye-commits-fra-claude")
    assert not er_gyldigt_domaene("")


# ── Modellen vaelger domaenet (25/9-2026) ────────────────────────────────
#
# Jeg skrev foerst en noegleords-tabel og maalte den mod de 42 raekker der
# faktisk havde naaet producenten: 10 traf, hoejst ét var rigtigt. `creativity`
# kom fra «digt» inde i «faerdig»; fire `identity` fra «dig selv» i
# «[SELF-WAKEUP FIRED] Du bad dig selv:». Med ordgraenser: 0 traf.
#
# Modellen maalt paa DE SAMME tekster: 0 af 14 fik et domaene — og det er
# rigtigt, for hver eneste er byg-ordrer, natrutiner og selv-vaekninger. Paa
# otte konstruerede tekster der FAKTISK roerer et staaende omraade ramte den 4.
# Fejlene er forvekslinger mellem nabodomaener (`relational` set som
# `boundary`), ikke falske positive paa arbejdssnak. Det er den rigtige vej at
# fejle: et forkert domaene paa en relevant tekst er mildere end et domaene paa
# en byg-ordre.

def _svar(monkeypatch, tekst: str):
    import core.services.daemon_llm as DL
    monkeypatch.setattr(DL, "daemon_llm_call",
                        lambda p, **kw: tekst)


def test_et_gyldigt_domaene_gives_videre(monkeypatch):
    from core.services.dream_domains import domaene_for_tur
    _svar(monkeypatch, '{"domaene": "memory"}')
    assert domaene_for_tur("Du glemmer hvad vi aftalte i går") == "memory"


def test_indhegnet_svar_laeses_ogsaa(monkeypatch):
    """Modellen svarer ofte med ```. Samme faelde som droemme-biasen i dag."""
    from core.services.dream_domains import domaene_for_tur
    _svar(monkeypatch, '```json\n{"domaene": "resilience"}\n```')
    assert domaene_for_tur("Det er fjerde gang samme fejl") == "resilience"


def test_none_er_det_normale_svar(monkeypatch):
    from core.services.dream_domains import domaene_for_tur
    _svar(monkeypatch, '{"domaene": "none"}')
    assert domaene_for_tur("byg den nu jeg vil teste den") is None


def test_et_navn_uden_for_ordforraadet_afvises(monkeypatch):
    """Modellen maa ikke kunne opfinde et emne — kaeden foejer paa netop de otte."""
    from core.services.dream_domains import domaene_for_tur
    _svar(monkeypatch, '{"domaene": "vis-mig-de-to-nye-commits"}')
    assert domaene_for_tur("vis mig de to nye commits") is None


def test_ulaeseligt_svar_giver_None(monkeypatch):
    from core.services.dream_domains import domaene_for_tur
    _svar(monkeypatch, "jeg ved det ikke rigtig")
    assert domaene_for_tur("en helt almindelig tur her") is None


def test_en_fejl_i_modellen_vaelter_ikke_turen(monkeypatch):
    """Kaldet ligger i en baggrundstraad efter turen — men en droemme-hypotese
    maa aldrig kunne kaste op i den kaede."""
    import core.services.daemon_llm as DL
    from core.services.dream_domains import domaene_for_tur

    def _braekker(p, **kw):
        raise RuntimeError("banen er nede")
    monkeypatch.setattr(DL, "daemon_llm_call", _braekker)
    assert domaene_for_tur("en helt almindelig tur her") is None


def test_for_kort_tekst_spoerger_slet_ikke(monkeypatch):
    """Intet kald, ingen omkostning, paa noget der ikke kan baere et domaene."""
    import core.services.daemon_llm as DL
    kaldt = []
    monkeypatch.setattr(DL, "daemon_llm_call",
                        lambda p, **kw: kaldt.append(1) or '{"domaene":"memory"}')
    from core.services.dream_domains import domaene_for_tur
    assert domaene_for_tur("hej") is None
    assert kaldt == []


# ── De to hardkodede broer (fjernet 25/9-2026) ───────────────────────────
#
# I `_domain_key_from_*` stod `if "danish-concise-calibration" in text: return
# "danish-concise-calibration"` og det samme for `avoid-repetitive-openers`.
# Virkningen var at `development-focus:communication:danish-concise-calibration`
# fik strippet sit `communication:`-segment, saa den matchede hypotesens
# `dream-hypothesis:...:danish-concise-calibration`.
#
# Det var den ENESTE grund til at droemme-kaeden nogensinde foejede noget
# sammen. Maalt: af 1125 fokus-noegler aendrede praecis TO sig da broerne kom
# vaek — netop de to. Kaeden havde aldrig et ordforraad den delte af sig selv.

_BROBYGGERE = (
    ("core.services.reflection_signal_tracking",
     ("_domain_key_from_focus", "_domain_key_from_critic")),
    ("core.services.goal_signal_tracking", ("_domain_key_from_focus",)),
    ("core.services.self_model_signal_tracking", ("_critic_limitation_key",)),
)


def test_ingen_noegle_udledning_navngiver_et_bestemt_emne():
    """AST, ikke grep: navnene staar stadig i etiketter og kommentarer.

    En ny undtagelse ville faa mekanikken til at se ud som om den virker igen.
    """
    import ast
    import importlib
    import inspect

    syndere: list[str] = []
    for modul_navn, funktioner in _BROBYGGERE:
        modul = importlib.import_module(modul_navn)
        traen = ast.parse(inspect.getsource(modul))
        for n in ast.walk(traen):
            if not isinstance(n, ast.FunctionDef) or n.name not in funktioner:
                continue
            for k in ast.walk(n):
                if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                        and k.value in {"danish-concise-calibration",
                                        "avoid-repetitive-openers"}:
                    syndere.append(f"{modul_navn}.{n.name} linje {k.lineno}: {k.value!r}")
    assert not syndere, (
        "en hardkodet bro er tilbage — saa foejer kaeden sig sammen paa en "
        f"undtagelse i stedet for paa et delt ordforraad:\n  "
        + "\n  ".join(syndere))


def test_fokus_noeglen_beholder_nu_hele_sin_sti():
    """Foer broen gav den `danish-concise-calibration`; nu det fulde omraade.

    Det er ikke en forbedring i sig selv — det er ærligheden: fokusset ER et
    kommunikations-fokus, og det moeder ikke en droemme-hypotese foer begge
    vaelger fra `DOMAENER`.
    """
    from core.services.goal_signal_tracking import _domain_key_from_focus
    assert _domain_key_from_focus(
        "development-focus:communication:danish-concise-calibration"
    ) == "communication-danish-concise-calibration"
