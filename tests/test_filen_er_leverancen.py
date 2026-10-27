"""Filen er leverancen — fra det øjeblik svaret opstår (27/10-2026).

Seks fejlformer blev fundet i samme kæde den 27/10. Den fælles rod: agentens
svar blev behandlet som PROSA der skulle klippes (400 → 350 → 450 → 500 → 70
tegn), ikke som en FIL der kunne peges på. Hver grænse var rimelig isoleret set;
hver gang lå kontrakten — agentens egen `DÆKNING`-linje — i halen der røg.

Infrastrukturen fandtes hele tiden: `agent_artifacts` med path/size/sha256,
`write_artifact`, `read_artifact` og ejer-kontrol. Det der manglede var
KOBBLINGEN, og den var brudt i alle tre led:

1. `write_terminal_artifacts` skrev filen men satte ALDRIG
   `agent_runs.artifact_path`. Maalt: feltet var tomt i **1613 af 1613** rækker,
   selv naar `final.txt` laa paa disken.
2. `_agent_run_row_to_dict` projicerede ikke kolonnen. Projektionen er den
   ENESTE vej fra række til flade — en kolonne der ikke projiceres er en kolonne
   ingen kan læse, uanset hvad der staar i DB.
3. `scout_inbox_delivery` GÆTTEDE stien (`artifact_root()/agent_id/run_id`) i
   stedet for at læse den. Gættet fejlede to gange i træk: først som RELATIV
   sti, derefter som peger paa et værktøj der ikke findes (`get_agent`).

En gættet sti kan drive fra virkeligheden. En skrevet kan ikke.
"""

from pathlib import Path

from core.services.scout_inbox_delivery import record_scout_completion


# ── Kobling 2: projektionen ───────────────────────────────────────────────────


def test_projektionen_baerer_artifact_path_og_fejlfelterne():
    """En kolonne der ikke projiceres kan ingen flade læse.

    `artifact_path` peger paa selve leverancen; `error_code`/`error_phase` siger
    HVORFOR en kørsel fejlede. Alle tre fandtes i schemaet og blev skrevet til
    DB — og faldt derefter ud i projektionen.
    """
    from core.runtime.db_agent_runtime import create_agent_run, get_agent_run, update_agent_run

    create_agent_run(run_id="run-proj-1", agent_id="agent-proj-1", status="failed")
    update_agent_run(
        "run-proj-1",
        artifact_path="/tmp/eksempel/final.txt",
        error_code="AGENT_INCOMPLETE",
        error_phase="delivery",
    )

    r = get_agent_run("run-proj-1")
    assert r is not None
    assert r["artifact_path"] == "/tmp/eksempel/final.txt", (
        "artifact_path skal projiceres — ellers naar stien aldrig en flade"
    )
    assert r["error_code"] == "AGENT_INCOMPLETE"
    assert r["error_phase"] == "delivery"


# ── Kobling 1: skrivevejen ───────────────────────────────────────────────────


