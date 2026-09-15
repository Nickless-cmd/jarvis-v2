"""En crash-dræbt kørsel blev aldrig genoptaget — af TRE grunde.

## Målt 14/9-2026

I basen står 25 `runtime.visible_run_interrupted`-events. I den levende
direktørs 744 spor er der NUL om en afbrudt kørsel. Genoptagelsen har aldrig
fyret én eneste gang.

Bjørn: «Ja den skal ihf. Ikk død! Et run må aldrig død..» og «Tag dem».

## Grund 1 — eventet udgives før nogen lytter

Genstart-loggen, i rækkefølge:

    21:44:33  jarvis-runtime: session_boot_reconciler   ← stempler de døde
    21:44:34  jarvis-runtime: living_executive: listener started

`event_bus.subscribe()` lægger i en liste i PROCESSEN. Genopretteren — den
eneste der finder crash-dræbte kørsler — kører et sekund før lytteren
abonnerer, så eventet udgives til en tom abonnent-liste. Det er ikke et
kapløb; det er en fast rækkefølge, og den kan ikke vindes.

Derfor indhenter lytteren ved start: den læser afbrydelserne fra DB'en (som
er delt på tværs af processer) i stedet for at stole på at have været til
stede i det rigtige sekund.

## Grund 2 — nedkølingen behandlede «tabt arbejde» som ÉN ting

Nøglen var konstanten `"visible-run-interrupted"` med 900 sekunder. To
forskellige kørsler der dør tre minutter fra hinanden gav derfor ÉN
genoptagelse — og den anden blev droppet uden spor.

Målt i hans egne tal, i nedkølingens eget 15-minutters vindue:

| tabte kørsler i vinduet | vinduer |
|---|---|
| 1 | 191 |
| 2 | 31 |
| 3 | 10 |
| 4 | 6 |
| 5 | 4 |
| 6 | 2 |
| 17 | 1 |

54 af 245 vinduer (22%) havde mere end én. Lagt sammen: 111 af 356 tabte
kørsler kunne aldrig være blevet genoptaget. Nøglen står nu på kørslens id.
En nedkøling skal afvise DET SAMME tabte arbejde to gange — ikke tabt arbejde
i almindelighed.

## Grund 3 — genoptagelsen sagde ikke hvilken kørsel

Prompten var «Resume from interrupted visible run: {summary}». Uden id kan
den vækkede umuligt vide hvad der skal genoptages.

## Og loftet

Det ene vindue med 17 er grunden til at nøglen pr. kørsel ikke kan stå alene:
en masse-død ville ellers planlægge 17 vækninger på én gang. Loftet er derfor
5 pr. vindue — men det er IKKE tavst. At droppe uden spor er præcis den fejl
det hele handler om.
"""
from __future__ import annotations

import pytest

from core.services import living_executive as lex


@pytest.fixture(autouse=True)
def _ren_tilstand(monkeypatch):
    """Tilstanden i hukommelsen, så prøven aldrig rører hans rigtige."""
    bod: dict = {}

    def _load(key, default):
        return bod.get(key, default) if isinstance(bod.get(key), dict) else dict(default)

    def _save(key, value):
        bod[key] = value

    monkeypatch.setattr(lex, "load_json", _load)
    monkeypatch.setattr(lex, "save_json", _save)
    return bod


@pytest.fixture
def vaekninger(monkeypatch):
    """Fanger de planlagte vækninger i stedet for at vække ham."""
    kaldt: list[dict] = []

    def _falsk(**kw):
        kaldt.append(dict(kw))
        return {"status": "ok", "wakeup": {"wakeup_id": f"w{len(kaldt)}"}}

    import core.services.self_wakeup as sw
    monkeypatch.setattr(sw, "schedule_self_wakeup", _falsk)
    return kaldt


