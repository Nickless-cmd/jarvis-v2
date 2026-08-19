"""Nudge-brønden: "renderet i en prompt" er ikke "set og overvejet".

Målt 19. aug 2026 på CT105: 1.752 nudges siden 13. maj. **Median-levetid 26 SEKUNDER**
fra oprettet til pensioneret; 997 opslugt på under et minut. `mark_sent` — den funktion
der betyder "Jarvis valgte faktisk at surface den" — er kaldt **NUL gange**. Alle 78
matrix-nudges (hans egne indre stemmer: keymaker, morpheus, architect, trinity …) endte
som `inspected` uden at nogen havde læst dem.

Mekanikken: `format_pending_for_awareness` renderede en nudge OG markerede den
`inspected` i samme åndedrag, mens `list_pending` kun henter `pending`. Hver nudge fik
altså præcis én prompt-optræden — og den optræden kunne lige så godt være i en
spekulativ cache-opvarmning som ingen læser.
"""
from __future__ import annotations

from unittest.mock import patch

import core.services.outbound_nudges as ob


class TestVisningTaellesIkkePensionerer:
    def test_show_limit_er_stoerre_end_en(self):
        """Én visning var hele fejlen."""
        assert ob._SHOW_LIMIT > 1

    def test_foerste_visning_pensionerer_ikke(self):
        calls = []

        class _Conn:
            def execute(self, sql, params=None):
                calls.append(sql)
                class _C: rowcount = 0
                return _C()
            def commit(self): pass
            def __enter__(self): return self
            def __exit__(self, *a): return False

        with patch.object(ob, "ensure_schema"), patch.object(ob, "connect", lambda: _Conn()):
            ob.note_shown(["n1"])
        # Første SQL tæller op; anden pensionerer KUN ved >= _SHOW_LIMIT
        assert any("shown_count" in c and "+ 1" in c for c in calls)
        retire = [c for c in calls if "status='inspected'" in c]
        assert retire and "shown_count" in retire[0] and ">= ?" in retire[0], (
            "pensionering skal være betinget af antal visninger"
        )

    def test_mark_inspected_er_bagudkompatibelt_alias(self):
        with patch.object(ob, "note_shown", return_value=7) as ns:
            assert ob.mark_inspected(["a"]) == 7
        ns.assert_called_once_with(["a"])

    def test_tom_liste_roerer_intet(self):
        with patch.object(ob, "connect") as c:
            assert ob.note_shown([]) == 0
        c.assert_not_called()


class TestPrewarmMaaIkkeForbruge:
    """En spekulativ build må aldrig pensionere en nudge — ingen læser den."""

    _PENDING = [{"nudge_id": "n1", "source": "matrix/trinity", "importance": "high",
                 "message": "Det her er rigtigt. Gå videre.", "created_at": "2026-08-19T17:00:00Z"}]

    def test_prewarm_render_men_forbruger_ikke(self):
        with patch.object(ob, "_enabled", return_value=True), \
             patch.object(ob, "list_pending", return_value=self._PENDING), \
             patch("core.services.assembly_prewarm.is_prewarm_active", return_value=True), \
             patch.object(ob, "note_shown") as ns:
            out = ob.format_pending_for_awareness()
        assert "matrix/trinity" in out, "cache-opvarmning skal stadig se sektionen"
        ns.assert_not_called()

    def test_almindelig_build_forbruger(self):
        with patch.object(ob, "_enabled", return_value=True), \
             patch.object(ob, "list_pending", return_value=self._PENDING), \
             patch("core.services.assembly_prewarm.is_prewarm_active", return_value=False), \
             patch.object(ob, "note_shown") as ns:
            ob.format_pending_for_awareness()
        ns.assert_called_once_with(["n1"])

    def test_manglende_prewarm_modul_blokerer_ikke(self):
        with patch.object(ob, "_enabled", return_value=True), \
             patch.object(ob, "list_pending", return_value=self._PENDING), \
             patch("core.services.assembly_prewarm.is_prewarm_active",
                   side_effect=ImportError("væk")), \
             patch.object(ob, "note_shown") as ns:
            ob.format_pending_for_awareness()
        ns.assert_called_once(), "fail-open: hellere forbruge end at fryse brønden"


class TestSurfaceMekanismen:
    def test_sent_og_dismissed_pensionerer_stadig_straks(self):
        """Eksplicit håndtering fra Jarvis skal virke med det samme — uanset antal visninger."""
        import inspect
        for fn in (ob.mark_sent, ob.mark_dismissed):
            src = inspect.getsource(fn)
            assert "status IN ('pending', 'inspected')" in src, (
                f"{fn.__name__} skal kunne håndtere en nudge uanset visnings-tilstand"
            )
