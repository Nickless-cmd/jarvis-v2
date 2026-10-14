"""Hvad flytter opgavens post væk fra `running` mens genoptagelsen kører?

Målt-behov 14/10-2026. Kl. 20:17:38 blev opgaven `visible-55ad6c59` genoptaget
som `visible-a8323914` (generation 1). Kl. 20:25:09 blev SAMME opgave taget
igen som `visible-ad85ab87` (generation 2) — mens generation 1 stadig kørte.
Lease-tråden er udelukket: den er målt gennem den ægte vej og fornyer med held
(`test_visible_run_recovery_dispatcher.py`). Altså må noget have flyttet
posten væk fra `running`, eller ryddet dens `recovery_owner`.

`renew_recovery_lease` kræver fire ting på én gang: posten findes via
`_record_key`, `recovery_owner` matcher, `recovery_generation` matcher, og
`status == "running"`. Denne fil måler hvilke af de fem status-skiftere i
`in_flight_runs` der kan ramme en post der er midt i et kørende genoptaget run.

De fem: `mark_interrupted`, `settle_recovering`, `settle_waiting`,
`settle_terminal` og `release_recovery_claim`.

**Hvad filen IKKE dækker (målt 14/10-2026):** ingen af testene her kalder
`renew_recovery_lease` selv. Falsifikations-forsøget — at fjerne dens
`status == "running"`-krav fra kilden — lod alle seks grønne, netop fordi
fornyelsen ikke er under test her. Kravet er dækket i
`test_visible_run_recovery_dispatcher.py` (den ægte vej). Her måles kun
*tilstandene* fornyelsen læser imod.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isolated_records(monkeypatch):
    records: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in records.items()})

    def save(value):
        records.clear()
        records.update({k: dict(v) for k, v in value.items()})

    monkeypatch.setattr(ifr, "_save", save)
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    return records


def _genoptaget_opgave(records, *, owner="100:1", lease_seconds=120.0, now=None):
    """Byg den tilstand den ÆGTE vej giver: original + genoptagelse.

    Rækkefølgen er kildens, ikke min: `mark_started` skriver opgaven, den
    forlades (`settle_recovering`), `claim_due_recovery` tager den (sætter
    `running` + owner på ORIGINALEN), og genoptagelsen journalfører sig under
    sit EGET id med opgavens id som `task_id`.
    """
    ifr.mark_started(run_id="opgave-1", session_id="s1", user_message="fix it")
    ifr.settle_recovering("opgave-1", reason="shutdown")
    krav = ifr.claim_due_recovery(owner=owner, lease_seconds=lease_seconds, now=now)
    assert krav is not None, "kravet skulle kunne tages"
    # Genoptagelsens egen post — som `stempl_genoptagelse` + `mark_started` skriver den.
    ifr.mark_started(
        run_id="genoptagelse-1",
        session_id="s1",
        user_message="fix it",
        task_id="opgave-1",
        recovery_generation=krav["recovery_generation"],
        recovery_attempt=krav["recovery_attempt"],
    )
    return krav


def test_den_aege_vej_efterlader_originalen_running_med_ejerskabet(_isolated_records):
    """Kontrollen: den ægte vej giver ORIGINALEN `running` + ejerskabet.

    Det er den tilstand lease-tråden fornyer imod. Fejler denne, måler resten
    af filen en tilstand systemet ikke producerer.
    """
    krav = _genoptaget_opgave(_isolated_records)

    original = ifr.get_record("opgave-1")
    genoptagelse = ifr.get_record("genoptagelse-1")

    assert original["status"] == "running"
    assert original["recovery_owner"] == "100:1"
    assert original["recovery_generation"] == krav["recovery_generation"]
    # Genoptagelsen bærer opgavens id, men ikke dens ejerskab.
    assert genoptagelse["task_id"] == "opgave-1"
    assert genoptagelse["recovery_owner"] == ""


def test_release_recovery_claim_rydder_ejerskabet_og_goer_opgaven_forfalden(
    _isolated_records,
):
    """`release_recovery_claim` er den ene vej der gør en KØRENDE opgave ledig.

    Den sætter `status="recovering"` og rydder `recovery_owner` — og det er
    præcis de to felter `claim_due_recovery` kigger på. Kaldes den mens
    genoptagelsen kører, kan opgaven tages igen med det samme.
    """
    t0 = datetime(2026, 10, 14, 18, 17, 38, tzinfo=UTC)
    _genoptaget_opgave(_isolated_records, now=t0)

    givet_tilbage = ifr.release_recovery_claim(
        "opgave-1", 1, owner="100:1", reason="recovery-run-terminal",
        retry_after_s=30.0, now=t0,
    )

    assert givet_tilbage is True
    original = ifr.get_record("opgave-1")
    assert original["status"] == "recovering"
    assert original["recovery_owner"] == ""
    # Backoff'en holder den: `next_attempt_at` staar 30 s frem, saa posten er
    # IKKE forfalden i samme sekund. Det er den beskyttelse der findes — og
    # den er grunden til at frigivelsen ikke straks koster en ny tur.
    assert ifr.claim_due_recovery(
        owner="200:2", now=t0 + timedelta(seconds=29)
    ) is None
    # Men naar backoff'en er ude, kan den tages — mens genoptagelsen kører.
    igen = ifr.claim_due_recovery(owner="200:2", now=t0 + timedelta(seconds=31))
    assert igen is not None, "posten blev forfalden og kan tages på ny"
    assert igen["recovery_generation"] == 2


def test_release_med_fremmed_owner_afvises(_isolated_records):
    """Modprøven: en anden ejer kan IKKE frigive vores krav.

    Uden den ville testen ovenfor ikke skelne «frigivet af os» fra «frigivet
    af hvem som helst».
    """
    _genoptaget_opgave(_isolated_records)

    afvist = ifr.release_recovery_claim(
        "opgave-1", 1, owner="999:9", reason="x", retry_after_s=30.0,
    )

    assert afvist is False
    assert ifr.get_record("opgave-1")["status"] == "running"


def test_settle_recovering_rammer_originalen_naar_den_faar_opgavens_id(
    _isolated_records,
):
    """`settle_recovering` flytter også posten væk fra `running`.

    Den kaldes fra `run_finalization` og `visible_run_recovery_coordinator` —
    begge steder hvor et run slutter. Rammer den opgavens id, er opgaven
    forfalden igen.
    """
    _genoptaget_opgave(_isolated_records)

    ifr.settle_recovering("opgave-1", reason="provider-timeout")

    original = ifr.get_record("opgave-1")
    assert original["status"] == "recovering"
    assert original["recovery_owner"] == ""
    assert ifr.claim_due_recovery(owner="200:2") is not None


def test_settle_terminal_lukker_opgaven_og_rydder_ejerskabet(_isolated_records):
    """`settle_terminal` er den legitime udgang — men den rydder også ejerskabet.

    Den er ikke en fejl: et terminalt udfald SKAL lukke opgaven. Den står her
    fordi den er den ene af de fem der efterlader posten ikke-forfalden, og
    forskellen mellem den og `release_recovery_claim` er hele spørgsmålet.
    """
    _genoptaget_opgave(_isolated_records)

    ifr.settle_terminal("opgave-1", status="completed", reason="done")

    original = ifr.get_record("opgave-1")
    assert original["status"] == "completed"
    assert original["recovery_owner"] == ""
    # Terminal = IKKE forfalden. Det er forskellen.
    assert ifr.claim_due_recovery(owner="200:2") is None


def test_et_udloebet_lejemaal_uden_fornyelse_goer_opgaven_forfalden(_isolated_records):
    """Den tredje vej: ingen rører posten — lejemaalet udløber af sig selv.

    Det er den hypotese der stod tilbage efter lease-tråden blev udelukket.
    Målt her uden at vente 120 sekunder: `now` flyttes forbi udløbet.
    """
    t0 = datetime(2026, 10, 14, 18, 17, 38, tzinfo=UTC)
    _genoptaget_opgave(_isolated_records, lease_seconds=120.0, now=t0)

    # Inden udløb: ingen kan tage den.
    assert ifr.claim_due_recovery(
        owner="200:2", now=t0 + timedelta(seconds=119)
    ) is None

    # Efter udløb: den er forfalden — uden at nogen har rørt posten.
    igen = ifr.claim_due_recovery(owner="200:2", now=t0 + timedelta(seconds=121))
    assert igen is not None
    assert igen["recovery_generation"] == 2
    # Og originalen stod `running` HELE tiden — det er hele pointen.
    assert ifr.get_record("opgave-1")["status"] == "running"
