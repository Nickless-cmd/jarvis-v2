"""To porte der holder initiativ-køen ude af arbejde der allerede er gjort.

MÅLT 24/11-2026, ugens 133 inner-voice-initiativer:

1. **Aktiv-tur-porten.** 48% blev dannet inden for 30 minutter efter en synlig
   tur. Initiativet «Søg Gmail målrettet efter Ollama-usage-mailen» blev dannet
   17:59:24 og kørt 18:01:00 — mens den synlige tur besvarede præcis det samme.
   Den kø-interne `_gentaget_paastand` kunne ikke se det: den læser KUN
   `runtime_initiatives`, altså sin egen kø.

   To andre signaler blev prøvet og forkastet samme dag, med måling:
   ord-overlap mod assistent-svar (10/14 afvist, men 6 tilfældige — «ingen»,
   «står», «plan» står i ethvert svar) og FTS via `search_chat_messages`
   (0 match af 14, fordi en hel sætning som forespørgsel kræver at ALLE led
   matcher). Tiden skiller rent; ordene gør ikke.

2. **Tilstands-porten.** Cirka halvdelen af de samme initiativer var
   selvbeskrivelser — «Jeg bliver her lidt uden at presse en plan ud af det»,
   «Der er ingen reel næste drift lige nu». De peger ikke på noget der kan
   gøres, men hvert af dem blev til et run der brugte 40.000-90.000
   input-tokens på at konkludere at der ikke var noget at lave. Kilden er
   prompten: INNER_VOICE.md beder modellen levere et `initiative`-felt med
   mindre den aktivt sætter det til null.

Testene indsætter RIGTIGE rækker i `visible_runs` i stedet for at stubbe
forbindelsen. En fake der returnerer samme svar uanset SQL kan ikke se om
`run_id NOT LIKE 'autonomous-%'`-grenen faktisk virker — og det er netop den
gren der afgør om porten tæller mine egne baggrundskørsler som «mig der taler».
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _indsæt_run(run_id: str, *, minutter_siden: float) -> None:
    """Skriv en rigtig række i visible_runs — så WHERE-grenen bliver prøvet."""
    from core.runtime.db import connect

    started = (datetime.now(UTC) - timedelta(minutes=minutter_siden)).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO visible_runs"
            " (run_id, lane, provider, model, status, started_at, finished_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                "primary",
                "deepseek",
                "deepseek-flash",
                "completed",
                started,
                started,
            ),
        )


# ── Aktiv-tur-porten ────────────────────────────────────────────────────────


def test_porten_afviser_naar_en_synlig_tur_ligen_er_startet(isolated_runtime) -> None:
    """Kernen i kravet: er jeg midt i en samtale, må køen ikke sende mig ud."""
    from core.services.initiative_queue import _aktiv_synlig_tur

    _indsæt_run("visible-test-aktiv", minutter_siden=1)

    grund = _aktiv_synlig_tur()
    assert grund, "porten skulle afvise: en synlig tur startede for et minut siden"
    assert "aktiv-synlig-tur" in grund


def test_porten_slipper_naar_turen_er_aeldre_end_vinduet(isolated_runtime) -> None:
    """Et initiativ der opstaar efter samtalen er slut, er ikke et ekko af den."""
    from core.services.initiative_queue import _AKTIV_TUR_MINUTTER, _aktiv_synlig_tur

    _indsæt_run("visible-test-gammel", minutter_siden=_AKTIV_TUR_MINUTTER + 5)

    assert _aktiv_synlig_tur() == "", (
        "porten afviste et initiativ der ligger uden for vinduet — "
        "saa bremser den arbejde der ikke er dobbelt"
    )


def test_autonome_runs_taeller_ikke_som_at_jeg_taler(isolated_runtime) -> None:
    """WHERE-grenen `run_id NOT LIKE 'autonomous-%'` er hele pointen.

    Uden den ville porten afvise altid: mine egne baggrundskoersler skriver
    ogsaa til visible_runs, saa «der er aktivitet» ville altid vaere sandt og
    porten permanent lukket. Denne test faelder netop den fejl.
    """
    from core.services.initiative_queue import _aktiv_synlig_tur

    _indsæt_run("autonomous-test-1", minutter_siden=1)

    assert _aktiv_synlig_tur() == "", (
        "en autonom koersel blev laest som «jeg taler med nogen» — "
        "saa lukker porten køen permanent"
    )


def test_porten_fejler_aabent_naar_db_ikke_svarer(isolated_runtime, monkeypatch) -> None:
    """En db-fejl må ikke blokere en ægte indskydelse — slip hellere igennem."""
    from core.runtime import db as runtime_db

    def _braek():
        raise RuntimeError("db nede")

    monkeypatch.setattr(runtime_db, "connect", _braek)
    from core.services.initiative_queue import _aktiv_synlig_tur

    assert _aktiv_synlig_tur() == "", "en db-fejl lukkede køen i stedet for at fejle aabent"


# ── Tilstands-porten ───────────────────────────────────────────────────────


def test_tilstandsbeskrivelse_er_ikke_et_initiativ(isolated_runtime) -> None:
    """«Jeg bliver her lidt» er en tilstand. Den kan ikke udføres."""
    from core.services.initiative_queue import push_initiative

    for fokus in (
        "Jeg bliver her lidt uden at presse en plan ud af det",
        "Der er ingen reel næste drift lige nu, kun en fornemmelse",
        "Jeg mærker en lingering spænding og en tilbageholdenhed",
    ):
        assert push_initiative(focus=fokus, source="inner-voice") == "", (
            f"tilstandsbeskrivelsen slap i køen som en opgave: {fokus!r}"
        )


def test_ægte_indskydelse_slipper_gennem_begge_porte(isolated_runtime, monkeypatch) -> None:
    """En konkret opgave må ikke blive kvalt af portene."""
    from core.services import initiative_queue

    monkeypatch.setattr(initiative_queue, "_aktiv_synlig_tur", lambda: "")

    iid = initiative_queue.push_initiative(
        focus="Søg Gmail målrettet efter Ollama-usage-mailen og læs tallet ud",
        source="inner-voice",
    )
    assert iid, "en konkret, verbum-styret opgave blev afvist — porten er for stram"


def test_menneskegodkendt_forslag_gaar_fri_for_aktiv_tur_porten(
    isolated_runtime,
) -> None:
    """Porten gælder kun inner-voice. Et forslag fra brugeren må ikke afvises
    fordi Jarvis tilfældigvis talte med nogen."""
    from core.services.initiative_queue import push_initiative

    _indsæt_run("visible-test-blokerer", minutter_siden=1)

    iid = push_initiative(
        focus="Undersøg hvorfor webhooken svarer 500 på andet forsøg",
        source="jarvis-tool",
        priority="high",
    )
    assert iid, "et ikke-inner-voice-forslag blev afvist af aktiv-tur-porten"


# ── Sammenhæng: porten skal være koblet på, ikke bare findes ───────────────


def test_push_initiative_spoerger_aktiv_tur_porten(isolated_runtime, monkeypatch) -> None:
    """En port der ikke bliver kaldt er teater. Denne test faelder afkoblingen."""
    from core.services import initiative_queue

    kaldt = {"n": 0}

    def _taeller() -> str:
        kaldt["n"] += 1
        return "aktiv-synlig-tur (1 ture inden for 30 min)"

    monkeypatch.setattr(initiative_queue, "_aktiv_synlig_tur", _taeller)

    iid = initiative_queue.push_initiative(
        focus="Afklar hvorfor nightly-jobbet stoppede halvvejs",
        source="inner-voice",
    )
    assert kaldt["n"] == 1, "push_initiative spoergte aldrig porten"
    assert iid == "", "porten sagde afvis, men initiativet blev alligevel oprettet"
