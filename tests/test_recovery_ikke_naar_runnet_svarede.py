"""Recovery må ikke genoptage et run der allerede har svaret (målt 10/10-2026).

Run `visible-9a64aa1d` skrev sit svar kl. 16:48:32 og blev stemplet `interrupted`
ét sekund senere (`pending-tool-intent`). Bjørn skrev intet imens — han ventede —
så «samtalen gik videre»-værnet var falsk, og dispatcheren genoptog tre sekunder
efter. Bjørn fik to forskellige svar på én besked.

Fixet spørger RUNNET selv: har det persisteret en besked? Kilden er
`besked_run_kobling`, der binder besked→run præcist — ikke `chat_messages`, hvor
enhver proaktiv besked, morgenbrief og heartbeat-ping ville blive talt med og
droppe genoptagelser Bjørn faktisk ventede på.

MEN ET SVAR ER IKKE ALTID ET SVAR (14/10-2026)
----------------------------------------------
Bjørn: «dette værn forsætter ikk et run som designet: En tvungen slutrunde
manglede bevis for at opgaven var faerdig. Jarvis fortsaetter automatisk fra
sit checkpoint.» Varslet lovede en fortsættelse — og droppet ovenfor dræbte
den, fordi en afslutning ALTID skriver et svar. Selvmodsigelsen var indbygget:
en tvungen slutrunde kan pr. definition ikke producere det bevis policyen
kræver, og dens svar blev alligevel læst som «så er den færdig».

Grænsen er derfor trukket ved om afslutningen var SELVVALGT. Er den tvunget
eller afkortet (`forced-finalize-unverified`, `completed-truncated`,
`budget-opbrugt`, `breaker-open`), er svaret ikke beviset — og posten
genoptages. Målt samme dag: `visible-c1bafe9b` blev tvunget til slutrunde efter
18 runder, skrev sit svar, og blev droppet tre gange i én samtale.
"""
from __future__ import annotations

import pytest

from core.services import besked_run_kobling as K
from core.services import in_flight_runs as ifr
from core.services import visible_run_recovery_dispatcher as D
from core.services import visible_terminal_policy as V


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    monkeypatch.delenv("JARVIS_ENABLE_RUNTIME_SERVICES", raising=False)
    # Koblingskortet i hukommelsen, så testen ikke rører den ægte fil.
    kort: dict[str, str] = {}
    monkeypatch.setattr(K, "_laes", lambda: dict(kort))
    monkeypatch.setattr(K, "noter", lambda mid, rid: kort.__setitem__(str(mid), str(rid)))
    return poster, kort


@pytest.fixture
def spawn(monkeypatch):
    kald: list[dict] = []

    def _start(**kw):
        kald.append(kw)
        return f"visible-{len(kald)}"

    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached", _start)
    return kald


def _forladt_opgave(
    run_id: str = "visible-svar", *, besked: str = "mål latensen",
    grund: str = "shutdown",
) -> None:
    ifr.mark_started(run_id=run_id, session_id="chat-1", user_message=besked)
    ifr.settle_recovering(run_id, reason=grund, summary=grund)


def test_run_der_har_svaret_genoptages_ikke(spawn, _isolerede_poster):
    """Kernen: et run der NÅEDE at svare må ikke genoptages."""
    poster, kort = _isolerede_poster
    _forladt_opgave("visible-9a64aa1d")
    K.noter("message-1", "visible-9a64aa1d")  # runnet svarede, så blev det stemplet afbrudt

    svar = D.recover_due_once()

    assert svar["started"] == 0
    assert svar["error"] == "koerslen-svarede-selv"
    assert spawn == []


def test_run_uden_svar_genoptages_stadig(spawn, _isolerede_poster):
    """Kontrollen: uden et svar er opgaven forladt og SKAL genoptages."""
    _forladt_opgave("visible-uden-svar")

    svar = D.recover_due_once()

    assert svar["started"] == 1
    assert len(spawn) == 1
    assert spawn[0]["recovery_task_id"] == "visible-uden-svar"