def _afbrudt(run_id: str, *, event_id: int = 1) -> dict:
    return {
        "id": event_id,
        "kind": "runtime.visible_run_interrupted",
        # Resuméet maa IKKE naevne run_id: foerste udgave skrev «doede i
        # visible-ccc», og saa bestod prompt-testen paa sin egen fixture i
        # stedet for paa koden. Den var tom og saa groen ud.
        "payload": {"run_id": run_id, "summary": "gik i staa", "error": ""},
    }


# ───────────────────────────────────────────── nedkoelingen skelner koersler

def test_TO_forskellige_koersler_giver_TO_genoptagelser(vaekninger):
    """Bjørn: «Tag dem». Før gav to crash tre minutter fra hinanden ÉN."""
    lex.process_event(_afbrudt("visible-aaa", event_id=1))
    lex.process_event(_afbrudt("visible-bbb", event_id=2))
    assert len(vaekninger) == 2, vaekninger


def test_SAMME_koersel_to_gange_giver_kun_ÉN(vaekninger):
    """Nedkølingen skal stadig virke — den skal bare virke på det rigtige."""
    lex.process_event(_afbrudt("visible-aaa", event_id=1))
    lex.process_event(_afbrudt("visible-aaa", event_id=2))
    assert len(vaekninger) == 1, vaekninger


def test_uden_run_id_deles_den_gamle_faelles_noegle(vaekninger):
    """Fejlretningen: kan vi ikke bevise at de er forskellige, så lad være med
    at gange genoptagelserne op. Tavshed er ikke belæg."""
    u = {"id": 1, "kind": "runtime.visible_run_interrupted",
         "payload": {"summary": "ukendt"}}
    lex.process_event(u)
    lex.process_event(dict(u, id=2))
    assert len(vaekninger) == 1, vaekninger


def test_genoptagelsen_naevner_HVILKEN_koersel(vaekninger):
    """Uden id kan den vækkede ikke vide hvad der skal genoptages."""
    lex.process_event(_afbrudt("visible-ccc"))
    assert "visible-ccc" in str(vaekninger[0].get("prompt") or "")


# ────────────────────────────────────────────────────────── indhentningen

def test_lytteren_indhenter_det_der_skete_FOER_den_abonnerede(monkeypatch, vaekninger):
    """Den ægte årsag: genopretteren stempler kl. :33, lytteren abonnerer
    kl. :34. Eventet udgives til en tom liste."""
    monkeypatch.setattr(lex, "_afbrudte_fra_db",
                        lambda **kw: [_afbrudt("visible-foer", event_id=7)])
    ud = lex.indhent_forsoemte_afbrydelser()
    assert len(vaekninger) == 1, vaekninger
    assert ud["genoptaget"] == 1


def test_indhentningen_genoptager_ALDRIG_den_samme_to_gange(monkeypatch, vaekninger):
    """Ellers ville hver genstart genoptage hele historikken forfra."""
    monkeypatch.setattr(lex, "_afbrudte_fra_db",
                        lambda **kw: [_afbrudt("visible-foer", event_id=7)])
    lex.indhent_forsoemte_afbrydelser()
    lex.indhent_forsoemte_afbrydelser()
    assert len(vaekninger) == 1, vaekninger


def test_indhentningen_tager_dem_ALLE_ikke_kun_den_foerste(monkeypatch, vaekninger):
    monkeypatch.setattr(lex, "_afbrudte_fra_db", lambda **kw: [
        _afbrudt("visible-a", event_id=1), _afbrudt("visible-b", event_id=2),
        _afbrudt("visible-c", event_id=3),
    ])
    lex.indhent_forsoemte_afbrydelser()
    assert len(vaekninger) == 3, vaekninger


# ───────────────────────────────────────────────────────────────── loftet

def test_et_massedoedsfald_har_et_loft(monkeypatch, vaekninger):
    """Ét vindue i hans historik havde 17. Sytten vækninger er ikke en
    redning, det er et stormløb."""
    monkeypatch.setattr(lex, "_afbrudte_fra_db", lambda **kw: [
        _afbrudt(f"visible-{i}", event_id=i) for i in range(17)
    ])
    lex.indhent_forsoemte_afbrydelser()
    assert len(vaekninger) == lex._MAKS_GENOPTAG_PR_VINDUE, len(vaekninger)


