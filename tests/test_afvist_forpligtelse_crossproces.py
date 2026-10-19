"""En afvist forpligtelse skal kunne BEVISES — også når runnet kører i en anden proces.

## Hullet, målt 19/10-2026

Rutinen fyrede i `jarvis-runtime` (8011), Bjørns tur kørte i `jarvis-api`
(8080). Run-guarden afviste korrekt, posten blev skrevet — og stod derefter med
`verificeret_ejer='ukendt'`. `kandidater()` springer alt over hvor ejeren ikke
er `jarvis`, så posten var hverken gate eller vækning. Loggen lovede det
modsatte.

Årsagen er strukturel: `verificeret_jarvis_run` krævede at run-id'et matchede
`aktivt_run_id()` — en ContextVar i DENNE proces. Et ægte run-id fra den anden
proces kunne derfor aldrig verificeres, uanset hvor ægte det var.

## Hvorfor den eksisterende test ikke fangede det

`test_afvist_forpligtelse.py` har en autouse-fixture der patcher
`aktivt_run_id` til et fast run-id. Den måler altså samme-proces-vejen, som
netop er den der virker i test og ikke i drift. Det er samme familie som de
øvrige målefælder: en grøn test der ikke rører det den påstår at værne om.

Testene her patcher i stedet den DELTE journal og lader `aktivt_run_id` være
tom — præcis som i runtime-processen.
"""
from __future__ import annotations

import pytest

from core.services import inbox_state


@pytest.fixture(autouse=True)
def _tom_kontekst(monkeypatch):
    """Som i runtime-processen: ingen ContextVar kender det kørende run."""
    monkeypatch.setattr(
        "core.services.session_context_resolve.aktivt_run_id",
        lambda standard="": standard,
    )


def _journal(monkeypatch, poster):
    from core.services import in_flight_runs

    monkeypatch.setattr(in_flight_runs, "levende_koersler", lambda **_kw: poster)


def _post(run_id="visible-2ab8", bruger="bjorn", status="running"):
    return {
        "run_id": run_id,
        "session_id": "chat-e82192",
        "status": status,
        "force_user_id": bruger,
    }


def test_run_i_den_delte_journal_beviser_ejerskab(monkeypatch):
    """Det ægte tilfælde: runnet kører i api, posten skrives i runtime."""
    _journal(monkeypatch, [_post()])
    assert inbox_state.verificeret_jarvis_run("visible-2ab8", "bjorn") is True


def test_et_run_for_en_anden_bruger_loefter_ikke(monkeypatch):
    """Beviset er runnets bruger — ikke bare at runnet findes."""
    _journal(monkeypatch, [_post(bruger="michelle")])
    assert inbox_state.verificeret_jarvis_run("visible-2ab8", "bjorn") is False


def test_et_opdigtet_run_id_afvises_stadig(monkeypatch):
    """Spoofing-værnet må ikke være blevet en åben dør."""
    _journal(monkeypatch, [_post()])
    assert inbox_state.verificeret_jarvis_run("visible-opdigtet", "bjorn") is False


def test_et_afsluttet_run_taeller_ikke(monkeypatch):
    """Kun et LEVENDE run er et bevis; en efterladt række er ikke."""
    _journal(monkeypatch, [_post(status="done")])
    assert inbox_state.verificeret_jarvis_run("visible-2ab8", "bjorn") is False


def test_uden_bruger_stempel_taeller_runnet_ikke(monkeypatch):
    """Tom `force_user_id` = intet bevis. Fail-closed."""
    _journal(monkeypatch, [_post(bruger="")])
    assert inbox_state.verificeret_jarvis_run("visible-2ab8", "bjorn") is False


def test_en_braekket_journal_loefter_ikke(monkeypatch):
    """Self-safe: en ulæselig journal må undlade at løfte, ikke gætte."""
    from core.services import in_flight_runs

    def _boom(**_kw):
        raise RuntimeError("journalen kunne ikke læses")

    monkeypatch.setattr(in_flight_runs, "levende_koersler", _boom)
    assert inbox_state.verificeret_jarvis_run("visible-2ab8", "bjorn") is False


def test_samme_proces_vejen_virker_uaendret(monkeypatch):
    """Regressionen: den oprindelige vej må ikke være blevet svækket."""
    monkeypatch.setattr(
        "core.services.session_context_resolve.aktivt_run_id",
        lambda standard="": "visible-lokal",
    )
    monkeypatch.setattr(inbox_state, "_autentificeret_bruger_matcher", lambda uid: uid == "bjorn")
    assert inbox_state.verificeret_jarvis_run("visible-lokal", "bjorn") is True
    assert inbox_state.verificeret_jarvis_run("visible-lokal", "michelle") is False


