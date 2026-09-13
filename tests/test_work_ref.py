"""`work_ref` — én præfikset reference, ét sted at opløse den.

Den bærende regel er at modulet **aldrig gætter**. En reference uden præfiks
kunne være et run-id eller et task-id, og de to peger i hvert sit lager — så et
gæt ville sende en fladeslå op det forkerte sted og vise det forkerte arbejde.
"""
from __future__ import annotations

import pytest

from core.runtime import work_ref as wr


# ------------------------------------------------------------------ at bygge

def test_en_reference_baerer_sin_art():
    assert wr.lav("run", "visible-abc") == "run:visible-abc"
    assert wr.fra_run("visible-abc") == "run:visible-abc"
    assert wr.fra_task("a1b2c3") == "task:a1b2c3"


def test_arten_normaliseres():
    assert wr.lav("  RUN  ", "x") == "run:x"


def test_ukendt_art_AFVISES():
    """Et gaet ville pege paa det forkerte lager."""
    with pytest.raises(wr.UgyldigReference) as e:
        wr.lav("kaffe", "x")
    assert "ukendt art" in str(e.value)


def test_tomt_id_afvises():
    """En reference til «ingenting» ser ud som en forbindelse og foerer ingen
    steder hen — vaerre end intet felt."""
    with pytest.raises(wr.UgyldigReference):
        wr.lav("run", "")
    with pytest.raises(wr.UgyldigReference):
        wr.lav("run", "   ")


def test_id_med_skilletegn_afvises():
    """`heartbeat-tick:uuid` er praecis den form der ville braekke oploesningen
    — og den FINDES allerede i `runtime_tasks.run_id`. Uden den her kontrol
    kunne den slippe ind og goere en reference tvetydig."""
    with pytest.raises(wr.UgyldigReference) as e:
        wr.lav("heartbeat-tick", "heartbeat-tick:036bd93e")
    assert "skilletegn" in str(e.value) or ":" in str(e.value)


# ----------------------------------------------------------------- at opløse

def test_oploesning_giver_art_og_id():
    assert wr.opløs("run:visible-abc") == ("run", "visible-abc")
    assert wr.opløs("task:a1b2c3") == ("task", "a1b2c3")


def test_reference_UDEN_praefiks_afvises():
    """Den vigtigste afvisning. Et bart id kunne vaere hvad som helst."""
    with pytest.raises(wr.UgyldigReference) as e:
        wr.opløs("visible-abc")
    assert "uden art" in str(e.value)


def test_ukendt_art_i_oploesning_afvises():
    with pytest.raises(wr.UgyldigReference):
        wr.opløs("kaffe:x")


def test_tom_reference_afvises():
    for tom in ("", "   ", None):
        with pytest.raises(wr.UgyldigReference):
            wr.opløs(tom)  # type: ignore[arg-type]


def test_tomt_id_i_oploesning_afvises():
    with pytest.raises(wr.UgyldigReference):
        wr.opløs("run:")


def test_rundtur_holder():
    for art, id_ in [("run", "visible-abc"), ("task", "a1"), ("flow", "f9"),
                     ("dispatch", "d3"), ("heartbeat-tick", "036bd93e")]:
        assert wr.opløs(wr.lav(art, id_)) == (art, id_)


# ----------------------------------------------------------- til filtrering

def test_er_gyldig_fejler_ikke():
    """Steder der skal FILTRERE maa ikke skulle pakke hvert opslag i try."""
    assert wr.er_gyldig("run:x") is True
    assert wr.er_gyldig("visible-abc") is False
    assert wr.er_gyldig("") is False


def test_lager_for_peger_paa_en_kolonne():
    """En art der ikke kan opløses tilbage til en raekke er ikke en reference."""
    assert "visible_runs" in wr.lager_for("run:x")
    assert "runtime_tasks" in wr.lager_for("task:x")


def test_alle_arter_har_et_lager():
    """Vagt mod at nogen tilfoejer en art uden at sige hvor den peger hen."""
    for art, lager in wr.ARTER.items():
        assert lager.strip(), f"arten {art!r} peger ingen steder"


def test_tick_er_aerligt_markeret_som_uden_lager():
    """Et tick er et TIDSPUNKT, ikke et stykke arbejde. Den forskel er hele
    grunden til at rod og ophav er to felter og ikke ét."""
    assert "intet lager" in wr.ARTER["heartbeat-tick"]