def test_loftet_er_IKKE_tavst(monkeypatch, vaekninger, _ren_tilstand):
    """At droppe uden spor er præcis den fejl det hele handler om."""
    monkeypatch.setattr(lex, "_afbrudte_fra_db", lambda **kw: [
        _afbrudt(f"visible-{i}", event_id=i) for i in range(17)
    ])
    lex.indhent_forsoemte_afbrydelser()
    spor = (_ren_tilstand.get("living_executive") or {}).get("traces") or []
    ramt = [t for t in spor if t.get("status") == "capped"]
    assert ramt, [t.get("status") for t in spor]


# ─────────────────────────────────────────────────────── og KALDER den nogen?

def test_lytter_start_kalder_indhentningen(monkeypatch):
    """Mutationen der overlevede: fjern kaldet fra `start_listener`, og alle
    ni andre tests blev grønne.

    De måler funktionen ved selv at kalde den — og en test der selv leverer
    inputtet kan aldrig se at INGEN leverer det. Det er husets hyppigste fejl,
    og her ville den have genindført præcis den fejl vi retter: mekanismen
    findes, kalderen mangler.
    """
    kaldt: list[int] = []
    monkeypatch.setattr(lex, "indhent_forsoemte_afbrydelser",
                        lambda **kw: kaldt.append(1) or {"set": 0, "genoptaget": 0})
    monkeypatch.setattr(lex, "_LISTENER_THREAD", None)
    try:
        lex.start_listener()
        assert kaldt, "start_listener indhenter ikke det der skete foer den lyttede"
    finally:
        lex.stop_listener()


# ───────────────────────────────────── selve forespoergslen, mod en RIGTIG base

