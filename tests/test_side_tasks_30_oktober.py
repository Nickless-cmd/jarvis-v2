"""Vagter for fire side-opgaver løst 30/10-2026.

Hver vagt er skrevet så den FÆLDER tilbagefaldet — ikke så den bare består.
Målingerne de værner står i den tilhørende kode-kommentar.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.memory.memory_md_writer import upsert_section
from core.runtime.db_runtime_self import _runtime_self_narrative_continuity_signal_from_row


# ── side-6c427ea182: memory_upsert_section fordoblede sektionens krop ──────
def test_upsert_med_egen_overskrift_i_indholdet_fordobler_ikke(tmp_path: Path) -> None:
    """MÅLT 30/10: to upserts gav 7 → 11 linjer, og `## Under` stod to gange.

    Fejlen: `parse_sections` ser indholdets egen heading som en NY sektion, så
    den gamle krop blev efterladt som en forældreløs hale mens værktøjet
    svarede «updated successfully». MEMORY.md nåede 34.584 linjer.
    """
    p = tmp_path / "MEM.md"
    p.write_text("# MEM\n\n## Eksisterende\n\ngammel linje\n", encoding="utf-8")
    body = "## Under\nny linje et\nny linje to"

    upsert_section(p, "Eksisterende", body, level=2, mode="replace")
    efter_foerste = p.read_text(encoding="utf-8")

    upsert_section(p, "Eksisterende", body, level=2, mode="replace")
    efter_anden = p.read_text(encoding="utf-8")

    assert efter_anden.count("ny linje et") == 1, (
        f"kroppen blev indsat {efter_anden.count('ny linje et')} gange — fordoblingen er tilbage"
    )
    assert efter_anden.count("## Under") == 1
    assert "gammel linje" not in efter_anden
    assert len(efter_anden.splitlines()) == len(efter_foerste.splitlines()), (
        "filen voksede ved anden upsert — halen blev efterladt igen"
    )


def test_upsert_fjerner_ikke_en_rigtig_sektion_med_samme_navn(tmp_path: Path) -> None:
    """Modprøve: fjernelsen må kun ramme den gamle HALE.

    En selvstændig `## Under`-sektion med ANDET indhold er ikke en hale og må
    ikke slettes af oprydningen.
    """
    p = tmp_path / "MEM.md"
    p.write_text(
        "# MEM\n\n## Eksisterende\n\ngammel\n\n## Under\nhelt andet indhold\n",
        encoding="utf-8",
    )
    upsert_section(p, "Eksisterende", "## Under\nnyt indhold", level=2, mode="replace")
    tekst = p.read_text(encoding="utf-8")
    assert "helt andet indhold" in tekst, "en ægte, selvstændig sektion blev slettet"


# ── side-e14ddde7f3: IndexError i narrative-continuity-mapperen ────────────
def test_narrative_mapper_laeser_ikke_candidate_fragment() -> None:
    """MÅLT 30/10: `IndexError: No item with that key` ved HVER række — 24
    forekomster i api-journalen — fordi mapperen læste en kolonne tabellen
    ikke har. Seks kognitive signaler blev aldrig skrevet.
    """
    kolonner = [
        "signal_id", "signal_type", "canonical_key", "status", "title", "summary",
        "rationale", "source_kind", "confidence", "evidence_summary",
        "support_summary", "status_reason", "run_id", "session_id",
        "support_count", "session_count", "merge_count", "created_at", "updated_at",
    ]
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE t (" + ", ".join(f"{k} TEXT" for k in kolonner) + ")"
    )
    conn.execute("INSERT INTO t (signal_id, support_count) VALUES ('s1', '2')")
    row = conn.execute("SELECT * FROM t").fetchone()

    resultat = _runtime_self_narrative_continuity_signal_from_row(row)

    assert resultat["signal_id"] == "s1"
    assert resultat["support_count"] == 2
    assert "candidate_fragment" not in resultat, (
        "nøglen er tilbage — den findes ikke i tabellen og kaster IndexError i drift"
    )


# ── side-f54c10a576: kvitteringer blev den indre stemmes top-fokus ─────────
def test_initiative_acted_kan_ikke_blive_top_fokus(monkeypatch: pytest.MonkeyPatch) -> None:
    """MÅLT 30/10: løkken var selvfodrende ende-til-ende.

    `mark_acted()` skrev en `initiative-acted`-post → den blev nyeste aktive →
    `excerpts[0]` → stemmens top-fokus → nyt initiativ → ny lukning → ny post.
    """
    from core.services import session_distillation as sd

    raekker = [
        {"record_type": "initiative-acted", "summary": "lukkede initiativ om afbrudt kørsel",
         "focus": "afbrudt", "confidence": "medium"},
        {"record_type": "initiative-acted", "summary": "endnu en lukning", "focus": "afbrudt",
         "confidence": "medium"},
        {"record_type": "reflection", "summary": "en ægte tanke", "focus": "tanke",
         "confidence": "high"},
    ]
    monkeypatch.setattr(sd, "list_private_brain_records", lambda **kw: list(raekker))

    ctx = sd.build_private_brain_context(limit=6)

    typer = [e["type"] for e in ctx["excerpts"]]
    assert "initiative-acted" not in typer, (
        f"en kvittering nåede grounding: {typer}"
    )
    assert ctx["excerpts"][0]["type"] == "reflection"
    assert "initiative-acted" not in ctx["by_type"]


# ── side-5fa43963a4: autonome komponist-forslag nåede aldrig Bjørn ─────────
def test_autonomt_forslag_kan_hentes_i_chat_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """MÅLT 30/10: 6 af 8 `auto-*`-forslag blev aldrig vist.

    `gem_forslag` bandt forslaget til den session det blev skrevet i, og
    opslaget slog kun op i DEN. `cj-81581b5da64948fa` («Godkend
    gentagelses-porten i Mission Control») lå uset i timevis.
    """
    from core.runtime import db_composer_jarvis as dcj
    from core.runtime import db_composer_choice as dcc

    autonomt = {
        "forslag_id": "cj-81581b5da64948fa",
        "forslag": "Godkend gentagelses-porten i Mission Control",
        "kilde_besked_id": "",
        "skrevet_at": dcj.datetime.now(dcj.UTC).isoformat(),
    }

    monkeypatch.setattr(dcj, "kig_forslag", lambda *, session_id: None)
    monkeypatch.setattr(dcc, "er_vist", lambda *, forslag_id: False)

    class _FakeConn:
        def execute(self, *a, **k):
            class _R:
                def fetchall(self_inner):
                    return [autonomt]
            return _R()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(dcj, "connect", lambda: _FakeConn())
    monkeypatch.setattr(dcj, "_sikr_tabel", lambda conn: None)

    fundet = dcj.kig_forslag_til_klient(session_id="chat-bjoern")

    assert fundet is not None, "det autonome forslag nåede stadig ikke chat-sessionen"
    assert fundet["forslag_id"] == "cj-81581b5da64948fa"


def test_eget_forslag_vinder_over_autonomt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Modprøve: et autonomt bud må ALDRIG fortrænge et forslag fra hans egen session."""
    from core.runtime import db_composer_jarvis as dcj

    eget = {"forslag_id": "cj-eget", "forslag": "eget bud",
            "kilde_besked_id": "", "skrevet_at": "2026-10-30T05:00:00Z"}
    monkeypatch.setattr(dcj, "kig_forslag", lambda *, session_id: eget)

    fundet = dcj.kig_forslag_til_klient(session_id="chat-bjoern")

    assert fundet == eget


def test_autonom_session_faar_ikke_et_andet_autonomt_forslag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """En autonom kørsel har ingen Bjørn at vise noget til — og må ikke arve et andet buds."""
    from core.runtime import db_composer_jarvis as dcj

    monkeypatch.setattr(dcj, "kig_forslag", lambda *, session_id: None)

    assert dcj.kig_forslag_til_klient(session_id="auto-heartbeat-20261030") is None