# ─────────────────────────────────────────────────────────────────────────
# Kolonnen der løj (13/9-2026)
#
# `runtime_tasks.run_id` indeholdt ikke et run. Målt: 984 rækker, og værdien er
# `heartbeat-tick:036bd93e-…` — et TIDSPUNKT. Ingen af de øvrige opgave-skabere
# sender overhovedet en kørsel med.
#
# Så længe den hed `run_id`, løj navnet — og det er præcis den slags der koster
# en eftermiddag om et halvt år, fordi nogen joiner på den i god tro.
# ─────────────────────────────────────────────────────────────────────────

def test_kolonnen_hedder_origin_ref():
    import sqlite3
    from core.runtime.db_runtime_tasks import ensure_runtime_tasks_tables
    conn = sqlite3.connect(":memory:")
    ensure_runtime_tasks_tables(conn)
    kolonner = {r[1] for r in conn.execute("PRAGMA table_info(runtime_tasks)")}
    assert "origin_ref" in kolonner
    assert "run_id" not in kolonner, "det gamle, loegnagtige navn staar stadig"


def test_en_EKSISTERENDE_tabel_omdoebes():
    """984 raekker fandtes allerede. En migration der kun virker paa en ny
    tabel ville efterlade produktionen med det gamle navn."""
    import sqlite3
    from core.runtime.db_runtime_tasks import ensure_runtime_tasks_tables
    conn = sqlite3.connect(":memory:")
    # Skemaet som det SAA UD foer omdoebningen — ikke en forenklet udgave.
    # Foerste udgave af denne test manglede `priority`, og migrationen faldt
    # over indekset. En fikstur der ikke ligner virkeligheden proever ikke
    # virkeligheden.
    conn.execute("""CREATE TABLE runtime_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL, origin TEXT NOT NULL, status TEXT NOT NULL,
        goal TEXT NOT NULL, scope TEXT NOT NULL DEFAULT '',
        priority TEXT NOT NULL DEFAULT 'medium',
        flow_id TEXT NOT NULL DEFAULT '', session_id TEXT NOT NULL DEFAULT '',
        run_id TEXT NOT NULL DEFAULT '', owner TEXT NOT NULL DEFAULT '',
        retry_at TEXT NOT NULL DEFAULT '', blocked_reason TEXT NOT NULL DEFAULT '',
        result_summary TEXT NOT NULL DEFAULT '', artifact_ref TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    conn.execute("INSERT INTO runtime_tasks (task_id, kind, origin, status, goal, "
                 "run_id, created_at, updated_at) VALUES "
                 "('t1','k','o','queued','g','heartbeat-tick:abc','x','y')")
    ensure_runtime_tasks_tables(conn)
    kolonner = {r[1] for r in conn.execute("PRAGMA table_info(runtime_tasks)")}
    assert "origin_ref" in kolonner and "run_id" not in kolonner
    # og VÆRDIEN foelger med — en omdoebning der taber data er ikke en
    # omdoebning, det er en sletning.
    v = conn.execute("SELECT origin_ref FROM runtime_tasks WHERE task_id='t1'").fetchone()
    assert v[0] == "heartbeat-tick:abc"


def test_migrationen_er_IDEMPOTENT():
    """Den koerer ved hvert `ensure`. Var den ikke idempotent, ville anden
    opstart braekke."""
    import sqlite3
    from core.runtime.db_runtime_tasks import ensure_runtime_tasks_tables
    conn = sqlite3.connect(":memory:")
    for _ in range(3):
        ensure_runtime_tasks_tables(conn)
    kolonner = [r[1] for r in conn.execute("PRAGMA table_info(runtime_tasks)")]
    assert kolonner.count("origin_ref") == 1


def test_hooken_praefikser_et_BART_id():
    """Et bart id kunne vaere baade et tick og en koersel."""
    from core.services.runtime_hooks import _tick_ref
    assert _tick_ref("036bd93e") == "heartbeat-tick:036bd93e"
    assert _tick_ref("") == ""
    assert _tick_ref(None) == ""


def test_hooken_praefikser_IKKE_en_allerede_gyldig_reference():
    """Producenten sender ALLEREDE `heartbeat-tick:…`, og 984 raekker baerer
    den form.

    Foerste udgave af `work_ref` kaldte arten `tick` og praefiksede oveni.
    Resultatet var at `lav()` afviste vaerdien (id med skilletegn) og feltet
    blev TOMT — en regression som en EKSISTERENDE test fangede. Dataen havde
    konventionen foerst; opgaven var at foelge den, ikke at opfinde en ny.
    """
    from core.services.runtime_hooks import _tick_ref
    assert _tick_ref("heartbeat-tick:abc") == "heartbeat-tick:abc"


def test_hookens_reference_kan_OPLOESES():
    from core.services.runtime_hooks import _tick_ref
    assert wr.opløs(_tick_ref("abc")) == ("heartbeat-tick", "abc")
