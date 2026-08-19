"""Indre-livs-handlinger skal MOTIVERES, ikke bare tillades.

Målt 19. aug 2026: heartbeat vælger sin handling med et LLM-kald. Prompten listede alle
~30 tilladte `execute_action`-værdier — og gav eksplicitte vink for de operationelle
("Prefer inspect_repo_context when…", "Prefer gather_system_context when…"). For
`write_chronicle_entry` fandtes NUL vink. Over 2.859 ticks: `act_on_initiative` valgt 227
gange, `write_chronicle_entry` **nul gange**. `cognitive_chronicle_entries` havde derfor
én række, og den kom fra finitude-ritualet — ikke fra chronicle-motoren.

Reglen der testes: foreslå kun det der faktisk ville lykkes. Ellers beder vi ham gøre
noget der tavst ikke gør noget.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.services.heartbeat_action_hints as hints


def _iso(days_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


class TestForfaldenhed:
    def test_aldrig_skrevet_er_maksimalt_forfalden(self):
        with patch("core.runtime.db.get_latest_cognitive_chronicle_entry", return_value=None):
            assert hints.chronicle_days_stale() == float("inf")

    def test_alder_beregnes_fra_created_at(self):
        with patch("core.runtime.db.get_latest_cognitive_chronicle_entry",
                   return_value={"created_at": _iso(5)}):
            d = hints.chronicle_days_stale()
        assert 4.9 < d < 5.1

    def test_ulaeselig_dato_giver_none_ikke_et_gaet(self):
        with patch("core.runtime.db.get_latest_cognitive_chronicle_entry",
                   return_value={"created_at": "ikke en dato"}):
            assert hints.chronicle_days_stale() is None

    def test_db_fejl_giver_none(self):
        with patch("core.runtime.db.get_latest_cognitive_chronicle_entry",
                   side_effect=RuntimeError("db")):
            assert hints.chronicle_days_stale() is None


class TestVinketSpejlerMotorensGates:
    """Vi må ikke foreslå en handling der ville returnere None."""

    def _hint(self, days_ago, runs):
        latest = None if days_ago is None else {"created_at": _iso(days_ago)}
        with patch("core.runtime.db.get_latest_cognitive_chronicle_entry", return_value=latest), \
             patch("core.runtime.db.recent_visible_runs", return_value=runs):
            return hints.chronicle_hint()

    def test_for_nylig_skrevet_giver_intet_vink(self):
        """Motoren har en 3-døgns-spærre — så vi tier indtil den er ovre."""
        assert self._hint(1, [{"id": 1}]) is None

    def test_ingen_nylige_runs_giver_intet_vink(self):
        """Uden runs ville motoren returnere None — så vi beder ham ikke om det."""
        assert self._hint(10, []) is None

    def test_forfalden_med_runs_giver_vink(self):
        h = self._hint(10, [{"id": 1}])
        assert h and "write_chronicle_entry" in h and "10 døgn" in h

    def test_aldrig_skrevet_giver_vink_uden_tal(self):
        h = self._hint(None, [{"id": 1}])
        assert h and "aldrig skrevet" in h
        assert "inf" not in h, "inf må aldrig lække ud i en prompt"

    def test_praecis_paa_graensen_tier(self):
        assert self._hint(2.9, [{"id": 1}]) is None

    def test_fejl_giver_intet_vink_i_stedet_for_at_kaste(self):
        with patch("core.runtime.db.get_latest_cognitive_chronicle_entry",
                   side_effect=RuntimeError("db")):
            assert hints.chronicle_hint() is None


class TestSamletListe:
    def test_tom_naar_intet_er_forfaldent(self):
        with patch.object(hints, "chronicle_hint", return_value=None):
            assert hints.inner_life_hints() == []

    def test_indeholder_aktive_vink(self):
        with patch.object(hints, "chronicle_hint", return_value="- vink"):
            assert hints.inner_life_hints() == ["- vink"]

    def test_en_fejlende_vink_vaelter_ikke_de_andre(self):
        with patch.object(hints, "chronicle_hint", side_effect=RuntimeError("boom")):
            assert hints.inner_life_hints() == []


class TestKobletPaaBeslutningsPrompten:
    def test_heartbeat_delegerer_selv_sikkert(self):
        from core.services.heartbeat_runtime import _inner_life_action_hints

        with patch("core.services.heartbeat_action_hints.inner_life_hints",
                   side_effect=RuntimeError("nede")):
            assert _inner_life_action_hints() == [], "et manglende vink må aldrig vælte prompten"

    def test_vink_naar_frem_til_kalderen(self):
        from core.services.heartbeat_runtime import _inner_life_action_hints

        with patch("core.services.heartbeat_action_hints.inner_life_hints",
                   return_value=["- prøv kronikken"]):
            assert _inner_life_action_hints() == ["- prøv kronikken"]


class TestDroemmeBatchSkaererIkkeHalenAf:
    def test_loftet_daekker_droemme_fasens_liste(self):
        """write_chronicle_entry stod nr. 7 af 7 og blev skåret af et loft på 5."""
        import inspect

        from core.services import heartbeat_runtime, living_heartbeat_cycle

        src = inspect.getsource(heartbeat_runtime)
        assert "batch_actions[:5]" not in src, "det gamle loft skar drømme-fasens hale af"

        dreaming = living_heartbeat_cycle._PHASES["dreaming"] \
            if hasattr(living_heartbeat_cycle, "_PHASES") else None
        if dreaming:
            assert len(dreaming["suggested_actions"]) <= 8, (
                "drømme-fasen er vokset forbi loftet — hæv _BATCH_CAP eller del listen"
            )