def test_kobling_til_et_andet_run_blokerer_ikke(spawn, _isolerede_poster):
    """En besked fra et FREMMED run i samme kort må ikke droppe denne opgave."""
    _forladt_opgave("visible-mit")
    K.noter("message-2", "visible-et-helt-andet-run")

    svar = D.recover_due_once()

    assert svar["started"] == 1
    assert len(spawn) == 1


def test_skrev_run_er_falsk_for_ukendt_og_tom(spawn, _isolerede_poster):
    """`skrev_run` svarer False på tomt og ukendt — fail-open mod genoptagelse."""
    _poster, kort = _isolerede_poster
    K.noter("message-3", "visible-kendt")

    assert K.skrev_run("visible-kendt") is True
    assert K.skrev_run("visible-ukendt") is False
    assert K.skrev_run("") is False


# ── MEN ET SVAR ER IKKE ALTID ET SVAR (14/10-2026) ─────────────────────────


class TestSvarBeviserFaerdig:
    """Grænsen ligger ved om afslutningen var selvvalgt — ikke ved om der kom tekst."""

    @pytest.mark.parametrize("grund", sorted(V.SVAR_ER_IKKE_BEVIS))
    def test_tvungen_afslutning_er_ikke_bevis(self, grund):
        assert V.svar_beviser_faerdig(grund) is False

    @pytest.mark.parametrize("grund", ["shutdown", "pending-tool-intent", "completed"])
    def test_selvvalgt_afslutning_er_bevis(self, grund):
        assert V.svar_beviser_faerdig(grund) is True

    def test_ukendt_grund_er_bevis(self):
        """Konservativt: vi ændrer kun de grunde vi KENDER, ikke alt ukendt.

        `settle_recovering` skriver altid en grund (`unknown` i værste fald), så
        dette er et kantscenarie — og det skal bevare den gamle adfærd.
        """
        assert V.svar_beviser_faerdig("") is True
        assert V.svar_beviser_faerdig(None) is True
        assert V.svar_beviser_faerdig("noget-vi-aldrig-har-set") is True


@pytest.mark.parametrize("grund", sorted(V.SVAR_ER_IKKE_BEVIS))
def test_tvungen_afslutning_genoptages_trods_svar(spawn, _isolerede_poster, grund):
    """Kernen i 14/10-fixet: et svar fra en tvungen afslutning draeber ikke posten.

    Testen beviser OGSAA kæden fixet hviler på: `settle_recovering` gemmer
    grunden i `exit_reason`, og `claim_due_recovery` bærer den videre til
    dispatcheren. Manglede feltet, ville `svar_beviser_faerdig(None)` svare
    sandt, droppet ville fyre, og `started` ville være 0.
    """
    _forladt_opgave("visible-tvunget", grund=grund)
    K.noter("message-t", "visible-tvunget")   # runnet NÅEDE at skrive et svar

    svar = D.recover_due_once()

    assert svar["started"] == 1, f"{grund} skulle genoptages, ikke droppes"
    assert len(spawn) == 1
    assert spawn[0]["recovery_task_id"] == "visible-tvunget"


@pytest.mark.parametrize("grund", ["shutdown", "pending-tool-intent"])
def test_selvvalgt_afslutning_droppes_stadig(spawn, _isolerede_poster, grund):
    """Kontrollen mod 10/10-bug'en: her ER svaret svaret, og posten skal droppes."""
    _forladt_opgave("visible-selvvalgt", grund=grund)
    K.noter("message-s", "visible-selvvalgt")

    svar = D.recover_due_once()

    assert svar["started"] == 0
    assert svar["error"] == "koerslen-svarede-selv"
    assert spawn == []


def test_uden_svar_genoptages_tvungen_afslutning_ogsaa(spawn, _isolerede_poster):
    """Uden et svar er sagen uændret: en forladt opgave genoptages."""
    _forladt_opgave("visible-tavs", grund="forced-finalize-unverified")

    svar = D.recover_due_once()

    assert svar["started"] == 1
    assert len(spawn) == 1