def test_parkeringen_bruger_den_delte_journal_som_faldback(monkeypatch):
    """Kæden: uden ContextVar skal `parker_forpligtelse` selv finde runnet."""
    from core.services import run_guard

    monkeypatch.setattr(run_guard, "levende_run_i_session", lambda _s: "visible-fra-journalen")
    monkeypatch.setattr(inbox_state, "_ejer_id", lambda: "bjorn")
    set_kald = {}

    def _falsk_registrer(**kw):
        set_kald.update(kw)
        return {"status": "ok"}

    monkeypatch.setattr(inbox_state, "registrer_kilde", _falsk_registrer)
    run_guard.parker_forpligtelse(
        origin="recurring", session_id="chat-e82192", beskrivelse="medicin"
    )
    assert set_kald["oprettende_run_id"] == "visible-fra-journalen"
    assert set_kald["kildetype"] == "afvist_run"
    assert set_kald["bloker"] is True


def test_contextvar_vinder_over_journalen(monkeypatch):
    """Er runnet kendt lokalt, er det det mest præcise svar."""
    from core.services import run_guard

    monkeypatch.setattr(
        "core.services.session_context_resolve.aktivt_run_id",
        lambda standard="": "visible-lokal",
    )
    monkeypatch.setattr(run_guard, "levende_run_i_session", lambda _s: "visible-fra-journalen")
    monkeypatch.setattr(inbox_state, "_ejer_id", lambda: "bjorn")
    set_kald = {}
    monkeypatch.setattr(
        inbox_state, "registrer_kilde", lambda **kw: set_kald.update(kw) or {"status": "ok"}
    )
    run_guard.parker_forpligtelse(
        origin="recurring", session_id="chat-e82192", beskrivelse="medicin"
    )
    assert set_kald["oprettende_run_id"] == "visible-lokal"


# ── En VÆKNING må ikke parkere sin egen prompt (19/10-2026) ──────────────────
#
# Målt i drift: fire døde poster på fem dage (2996, 3325, 4097, 4601). En
# afvist `inbox`-vækning skrev en DUBLET af den post den var ved at løfte —
# med `oprettende_run_id=''`, altså `verificeret_ejer='ukendt'` og
# `kraever_handling=0`. `kandidater()` kræver `jarvis`, så posten kunne
# hverken gate eller løftes: en død post der lovede handling for evigt.
#
# `wakeup` har samme form — en self-wakeup er booket og fyrer igen.
# `recurring` er ÉN aflevering og SKAL parkeres, ellers går den tabt.


@pytest.fixture
def _parkering(monkeypatch):
    """Fanger parkerings-kaldet i stedet for at skrive i den ægte indbakke."""
    kald: list[dict] = []

    def _fake_parker(**kwargs):
        kald.append(kwargs)
        return {"status": "ok", "post": {"id": "test"}}

    monkeypatch.setattr(
        "core.services.run_guard.parker_forpligtelse", _fake_parker
    )
    return kald


def _afvis(monkeypatch, origin: str) -> bool:
    """Kør starteren med en vagt der ALTID afviser, og returnér dens svar."""
    from core.services import visible_autonomous_run as var

    monkeypatch.setattr(
        "core.services.run_guard.blokeringsgrund",
        lambda _origin, _session: "levende_run_i_session:test",
    )
    return var.start_autonomous_run(
        "en besked", session_id="chat-test", origin=origin
    )


@pytest.mark.parametrize("origin", ["inbox", "wakeup"])
def test_en_afvist_vaekning_parkerer_ikke_sin_egen_prompt(
    monkeypatch, _parkering, origin
):
    """Kilden ligger allerede i indbakken — en kopi ville være en død post."""
    assert _afvis(monkeypatch, origin) is False
    assert _parkering == [], f"{origin} skrev en dubleret post"


@pytest.mark.parametrize("origin", ["recurring", "scheduled"])
def test_en_afvist_rutine_parkerer_stadig(monkeypatch, _parkering, origin):
    """Én aflevering: uden parkeringen ville forpligtelsen gå tabt."""
    assert _afvis(monkeypatch, origin) is False
    assert len(_parkering) == 1, f"{origin} tabte sin forpligtelse"
    assert _parkering[0]["origin"] == origin
    assert _parkering[0]["session_id"] == "chat-test"
