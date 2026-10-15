"""Tests for core.services.memory_write_queue — async write queue."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def fresh_queue(monkeypatch, tmp_path):
    """Isolate queue DB via HOME-based DB_PATH, then reset module state."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))

    # Force reload of ALL config/DB modules so Path.home() is re-evaluated.
    # Order matters: config → db_core → db → bootstrap → memory_write_queue
    import importlib
    for mod_name in [
        "core.runtime.config",
        "core.runtime.db_core",
        "core.runtime.db",
        "core.runtime.bootstrap",
        "core.services.memory_write_queue",
    ]:
        importlib.reload(__import__(mod_name, fromlist=[""]))

    from core.services import memory_write_queue as mwq
    from core.identity.workspace_context import user_context
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "test-user")
    with user_context(discord_id="test-user"):
        yield mwq


class TestEnqueueWrite:
    def test_enqueue_sensory(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("sensory", {
            "modality": "visual", "content": "test", "mood_tone": "neutral",
        })
        assert qid != ""
        assert qid.startswith("mwq-")
        counts = mwq.queue_size()
        assert counts["pending"] >= 1

    def test_enqueue_brain(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("brain", {
            "kind": "indsigt", "title": "test", "content": "brain entry",
            "visibility": "personal", "domain": "self",
        })
        assert qid != ""

    def test_enqueue_memory_sidecar(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("memory_sidecar", {
            "heading": "test", "action": "updated", "content": "sidecar",
        })
        assert qid != ""

    def test_enqueue_invalid_type(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("invalid_type", {"content": "nope"})
        assert qid == ""

    def test_queue_initial_state_empty(self, fresh_queue):
        mwq = fresh_queue
        counts = mwq.queue_size()
        assert counts["total"] == 0, f"expected empty queue, got {counts}"


class TestProcessQueue:
    def test_process_pending(self, fresh_queue):
        mwq = fresh_queue
        qid = mwq.enqueue_write("sensory", {
            "modality": "atmosphere", "content": "en stille stue", "mood_tone": "roligt",
        })
        assert qid != ""

        result = mwq.process_queue(batch_size=10)
        assert result["processed"] >= 1
        assert result["succeeded"] >= 1

        counts = mwq.queue_size()
        assert counts["pending"] == 0, f"expected 0 pending, got {counts}"

    def test_process_empty_no_error(self, fresh_queue):
        mwq = fresh_queue
        result = mwq.process_queue(batch_size=10)
        assert result["processed"] == 0
        assert result["failed"] == 0

    def test_multiple_writes_then_process(self, fresh_queue):
        mwq = fresh_queue
        for i in range(5):
            qid = mwq.enqueue_write("sensory", {
                "modality": "mixed", "content": f"batch item {i}", "mood_tone": "neutral",
            })
            assert qid != ""
        counts = mwq.queue_size()
        assert counts["pending"] == 5, f"expected 5 pending, got {counts}"

        result = mwq.process_queue(batch_size=10)
        assert result["processed"] == 5, f"expected 5 processed, got {result}"
        assert result["succeeded"] == 5


class TestDaemonTick:
    def test_tick_signature(self, fresh_queue):
        mwq = fresh_queue
        result = mwq.tick_memory_write_queue_daemon()
        assert isinstance(result, dict)

    def test_tick_processes_items(self, fresh_queue):
        mwq = fresh_queue
        mwq.enqueue_write("sensory", {
            "modality": "visual", "content": "tick test", "mood_tone": "neutral",
        })
        result = mwq.tick_memory_write_queue_daemon()
        assert result.get("processed", 0) >= 1 or result.get("succeeded", 0) >= 1


class TestOrphanedProcessing:
    """En `processing`-post hvis proces doede, maa ikke ligge fast for evigt.

    Maalt i drift 15/10-2026: 99 poster laast siden 22. juni, alle
    `memory_sidecar`, `retry_count = 0`. Aarsagen er at `process_queue`
    committer `processing` FOER den udfoerer skrivningen.
    """

    @staticmethod
    def _doed(*_args, **_kwargs):
        raise RuntimeError("processen doede midt i skrivningen")

    def _efterlad_i_processing(self, mwq, monkeypatch, queue_type="sensory"):
        """Den AEGTE fejlvej: skrivningen kaster efter claimet er committet."""
        payload = (
            {"heading": "gammel sektion", "action": "added", "content": "x"}
            if queue_type == "memory_sidecar"
            else {"modality": "visual", "content": "afbrudt", "mood_tone": "neutral"}
        )
        assert mwq.enqueue_write(queue_type, payload) != ""
        monkeypatch.setattr(mwq, "_process_item", self._doed)
        mwq.process_queue(batch_size=10)

    def test_afbrudt_behandling_efterlader_stemplet_claim(self, fresh_queue, monkeypatch):
        """Posten bliver liggende — og den baerer HVORNAAR den blev claimet."""
        mwq = fresh_queue
        self._efterlad_i_processing(mwq, monkeypatch)

        from core.runtime.db import connect
        with connect() as conn:
            raekke = conn.execute(
                "SELECT status, claimed_at FROM memory_write_queue").fetchone()
        assert raekke["status"] == "processing"
        assert raekke["claimed_at"], "claimet skal vaere stempler — ellers kan intet se alderen"

    def test_frisk_claim_roeres_ikke(self, fresh_queue, monkeypatch):
        """Et claim fra NU er ikke foraeldreloest. Sweep'en maa ikke rive det vaek."""
        mwq = fresh_queue
        self._efterlad_i_processing(mwq, monkeypatch)

        svar = mwq.requeue_orphaned_processing()
        assert svar == {"requeued": 0, "abandoned": 0}
        assert mwq.queue_size()["processing"] == 1

    def test_foraeldreloes_post_genkoeres(self, fresh_queue, monkeypatch):
        """Naar claimet er blevet gammelt, skal posten tilbage i koen."""
        mwq = fresh_queue
        self._efterlad_i_processing(mwq, monkeypatch)

        senere = datetime.now(UTC) + timedelta(hours=1)
        svar = mwq.requeue_orphaned_processing(now=senere)
        assert svar["requeued"] == 1
        assert svar["abandoned"] == 0
        counts = mwq.queue_size()
        assert counts["pending"] == 1
        assert counts["processing"] == 0

    def test_for_gammel_post_lukkes_og_genkoeres_ikke(self, fresh_queue, monkeypatch):
        """Fire maaneder gammel: maa ikke skrives ind i MEMORY.md igen.

        Begge tider skal vaere gamle: `claimed_at` afgoer OM posten er
        foraeldreloes, `created_at` afgoer om den maa genkoeres.
        """
        mwq = fresh_queue
        self._efterlad_i_processing(mwq, monkeypatch, queue_type="memory_sidecar")

        from core.runtime.db import connect
        with connect() as conn:
            conn.execute(
                "UPDATE memory_write_queue SET created_at = ?, claimed_at = ?",
                ("2026-06-22T07:31:01+00:00", "2026-06-22T07:31:01+00:00"))
            conn.commit()

        svar = mwq.requeue_orphaned_processing(now=datetime.now(UTC))
        assert svar["abandoned"] == 1
        assert svar["requeued"] == 0
        counts = mwq.queue_size()
        assert counts["failed"] == 1
        assert counts["pending"] == 0

    def test_daemon_ticket_frigor_foraeldreloese_poster(self, fresh_queue, monkeypatch):
        """Sweep'en skal vaere KOBLET PAA tick'en.

        En funktion ingen kalder frigor intet — praecis husets eget problem med
        `abandon()`, der kunne skelne fra dag ét men som ingen kaldte.

        Maalet er at posten bliver KOERT FAERDIG efter tick'en: uden sweep'en
        ville den blive i `processing` for evigt, fordi intet nulstiller den.
        """
        mwq = fresh_queue
        aegte = mwq._process_item
        self._efterlad_i_processing(mwq, monkeypatch)
        assert mwq.queue_size()["processing"] == 1

        # Skrivningen virker igen — praecis som efter en genstart.
        monkeypatch.setattr(mwq, "_process_item", aegte)

        senere = datetime.now(UTC) + timedelta(hours=2)
        mwq.tick_memory_write_queue_daemon(now=senere)

        counts = mwq.queue_size()
        assert counts["done"] == 1, (
            "tick'en skal have frigjort posten OG koert den faerdig; "
            f"uden sweep'en ville den blive i processing for evigt — fik {counts}")
        assert counts["processing"] == 0
