"""En AFVIST forpligtelse skal i indbakken — ikke forsvinde.

Bjørn 14/10-2026: «istedet for at afvise burde de lande i indbox og så vælger
inbox om du er i et run og du for den i prompten til næste runde eller idle
vække dig».

Hullet der blev målt samme dag: begge run-startere loggede «forpligtelsen
bliver i indbakken til sessionen er ledig» og `return`erede så — uden at skrive
noget. `grep registrer_kilde` i `visible_autonomous_run.py` gav ét træf: en
kommentar. Et afvist run forsvandt altså sporløst: hverken kørt eller lagt til
side.

Testene her pinner de fire led i kæden, og de pinner den ÆRLIGE grænse: en post
hvis ejer ikke kan verificeres som Jarvis gater IKKE. Det er ikke en fejl —
`bloker` bærer gatingen alene i det tilfælde, og `kraever_handling` afgør om
vækkeren må røre den.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox


@pytest.fixture
def inbox_db(monkeypatch, tmp_path):
    """Samme mønster som `test_inbox_idle_waker.py` — én isoleret DB pr. test."""
    sti = tmp_path / "afvist.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


@pytest.fixture(autouse=True)
def _ejer_og_run(monkeypatch):
    """Giv parkeringen en ejer og et kørende run — som i drift.

    `parker_forpligtelse` slår ejeren op gennem `_ejer_id()` og run-id'et gennem
    `aktivt_run_id()`. Begge læses fra processens kontekst, så de skal stå fast
    i testen; ellers måler vi et tilfælde der ikke findes.
    """
    from core.services import inbox_state, run_guard

    monkeypatch.setattr(inbox_state, "_ejer_id", lambda: "bjorn")
    monkeypatch.setattr(
        "core.services.session_context_resolve.aktivt_run_id",
        lambda standard="": "visible-afvist-1",
    )
    # `verificeret_jarvis_run` kræver at run-id'et matcher det AKTIVE run.
    monkeypatch.setattr(inbox_state, "verificeret_jarvis_run", lambda rid, uid: bool(rid))
    return run_guard


def _parker(**kw):
    from core.services.run_guard import parker_forpligtelse

    return parker_forpligtelse(
        origin=kw.pop("origin", "recurring"),
        session_id=kw.pop("session_id", "chat-6f46abc"),
        beskrivelse=kw.pop("beskrivelse", "Eftermiddagsmedicin: 50 mg ritalin."),
        **kw,
    )


# ── Leddene i kæden ──────────────────────────────────────────────────────────

class TestAfvistForpligtelseLandet:
    def test_afvisningen_skriver_en_post(self, inbox_db):
        """Det målte hul: log-linjen lovede en post, koden skrev ingen."""
        r = _parker()
        assert r.get("status") == "ok", r
        post = r.get("post") or {}
        assert post.get("kildetype") == "afvist_run"
        assert post.get("status") == "aaben"

    def test_posten_baerer_samtalen_den_hoerte_til(self, inbox_db):
        """Uden bindingen ville vækkeren vække en `auto-*`-silo."""
        r = _parker(session_id="chat-6f46abc")
        assert (r.get("post") or {}).get("session_id") == "chat-6f46abc"

    def test_posten_er_gatende(self, inbox_db):
        """`kraever_handling=1` er det der gør den til en forpligtelse."""
        r = _parker()
        post = r.get("post") or {}
        assert post.get("kraever_handling") in (1, True), post
        assert post.get("bloker") in (1, True), post

    def test_posten_faar_en_frist(self, inbox_db):
        """En blokerende post uden frist er en permanent lås."""
        r = _parker()
        assert str((r.get("post") or {}).get("expires_at") or "").strip(), r

    def test_kildetypen_maa_vaekke(self, inbox_db):
        """Uden `afvist_run` i sættet ville posten kun dukke op når Bjørn skrev."""
        from core.services.inbox_state import kan_dispatch

        assert kan_dispatch("afvist_run") is True

    def test_vaekkeren_ser_posten(self, inbox_db):
        """Den anden halvdel af Bjørns arkitektur: idle → væk mig."""
        from core.services.inbox_idle_waker import kandidater

        _parker()
        ids = [p.get("kilde_id") for p in kandidater("bjorn")]
        assert ids, "vækkeren så ingen kandidat — posten ville stå stille"


# ── Den ærlige grænse ────────────────────────────────────────────────────────

class TestGraensen:
    def test_uden_verificeret_ejer_gater_posten_ikke(self, inbox_db, monkeypatch):
        """`huset` kan informere, men ikke kræve — heller ikke her.

        Det er ikke en fejl i parkeringen: `bloker` bærer gatingen alene, og
        `kraever_handling` afgør om vækkeren må røre posten. Testen pinner at
        de to felter ikke smelter sammen.
        """
        from core.services import inbox_state

        monkeypatch.setattr(inbox_state, "verificeret_jarvis_run", lambda rid, uid: False)
        r = _parker()
        post = r.get("post") or {}
        assert post.get("verificeret_ejer") != db_inbox.EJER_JARVIS
        assert post.get("bloker") in (1, True), post

    def test_parkeringen_vaelter_ikke_ved_fejl(self, inbox_db, monkeypatch):
        """Self-safe: en manglende post må ikke kunne vælte run-starteren."""
        from core.services import inbox_state

        def _braender(*a, **kw):
            raise RuntimeError("DB nede")

        monkeypatch.setattr(inbox_state, "registrer_kilde", _braender)
        r = _parker()
        assert r.get("status") == "fejl", r
