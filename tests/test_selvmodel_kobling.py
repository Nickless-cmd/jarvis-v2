"""Selvmodellens lodrette skive: fra hans svar til hans prompt (spec §8).

Falsk eventbus og falsk billig model — ingen netværk, ingen ægte bruger-id'er.
"""
from __future__ import annotations

import pytest

LANG = ("Jeg har tænkt over det, og jeg mener ærligt talt at et ærligt nul er mere værd "
        "end et smukt tal. " * 4)


class _Bus:
    def __init__(self):
        self.rows: list[dict] = [{"id": 100, "kind": "runtime.x", "payload": {}}]

    def recent(self, limit=50):
        return list(reversed(self.rows))[:limit]

    def recent_since_id(self, after_id, *, limit=100):
        return [r for r in self.rows if r["id"] > after_id][:limit]

    def svar(self, session_id, tekst, role="assistant"):
        nid = self.rows[-1]["id"] + 1
        self.rows.append({"id": nid, "kind": "channel.chat_message_appended",
                          "payload": {"session_id": session_id,
                                      "message": {"id": f"m{nid}", "role": role, "content": tekst}}})


@pytest.fixture
def k(isolated_runtime, monkeypatch):
    from core.services import selvmodel_kobling as k
    bus = _Bus()
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod.event_bus, "recent", bus.recent)
    monkeypatch.setattr(bus_mod.event_bus, "recent_since_id", bus.recent_since_id)
    monkeypatch.setattr(k, "er_taendt", lambda: True)
    monkeypatch.setattr(k, "_ejer_id", lambda: "ejer-1")
    brugere = {"s-ejer-1": "ejer-1", "s-ejer-2": "ejer-1", "s-gæst": "gæst-9"}
    monkeypatch.setattr(k, "samtalens_kilde", lambda sid: None if sid.startswith("auto-")
                        else ("nominering" if brugere.get(sid) == "ejer-1" else "anden_bruger"))
    kald: list[str] = []
    svar = '[{"emne": "ærlige tal", "udsagn": "Jeg mener et ærligt nul er mere værd end et smukt tal."}]'
    monkeypatch.setattr(k, "_kald_billig_model", lambda prompt: (kald.append(prompt), svar)[1])
    monkeypatch.setattr(k, "_kald", [])
    k._bus, k._kald_log = bus, kald
    return k


def test_foerste_poll_starter_fra_nu_og_gennemgaar_ikke_historikken(k):
    k._bus.svar("s-ejer-1", LANG)
    assert k.poll_en_gang() == 0
    assert k._kald_log == []


def test_samme_holdning_i_to_ejer_samtaler_naar_hele_vejen_til_prompten(k):
    """Ende-til-ende (spec §8.1): svar → nominering → korroborering → prompt."""
    from core.services import selvmodel
    k.poll_en_gang()  # sæt pegepinden
    k._bus.svar("s-ejer-1", LANG)
    assert k.poll_en_gang() == 1
    assert selvmodel.aktive() == []          # én samtale er ikke nok
    k._bus.svar("s-ejer-2", LANG)
    k.poll_en_gang()
    [t] = selvmodel.aktive()
    assert t["udsagn"] == "Jeg mener et ærligt nul er mere værd end et smukt tal."
    assert set(t["samtaler"]) == {"s-ejer-1", "s-ejer-2"}
    tekst = selvmodel.prompt_sektion()
    assert "et ærligt nul" in tekst and "2 samtaler" in tekst


def test_hans_egne_brugerbeskeder_og_korte_svar_nomineres_ikke(k):
    k.poll_en_gang()
    k._bus.svar("s-ejer-1", LANG, role="user")
    k._bus.svar("s-ejer-1", "Ok, gjort.")
    k.poll_en_gang()
    assert k._kald_log == []


def test_autonome_samtaler_nomineres_ikke(k):
    k.poll_en_gang()
    k._bus.svar("auto-heartbeat-20260919", LANG)
    k.poll_en_gang()
    assert k._kald_log == []


def test_en_gaest_kan_kun_nominere_og_aldrig_alene_skabe_et_traek(k):
    from core.services import selvmodel
    k.poll_en_gang()
    k._bus.svar("s-gæst", LANG)
    k.poll_en_gang()
    assert selvmodel.aktive() == []


def test_loftet_pr_time_holder(k, monkeypatch):
    monkeypatch.setattr(k, "MAX_PR_TIME", 2)
    k.poll_en_gang()
    for _ in range(4):
        k._bus.svar("s-ejer-1", LANG)
    k.poll_en_gang()
    assert len(k._kald_log) == 2


def test_prompt_sektionen_vises_kun_for_ejeren(k, monkeypatch):
    from core.services import selvmodel
    selvmodel.udtryk("holdning", "tests", "Jeg synes tests skal skrives før koden.",
                     kilde="bevidst_valg", bevis="tool")
    monkeypatch.setattr("core.identity.workspace_context.current_role", lambda: "member")
    assert k.selvmodel_sektion() is None
    monkeypatch.setattr("core.identity.workspace_context.current_role", lambda: "owner")
    assert "tests skal skrives" in k.selvmodel_sektion()


def test_slukket_flag_betyder_ingen_sektion(k, monkeypatch):
    monkeypatch.setattr(k, "er_taendt", lambda: False)
    monkeypatch.setattr("core.identity.workspace_context.current_role", lambda: "owner")
    assert k.selvmodel_sektion() is None


@pytest.mark.parametrize("tekst,antal", [
    ('[{"emne": "a", "udsagn": "Jeg mener a."}]', 1),
    ('Her: [{"emne": "a", "udsagn": "x"}, {"emne": "b", "udsagn": "y"}, {"emne": "c", "udsagn": "z"}]', 2),
    ("[]", 0), ("ingen json", 0), ('[{"emne": "", "udsagn": "x"}]', 0),
])
def test_parse_nomineringer(tekst, antal):
    from core.services.selvmodel_kobling import parse_nomineringer
    assert len(parse_nomineringer(tekst)) == antal


def test_flaget_er_slukket_som_standard(isolated_runtime):
    from core.runtime.settings import load_settings
    assert load_settings().selvmodel_enabled is False