def test_terminal_artefakt_skriver_stien_paa_raekken(monkeypatch, tmp_path):
    """Rækken skal bære filen fra det øjeblik svaret opstår.

    Ikke en sti nogen har regnet sig til bagefter — den fil der FAKTISK blev
    skrevet, med dens faktiske indhold.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    from core.runtime.db_agent_artifacts import ensure_artifact_tables, write_terminal_artifacts
    from core.runtime.db_agent_contract import _conn

    conn = _conn()
    ensure_artifact_tables(conn)
    # Rækken oprettes gennem SAMME forbindelse som `write_terminal_artifacts`
    # læser fra. `create_agent_run` går gennem runtime-modulets `connect()`, og
    # en UPDATE der rammer nul rækker fejler IKKE — så en kryds-forbindelses
    # test ville være grøn af den forkerte grund. (Målt 27/10: første forsøg
    # fejlede netop sådan, med `intet run at gemme artefakter for`.)
    conn.execute(
        "INSERT OR REPLACE INTO agent_runs (run_id, agent_id, status, assignment_id,"
        " created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("run-art-1", "agent-art-1", "starting", "asg-art-1",
         "2026-10-27T00:00:00+00:00", "2026-10-27T00:00:00+00:00"),
    )
    conn.commit()

    svar = "Summary: svaret.\n\nDÆKNING: 1"
    write_terminal_artifacts(
        agent_id="agent-art-1", assignment_id="asg-art-1", owner_user_id="bjorn",
        status="completed", reply=svar, summary="kort", error_code="", error_phase="",
    )

    row = conn.execute("SELECT artifact_path FROM agent_runs WHERE run_id=?",
                       ("run-art-1",)).fetchone()
    assert row is not None, "test-setup: raekken skal findes i den laesende forbindelse"
    sti = str(row[0] or "")
    assert sti, "raekken skal baere leverancen — feltet blev aldrig skrevet foer 27/10"
    p = Path(sti)
    assert p.is_absolute(), "en relativ sti kan en modtager uden for ~/.jarvis-v2 ikke aabne"
    assert p.exists(), "pegeren maa ikke pege i tomme luft"
    assert "DÆKNING" in p.read_text(encoding="utf-8"), (
        "filen skal baere kontrakten — det er hele grunden til at pege paa den"
    )


# ── Kobling 3: læsevejen ─────────────────────────────────────────────────────


def _surface(run_extra: dict | None = None, agent_id="agent-1", run_id="run-1"):
    run = {"run_id": run_id, "output_summary": "delvis svar"}
    run.update(run_extra or {})
    return {
        "agent_id": agent_id,
        "role": "researcher",
        "tool_policy": "read-only-runtime",
        "status": "failed",
        "goal": "E2E",
        "context": {"user_id": "bjorn"},
        "latest_run": run,
    }


def _fang(monkeypatch):
    from core.services import inbox_state

    fanget: dict[str, object] = {}

    def _reg(**kw):
        fanget.update(kw)
        return {"status": "ok"}

    monkeypatch.setattr(inbox_state, "registrer_kilde", _reg)
    return fanget


def test_inbox_laeser_stien_fra_raekken_frem_for_at_gaette(monkeypatch, tmp_path):
    """Den stærkeste vagt: filen ligger hvor gættet ALDRIG ville lede.

    Det gamle gæt var `artifact_root()/agent_id/run_id/final.txt`. Her lægges
    filen i en helt anden mappe, og rækken bærer dens sti. Finder posten den,
    er stien læst — ikke gættet. Gættede koden stadig, ville `output_sti` være
    tom, fordi den gættede mappe ikke findes.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    aegte = tmp_path / "helt-andet-sted" / "svar.txt"
    aegte.parent.mkdir(parents=True)
    aegte.write_text("DÆKNING: 1", encoding="utf-8")

    fanget = _fang(monkeypatch)
    assert record_scout_completion(_surface({"artifact_path": str(aegte)})) is True

    assert fanget.get("output_sti") == str(aegte), (
        "posten skal arve den SKREVNE sti — ikke en sti den selv har regnet sig til"
    )
    assert fanget.get("output_bytes") == aegte.stat().st_size
    assert str(aegte) in str(fanget.get("beskrivelse") or "")


def test_inbox_falder_tilbage_til_gættet_for_gamle_raekker(monkeypatch, tmp_path):
    """Rækker fra før feltet blev udfyldt har tom `artifact_path`.

    De skal stadig kunne leveres — men kun naar filen faktisk ligger det
    forventede sted. Fallback'en er bagudkompatibilitet, ikke standardvejen.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    mappe = tmp_path / ".jarvis-v2/state/agent-artifacts/agent-1/run-1"
    mappe.mkdir(parents=True)
    svar = mappe / "final.txt"
    svar.write_text("gammelt svar", encoding="utf-8")

    fanget = _fang(monkeypatch)
    assert record_scout_completion(_surface()) is True

    assert fanget.get("output_sti") == str(svar), (
        "en raekke uden artifact_path skal stadig kunne finde sin fil"
    )
