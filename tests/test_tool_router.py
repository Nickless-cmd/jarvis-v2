"""Kernens rangering: tidsgraensen og bruger-dimensionen.

To ting maales her, begge fra 29/9-2026.

1. `_always_core_set` afgraensede med `datetime('now','-7 days')`, som giver
   MELLEMRUM mellem dato og tid. `events.created_at` er ISO med 'T', og 'T'
   (84) sorterer efter mellemrum (32) — saa hele graensedoegnet slap igennem.
   Maalt paa produktionsbasen: 59.779 raekker mod 58.686 med den rigtige form.
   Samme faelde ramte tre andre maalinger samme doegn.

2. Kernen er ÉN global liste uden bruger-dimension. `kald_pr_bruger` svarer
   ikke paa hvad kernen skal vaere — den goer det muligt at SE om der
   overhovedet er forskellige saet, foer nogen skaerer kassen efter ét
   menneskes uge.
"""
import json
import sqlite3
from contextlib import contextmanager

import pytest

from core.services import tool_router


def _base(raekker):
    """En base med `events` og de givne (kind, created_at, payload)-raekker."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, "
              "created_at TEXT, payload_json TEXT)")
    for kind, ts, p in raekker:
        c.execute("INSERT INTO events (kind, created_at, payload_json) VALUES (?,?,?)",
                  (kind, ts, json.dumps(p)))
    c.commit()
    return c


@contextmanager
def _forbind(c):
    yield c


def test_graensen_sammenlignes_i_KOLONNENS_egen_form(monkeypatch):
    """Den praecise fejl: en raekke fra graensedoegnets MORGEN maa ikke med.

    Graensen er «for 7 dage siden, paa dette klokkeslet». En ISO-raekke fra
    samme dato men 8 timer tidligere er AELDRE og skal udenfor. Med en
    mellemrums-graense sorterer raekkens 'T' efter graensens mellemrum paa
    plads 10, og den slap ind uanset klokkeslettet.

    Raekkerne skrives med SQLites egne udtryk, saa de altid ligger rigtigt i
    forhold til `now` — en fast dato ville holde op med at maale noget den dag
    testen bliver gammel.
    """
    c = _base([])
    c.execute("INSERT INTO events (kind, created_at, payload_json) VALUES "
              "('tool.invoked', replace(datetime('now','-1 hours'),' ','T')||'+00:00', ?)",
              (json.dumps({"tool": "ny"}),))
    c.execute("INSERT INTO events (kind, created_at, payload_json) VALUES "
              "('tool.invoked', replace(datetime('now','-7 days','-8 hours'),' ','T')||'+00:00', ?)",
              (json.dumps({"tool": "for_gammel"}),))
    c.commit()
    monkeypatch.setattr(tool_router, "connect", lambda: _forbind(c))
    monkeypatch.setattr("core.services.tool_tagger.get_pinned_set", lambda: set())
    kerne = tool_router._always_core_set(10)
    assert "ny" in kerne, "en frisk raekke faldt ud — graensen er for stram"
    assert "for_gammel" not in kerne, (
        "graensedoegnets aeldre raekke slap igennem — mellemrum mod 'T' igen")


def test_en_raekke_LIGE_inden_for_vinduet_kommer_med(monkeypatch):
    """Kontrol mod det modsatte: rettelsen maa ikke bare skaere en dag af.
    En raekke fra 7 dage siden PLUS en time er inde og skal taelle med."""
    c = _base([])
    c.execute("INSERT INTO events (kind, created_at, payload_json) VALUES "
              "('tool.invoked', replace(datetime('now','-7 days','+1 hours'),' ','T')||'+00:00', ?)",
              (json.dumps({"tool": "lige_indenfor"}),))
    c.commit()
    monkeypatch.setattr(tool_router, "connect", lambda: _forbind(c))
    monkeypatch.setattr("core.services.tool_tagger.get_pinned_set", lambda: set())
    assert "lige_indenfor" in tool_router._always_core_set(10)


def test_kald_pr_bruger_skiller_to_brugere_ad(monkeypatch):
    """Selve formaalet: kan man overhovedet se to forskellige vaerktoejssaet?"""
    c = _base([
        ("tool.invoked", "2026-09-29T10:00:00+00:00", {"tool": "bash", "user_id": "a"}),
        ("tool.invoked", "2026-09-29T10:01:00+00:00", {"tool": "bash", "user_id": "a"}),
        ("tool.invoked", "2026-09-29T10:02:00+00:00", {"tool": "home_assistant", "user_id": "b"}),
    ])
    monkeypatch.setattr(tool_router, "connect", lambda: _forbind(c))
    ud = tool_router.kald_pr_bruger(dage=3650)
    assert ud == {"a": {"bash": 2}, "b": {"home_assistant": 1}}


def test_kald_uden_bruger_havner_i_UKENDT_og_forsvinder_ikke(monkeypatch):
    """63 % af eventene manglede feltet da det blev maalt. Falder de ud af
    taellingen, ligner et hul et resultat."""
    c = _base([
        ("tool.invoked", "2026-09-29T10:00:00+00:00", {"tool": "bash"}),
        ("tool.invoked", "2026-09-29T10:01:00+00:00", {"tool": "bash", "user_id": "a"}),
    ])
    monkeypatch.setattr(tool_router, "connect", lambda: _forbind(c))
    ud = tool_router.kald_pr_bruger(dage=3650)
    assert ud == {"UKENDT": {"bash": 1}, "a": {"bash": 1}}


def test_kald_pr_bruger_taeller_kun_tool_invoked(monkeypatch):
    """Andre event-familier maa ikke smitte af paa en vaerktoejstaelling."""
    c = _base([
        ("tool.invoked", "2026-09-29T10:00:00+00:00", {"tool": "bash", "user_id": "a"}),
        ("tool.completed", "2026-09-29T10:00:01+00:00", {"tool": "bash", "user_id": "a"}),
        ("runtime.agentic_round_start", "2026-09-29T10:00:02+00:00", {"tool": "bash", "user_id": "a"}),
    ])
    monkeypatch.setattr(tool_router, "connect", lambda: _forbind(c))
    assert tool_router.kald_pr_bruger(dage=3650) == {"a": {"bash": 1}}


def test_en_doed_base_giver_tomt_svar_og_ikke_en_undtagelse(monkeypatch):
    """Rapporten maa ikke kunne braekke det den rapporterer om."""
    @contextmanager
    def _brudt():
        raise sqlite3.OperationalError("no such table: events")
        yield
    monkeypatch.setattr(tool_router, "connect", _brudt)
    assert tool_router.kald_pr_bruger() == {}


def test_routeren_sender_sin_egen_korte_deadline(monkeypatch):
    """Et timeout i routeren er et FRAVALG, ikke en fejl: den gaar videre med
    kerne-vaerktoejerne frem for at lade turen staa stille i 15 sekunder.

    Maalt 6/10-2026: 243 af 1.650 beslutninger ventede 15.197 ms og fik NUL
    picks. Prisen for at miste picks er 1,4 procentpoint hoejere
    `load_more`-rate; prisen for at vente er 55-88 minutter om ugen.
    """
    from core.services import tool_router as tr

    set_t = {}

    def _top_k(q, k=30, timeout_s=None):
        set_t["timeout_s"] = timeout_s
        return []

    monkeypatch.setattr("core.services.tool_embeddings.top_k_similar", _top_k)
    monkeypatch.setattr(tr, "_persist", lambda *a, **k: None)
    tr.select_tools(user_message="hvor ligger pfsense-noeglen",
                    session_id="s", lane="visible", run_id="r")
    assert set_t["timeout_s"] == 4.0, \
        f"routeren brugte {set_t.get('timeout_s')!r} i stedet for sin egen deadline"


def test_et_timeout_giver_stadig_et_brugbart_vaerktoejssaet(monkeypatch):
    """Degraderingen fandtes i forvejen — den skal BLIVE der. Fejler embeddet,
    maa routeren ikke returnere tomt; den skal give kerne-vaerktoejerne."""
    from core.services import tool_router as tr

    def _boom(q, k=30, timeout_s=None):
        raise TimeoutError("embed tog for lang tid")

    monkeypatch.setattr("core.services.tool_embeddings.top_k_similar", _boom)
    monkeypatch.setattr(tr, "_persist", lambda *a, **k: None)
    sel = tr.select_tools(user_message="hvor ligger pfsense-noeglen",
                          session_id="s", lane="visible", run_id="r")
    assert sel.selected_names, "et timeout maa ikke efterlade turen uden vaerktoejer"
    assert not sel.embedding_picks, "der kan ikke vaere picks naar embeddet fejlede"
