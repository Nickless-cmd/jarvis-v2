"""`agent_runs`-raekken skal baere samme udfald som outbox'en (26/10-2026).

MAALT 26/10-2026 paa `asg-b0e20bf925564962`:

* `agent_result_outbox` fik `error_code=AGENT_INCOMPLETE`, `error_phase=delivery`
  af `settle_agent_status` — den vej var rettet.
* `agent_runs`-raekken havde `error_code=''` og `error_phase=''`.

To skriveveje, kun den ene rettet. `agent_runs` skrives af spawn'ens
exception-handler, og `update_agent_run` kendte hverken `error_code` eller
`error_phase` — den kunne ikke baere dem, selv hvis nogen bad den om det.

Det er ikke kosmetik: raekken er det foerste jeg slaar op i, og den sagde
ingenting. Fasen er det spor den naeste mig soeger i — `model` peger paa
udbyderen, `delivery` peger paa leverancen.

BEMAERK om testens egen faelde: `db_agent_runtime` importerer `connect` ved
import-tid, saa en monkeypatch paa `core.runtime.db.DB_PATH` rammer INGEN ting —
UPDATE'en gaar mod den rigtige base, rammer nul raekker, og testen er groen af
den forkerte grund. Den patcher derfor det symbol funktionen faktisk kalder.
"""

from __future__ import annotations

import sqlite3

import pytest


def _frisk_db(tmp_path, monkeypatch):
    """En rigtig sqlite-fil, koblet paa det `connect` funktionen kalder."""
    from core.runtime import db_agent_runtime as rt

    sti = tmp_path / "agent_runs.db"

    def _connect():
        c = sqlite3.connect(sti)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(rt, "connect", _connect, raising=False)
    with _connect() as c:
        rt._ensure_agent_runtime_tables(c)
        # 27/10-2026: workarounden er FJERNET. Den lagde selv error_code og
        # error_phase paa en frisk base, fordi `_ensure_agent_runtime_tables`
        # ikke gjorde det — og skjulte dermed praecis den schema-drift der nu
        # er rettet (fire kolonner blev lagt til). Uden workarounden maaler
        # testen baade UPDATE'en OG at skemaet er komplet.
        c.execute(
            "INSERT INTO agent_runs (run_id, agent_id, status, created_at, updated_at,"
            " error_code, error_phase) VALUES ('run-x','agent-x','running','t0','t0','','')"
        )
        c.commit()
    return sti


def _raekke(sti):
    conn = sqlite3.connect(sti)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM agent_runs WHERE run_id='run-x'").fetchone()
    conn.close()
    return dict(r)


def test_update_agent_run_kan_baere_error_code_og_fase(tmp_path, monkeypatch):
    """Den mekaniske soem: funktionen skal kunne skrive de to felter."""
    sti = _frisk_db(tmp_path, monkeypatch)
    from core.runtime.db_agent_runtime import update_agent_run

    update_agent_run(
        "run-x",
        status="failed",
        failure_reason="UFULDSTÆNDIG (2 ubesvarede spørgsmål) — agentens tekst: …",
        provider_status="failed",
        error_code="AGENT_INCOMPLETE",
        error_phase="delivery",
    )
    r = _raekke(sti)
    assert r["error_code"] == "AGENT_INCOMPLETE", f"fik {r['error_code']!r}"
    assert r["error_phase"] == "delivery", f"fik {r['error_phase']!r}"


def test_en_aegte_fejl_bliver_stadig_model():
    """Vagten skal ikke goere alt til 'delivery' — saa bliver systemet blindt."""
    from core.runtime.db_agent_contract import partial_delivery_error

    kode, fase = partial_delivery_error(full="Connection reset by peer", registry_status="failed")
    assert (kode, fase) == ("AGENT_FAILED", "model"), f"fik {(kode, fase)!r}"


def test_en_delvis_leverance_er_delivery():
    """Markeringen i teksten er det der afgoer fasen — ikke ordlyden af fejlen."""
    from core.runtime.db_agent_contract import partial_delivery_error

    kode, fase = partial_delivery_error(
        full="UFULDSTÆNDIG (2 ubesvarede spørgsmål) — agentens tekst: 5 felter.",
        registry_status="failed",
    )
    assert (kode, fase) == ("AGENT_INCOMPLETE", "delivery"), f"fik {(kode, fase)!r}"


def test_en_frisk_db_har_de_kolonner_projektionen_laeser(tmp_path, monkeypatch):
    """En frisk base skal kunne koere praecis den samme kode som den levende.

    MAALT 27/10-2026: `_ensure_agent_runtime_tables` oprettede 19 kolonner,
    men `_agent_run_row_to_dict` laeser 25. Paa den LEVENDE base var
    forskellen usynlig — kolonnerne var lagt til med ALTER andre steder — men
    en frisk base kastede `IndexError: No item with that key`, ikke KeyError.
    Det var den fejl der fik `test_update_agent_run_kan_baere_error_code_og_fase`
    til at fejle paa ren HEAD.
    """
    sti = _frisk_db(tmp_path, monkeypatch)
    from core.runtime.db_agent_runtime import get_agent_run

    run = get_agent_run("run-x")
    assert run is not None, "raekken kunne ikke laeses fra en frisk base"
    for felt in ("artifact_path", "error_code", "error_phase", "assignment_id"):
        assert felt in run, (
            f"{felt} mangler i projektionen — en frisk base kan ikke koere "
            f"den samme kode som den levende. felter: {sorted(run)}"
        )