@pytest.fixture
def base(monkeypatch):
    """En rigtig sqlite. De ovenstående tests udskifter `_afbrudte_fra_db`, så
    forespørgslen selv står utestet — og det er netop det led der kan give et
    stille nul (kind stavet forkert, tidsvinduet vendt om, halen skjult af et
    blankt limit)."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, "
                 "payload_json TEXT, created_at TEXT)")

    class _Uden:
        def __enter__(self): return conn
        def __exit__(self, *a): return False

    import core.runtime.db as db
    monkeypatch.setattr(db, "connect", lambda: _Uden())
    return conn


def _laeg(conn, eid, kind, run_id, minutter_siden):
    import json
    conn.execute(
        "INSERT INTO events (id, kind, payload_json, created_at) "
        "VALUES (?,?,?, datetime('now', ?))",
        (eid, kind, json.dumps({"run_id": run_id}), f"-{minutter_siden} minutes"),
    )


def test_forespoergslen_tager_kun_afbrydelser(base):
    """Ét bogstav galt i arten giver nul rækker og ingen fejl."""
    _laeg(base, 1, "runtime.visible_run_interrupted", "visible-a", 2)
    _laeg(base, 2, "runtime.visible_run_completed", "visible-b", 2)
    ud = lex._afbrudte_fra_db()
    assert [e["payload"]["run_id"] for e in ud] == ["visible-a"]


def test_forespoergslen_lader_det_gamle_ligge(base):
    """Målt på hans base inden deploy: ét event i et 24-timers vindue, en
    autonom kørsel fra i GÅR. Det er ikke afbrudt arbejde, det er historie."""
    _laeg(base, 1, "runtime.visible_run_interrupted", "visible-ny", 5)
    _laeg(base, 2, "runtime.visible_run_interrupted", "visible-gammel", 300)
    ud = lex._afbrudte_fra_db()
    assert [e["payload"]["run_id"] for e in ud] == ["visible-ny"]


def test_forespoergslen_giver_AELDST_foerst(base):
    """Så loftet rammer de nyeste sidst, og sporet står i dødsrækkefølge."""
    _laeg(base, 1, "runtime.visible_run_interrupted", "visible-foerst", 9)
    _laeg(base, 2, "runtime.visible_run_interrupted", "visible-sidst", 1)
    ud = lex._afbrudte_fra_db()
    assert [e["payload"]["run_id"] for e in ud] == ["visible-foerst", "visible-sidst"]


# ───────────────────────── opstarts-fejning var ikke nok (målt 15/9-2026)

def test_lytteren_fejer_LOEBENDE_ikke_kun_ved_opstart(monkeypatch):
    """Den ægte hændelse: jeg genstartede jarvis-api, som udgav
    «api-nedlukning» for Bjørns kørsel — og lytteren bor i jarvis-runtime, som
    IKKE blev genstartet. Eventet lå i DB'en, ingen så det, og hans besked blev
    aldrig genoptaget.

    Event-bussens abonnenter er process-lokale; DB'en er den delte sandhed. En
    lytter der kun kigger ved sin egen opstart er blind for alt hvad den ANDEN
    proces udgiver imens.
    """
    import queue as _q
    import time as _t

    fejet: list[int] = []
    monkeypatch.setattr(lex, "indhent_forsoemte_afbrydelser",
                        lambda **kw: fejet.append(1) or {"set": 0, "genoptaget": 0})
    monkeypatch.setattr(lex, "_FEJE_INTERVAL_S", 0.0)

    kø: _q.Queue = _q.Queue()
    lex._LISTENER_STOP.clear()

    def _stop_snart():
        _t.sleep(0.25)
        lex._LISTENER_STOP.set()
        kø.put(None)

    import threading
    threading.Thread(target=_stop_snart, daemon=True).start()
    try:
        lex._listener_loop(kø)
    finally:
        lex._LISTENER_STOP.set()

    assert fejet, "lytteren fejede ikke mens den koerte"


def test_fejningen_har_et_interval_saa_den_ikke_hamrer_DBen():
    """Løkken tikker hvert sekund. Uden et interval ville den forespørge
    DB'en 86.400 gange i døgnet for noget der sker et par gange om ugen."""
    assert lex._FEJE_INTERVAL_S >= 30.0


def test_fejningen_holder_sin_takt_over_TID(monkeypatch):
    """Mutationen der overlevede: fjern `sidst_fejet = ...` inde i grenen.

    Så fejer den ved HVER tik efter første gang — samme skade som intet
    interval, ad en anden vej. En test på konstanten kan ikke se det, fordi
    konstanten er uændret. Takten skal måles over tid.
    """
    import queue as _q
    import threading
    from types import SimpleNamespace

    ur = {"t": 0.0}
    monkeypatch.setattr(lex, "time", SimpleNamespace(monotonic=lambda: ur["t"]))
    monkeypatch.setattr(lex, "_FEJE_INTERVAL_S", 5.0)

    fejet: list[float] = []
    monkeypatch.setattr(lex, "indhent_forsoemte_afbrydelser",
                        lambda **kw: fejet.append(ur["t"]) or {"set": 0, "genoptaget": 0})

    kø: _q.Queue = _q.Queue()
    for _ in range(20):
        kø.put({"kind": "noget.ligegyldigt", "payload": {}})

    lex._LISTENER_STOP.clear()
    rigtig_get = kø.get

    def _get_og_tik(*a, **kw):
        ur["t"] += 1.0          # ét sekund pr. tik
        v = rigtig_get(*a, **kw)
        if kø.empty():
            lex._LISTENER_STOP.set()
        return v

    monkeypatch.setattr(kø, "get", _get_og_tik)
    try:
        lex._listener_loop(kø)
    finally:
        lex._LISTENER_STOP.set()

    # 20 sekunder, interval 5 → et par gange. Uden nulstilling: ~16.
    assert 2 <= len(fejet) <= 5, f"{len(fejet)} fejninger paa 20 tik: {fejet}"


# ────────────────── er brugeren gaaet videre? (målt 15/9-2026)

