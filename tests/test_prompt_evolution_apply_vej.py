"""Apply-vejen for prompt-evolution (28/10-2026).

BAGGRUND. `prompt_evolution_runtime` producerede 65 forslag, hvoraf 0 blev
anvendt. Docstringen sagde «proposal-only … does not apply prompts», og det var
sandt — men der var heller ingen vej for et MENNESKE. Forslagene stod i
`runtime_self_authored_prompt_proposals` med status 'fresh' eller 'stale', og
den indsættelige sætning levede kun som hale i `rationale`, hvor den ikke kunne
skelnes fra begrundelsen.

Disse tests værner de tre led der nu findes:

1. Fragmentet persisteres i sin egen kolonne (ikke kun i prosa).
2. Executoren INDSÆTTER fragmentet — den erstatter ikke filen.
3. Et fragment der er metadata-prosa afvises, fordi det ville skrive
   systemprosa ind i prompten.

Testene rører ALDRIG den levende workspace-fil: `_workspace_path` patches til
en tmp-sti. (Målt 28/10-2026: en tidligere test skrev til den rigtige
HEARTBEAT.md fordi `JARVIS_RUNTIME_HOME` ikke bider på den funktion. Den blev
rullet tilbage, men fælden er grunden til at patchen her er eksplicit.)
"""

from __future__ import annotations

import pathlib

import pytest

from core.services import autonomy_proposal_queue as q
from core.services import prompt_mutation_loop as pml


@pytest.fixture()
def isoleret_workspace(tmp_path, monkeypatch):
    """En tmp-workspace med en HEARTBEAT.md, og _workspace_path pegende derpå."""
    shared = tmp_path / "shared"
    shared.mkdir()
    fil = shared / "HEARTBEAT.md"
    fil.write_text(
        "# HEARTBEAT\n\nStatus: enabled\nKill Switch: enabled\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(pml, "_workspace_path", lambda name: shared / name)
    # Mutation-storage skal ogsaa vaere isoleret, ellers skrives der til den
    # levende mutations-historik.
    monkeypatch.setattr(pml, "_storage_path", lambda: tmp_path / "mutations.json")
    return fil


def test_executor_registreret() -> None:
    """Kind'en skal have en executor — ellers godkender mennesket uden virkning."""
    assert "prompt-evolution" in q._PROPOSAL_EXECUTORS


def test_ukendt_forslag_giver_fejl_ikke_stille_succes() -> None:
    resultat = q._execute_prompt_evolution_proposal({"proposal_id": "findes-ikke"})
    assert resultat["status"] == "error"
    assert "not found" in resultat["error"]


def test_tomt_fragment_afvises() -> None:
    """Et forslag uden indsaettelig tekst maa ikke skrive noget som helst."""
    import core.runtime.db_runtime_self as drs

    original = drs.get_runtime_self_authored_prompt_proposal
    try:
        drs.get_runtime_self_authored_prompt_proposal = lambda pid: {
            "proposal_id": pid,
            "candidate_fragment": "",
        }
        resultat = q._execute_prompt_evolution_proposal({"proposal_id": "x"})
    finally:
        drs.get_runtime_self_authored_prompt_proposal = original

    assert resultat["status"] == "error"
    assert "no candidate_fragment" in resultat["error"]


def test_metadata_prosa_afvises() -> None:
    """«Bounded focus-nudge proposal for HEARTBEAT.md» er ikke en instruktion."""
    import core.runtime.db_runtime_self as drs

    prosa = "Bounded focus-nudge proposal for HEARTBEAT.md. Prompt target=direction-framing."
    original = drs.get_runtime_self_authored_prompt_proposal
    try:
        drs.get_runtime_self_authored_prompt_proposal = lambda pid: {
            "proposal_id": pid,
            "candidate_fragment": prosa,
        }
        resultat = q._execute_prompt_evolution_proposal({"proposal_id": "x"})
    finally:
        drs.get_runtime_self_authored_prompt_proposal = original

    assert resultat["status"] == "error"
    assert "metadata prose" in resultat["error"]


def test_indsaettelse_bevarer_filen(isoleret_workspace) -> None:
    """Kernen i executors adfaerd: fragmentet TILFOEJES, filen erstattes ikke.

    `apply_mutation` erstatter hele filen med `new_content`. Uden
    indsaettelses-trinnet ville en godkendelse slette HEARTBEAT.md og efterlade
    én saetning — derfor maales det her.
    """
    fil = isoleret_workspace
    foer = fil.read_text(encoding="utf-8")
    fragment = "Keep the next step plain, bounded, and alive."
    markoer = "## Anvendt prompt-justering"

    nyt = f"{foer.rstrip()}\n\n{markoer}\n\n{fragment}\n"
    pml.apply_mutation(
        target_file="HEARTBEAT.md",
        new_content=nyt,
        source="prompt_evolution",
        reason="test",
    )

    efter = fil.read_text(encoding="utf-8")
    assert "Status: enabled" in efter, "originalindholdet skal overleve"
    assert "Kill Switch: enabled" in efter
    assert fragment in efter, "fragmentet skal vaere tilfoejet"
    assert efter.count(markoer) == 1


def test_idempotent_sektion(isoleret_workspace, monkeypatch) -> None:
    """En fil der ALLEREDE har sektionen faar ikke en ny — sektionen erstattes.

    Testen anvender bevidst kun ÉN gang. To anvendelser i samme fil er ikke
    muligt inden for et doegn: `apply_mutation` har et per-fil-cooldown paa
    `_PER_FILE_COOLDOWN_HOURS = 24` (maalt 28/10-2026 — det andet kald blev
    afvist med «had a mutation within the last 24h»). Det er et vaern, ikke en
    fejl, og testen maaler derfor det den kan: at en eksisterende sektion
    erstattes i stedet for at blive duplikeret.
    """
    import core.runtime.db_runtime_self as drs

    fil = isoleret_workspace
    markoer = "## Anvendt prompt-justering"
    gammelt = "Gammel justering der skal erstattes."
    nyt_fragment = "Keep the next step plain."

    # Filen har ALLEREDE en sektion fra en tidligere justering.
    fil.write_text(
        f"# HEARTBEAT\n\nStatus: enabled\n\n{markoer}\n\n{gammelt}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        drs,
        "get_runtime_self_authored_prompt_proposal",
        lambda pid: {"proposal_id": pid, "candidate_fragment": nyt_fragment},
    )
    monkeypatch.setattr(
        drs,
        "update_runtime_self_authored_prompt_proposal_status",
        lambda *a, **k: None,
    )

    res = q._execute_prompt_evolution_proposal(
        {"proposal_id": "p1", "target_file": "HEARTBEAT.md"}
    )
    assert res["status"] == "executed", res

    efter = fil.read_text(encoding="utf-8")
    assert efter.count(markoer) == 1, "sektionen maa ikke duplikeres"
    assert nyt_fragment in efter, "det nye fragment skal ind"
    assert gammelt not in efter, "det gamle fragment skal vaere erstattet"
    assert "Status: enabled" in efter, "resten af filen skal overleve"