@pytest.fixture
def koersels_base(monkeypatch):
    """En rigtig sqlite med visible_runs."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE visible_runs (run_id TEXT, status TEXT, "
                 "started_at TEXT, finished_at TEXT)")

    class _Uden:
        def __enter__(self): return conn
        def __exit__(self, *a): return False

    import core.runtime.db as db
    monkeypatch.setattr(db, "connect", lambda: _Uden())
    return conn


def _run(conn, rid, status, start, slut=None):
    conn.execute("INSERT INTO visible_runs VALUES (?,?,?,?)", (rid, status, start, slut))


def test_en_senere_faerdig_koersel_betyder_gaaet_videre(koersels_base):
    """Det ægte forløb: afbrudt 10:41:31, ny kørsel 10:42:03 blev færdig, og
    Bjørn havde sit svar. En genoptagelse dér er ren støj."""
    _run(koersels_base, "visible-doed", "interrupted", "2026-09-15T08:41:27", "2026-09-15T08:41:31")
    _run(koersels_base, "visible-ny", "completed", "2026-09-15T08:42:03", "2026-09-15T08:42:38")
    assert lex._allerede_besvaret("visible-doed") is True


def test_ingen_senere_koersel_betyder_IKKE_besvaret(koersels_base):
    """Den almindelige sag: noget døde om natten og ingen har været der siden.
    Den SKAL genoptages — «Et run må aldrig dø»."""
    _run(koersels_base, "visible-doed", "interrupted", "2026-09-15T08:41:27", "2026-09-15T08:41:31")
    assert lex._allerede_besvaret("visible-doed") is False


def test_en_senere_koersel_der_ogsaa_DOEDE_taeller_ikke(koersels_base):
    """To crash i træk er ikke et svar. Ellers ville den anden død dække over
    den første."""
    _run(koersels_base, "visible-doed", "interrupted", "2026-09-15T08:41:27", "2026-09-15T08:41:31")
    _run(koersels_base, "visible-ogsaa-doed", "cancelled", "2026-09-15T08:42:03", "2026-09-15T08:57:00")
    assert lex._allerede_besvaret("visible-doed") is False


def test_en_TIDLIGERE_faerdig_koersel_taeller_ikke(koersels_base):
    """Svaret skal komme EFTER døden for at være et svar på den."""
    _run(koersels_base, "visible-foer", "completed", "2026-09-15T08:30:00", "2026-09-15T08:30:20")
    _run(koersels_base, "visible-doed", "interrupted", "2026-09-15T08:41:27", "2026-09-15T08:41:31")
    assert lex._allerede_besvaret("visible-doed") is False


def test_ukendt_run_genoptages(koersels_base):
    """Fejlretningen: tvivlen falder ud til fordel for at prøve."""
    assert lex._allerede_besvaret("visible-findes-ikke") is False
    assert lex._allerede_besvaret("") is False


def test_basen_utilgaengelig_giver_GENOPTAG(monkeypatch):
    """«Et run må aldrig dø». Kan vi ikke måle, skal vi prøve — ikke tie."""
    import core.runtime.db as db
    def _knald():
        raise RuntimeError("ingen base")
    monkeypatch.setattr(db, "connect", _knald)
    assert lex._allerede_besvaret("visible-hvadsomhelst") is False


def test_indhentningen_springer_de_besvarede_over(monkeypatch, vaekninger):
    monkeypatch.setattr(lex, "_afbrudte_fra_db", lambda **kw: [
        _afbrudt("visible-gammel", event_id=1), _afbrudt("visible-frisk", event_id=2),
    ])
    monkeypatch.setattr(lex, "_allerede_besvaret", lambda rid: rid == "visible-gammel")
    ud = lex.indhent_forsoemte_afbrydelser()
    assert ud["sprunget"] == 1
    assert len(vaekninger) == 1, vaekninger
    assert "visible-frisk" in str(vaekninger[0].get("prompt") or "")
