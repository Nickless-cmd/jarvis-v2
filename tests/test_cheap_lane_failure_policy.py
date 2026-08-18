"""Karantæne efter ÅRSAG, ikke kun efter antal.

Målt på hele cheap-lane-poolen 18. aug 2026 (106 slots): 71 sunde med median 858 ms,
men 25 slots i permanent eller kvote-bestemt fejl cyklede tilbage i lodtrækningen hver
time, fordi breaker-trappen behandlede en pensioneret model som et flakkende netværk.
Med `max_retries=3` kunne et kald derfor rutinemæssigt trække tre døde slots og erklære
"hele bunden tør" — mens to tredjedele af poolen stod ubrugt.
"""
from __future__ import annotations

from core.services import cheap_lane_failure_policy as pol


class TestKlassifikation:
    def test_config_drift_er_permanent(self):
        """Modellen/endpointet findes ikke — det kræver en config-ændring, ikke tid."""
        for code in ("model-not-found", "http-410", "http-404", "not-found"):
            assert pol.classify(code) == "permanent", code

    def test_afviste_noegler_er_permanente(self):
        for code in ("auth-rejected", "unauthorized", "forbidden", "http-401"):
            assert pol.classify(code) == "permanent", code

    def test_opbrugt_budget_er_depleted(self):
        for code in ("credits-exhausted", "quota-exhausted", "billing"):
            assert pol.classify(code) == "depleted", code

    def test_ægte_transiente_fejl_forbliver_transiente(self):
        for code in ("unreachable", "rate-limited", "request-failed", "http-400"):
            assert pol.classify(code) == "transient", code

    def test_ukendt_kode_er_transient(self):
        """Mild ved tvivl: en fejl vi ikke forstår må ikke fjerne et sundt slot i et døgn."""
        assert pol.classify("noget-helt-nyt") == "transient"
        assert pol.classify("") == "transient"
        assert pol.classify(None) == "transient"


class TestKarantaeneLaengde:
    def test_permanent_faar_et_doegn(self):
        assert pol.quarantine_seconds("model-not-found") == pol.PERMANENT_QUARANTINE_S

    def test_depleted_faar_seks_timer(self):
        assert pol.quarantine_seconds("credits-exhausted") == pol.DEPLETED_QUARANTINE_S

    def test_transient_falder_tilbage_paa_breaker_trappen(self):
        assert pol.quarantine_seconds("unreachable") == 0

    def test_retry_after_fra_serveren_vinder_altid(self):
        """Providerens eget svar om hvornår den er klar må aldrig overskrives."""
        assert pol.quarantine_seconds("credits-exhausted", retry_after_s=30) == 0
        assert pol.quarantine_seconds("model-not-found", retry_after_s=5) == 0

    def test_karantaene_er_tidsbegraenset_ikke_evig(self):
        """En rettet config skal hele sig selv uden at nogen husker et flag."""
        assert 0 < pol.PERMANENT_QUARANTINE_S <= 48 * 3600


class TestBalancerBrugerPolitikken:
    def _state(self):
        from core.services.cheap_lane_balancer import SlotState

        return SlotState(slot_id="s1")

    def test_doed_model_ryger_ud_med_det_samme(self):
        """Før: tre fejl → 5 min. Nu: første fejl → et døgn."""
        from core.services.cheap_lane_balancer import _register_failure

        st = self._state()
        _register_failure(st, "model-not-found", now=1000.0)
        assert st.cooldown_until == 1000.0 + pol.PERMANENT_QUARANTINE_S
        assert st.consecutive_failures == 1  # ikke tre

    def test_transient_fejl_beholder_den_gamle_trappe(self):
        from core.services.cheap_lane_balancer import _register_failure

        st = self._state()
        _register_failure(st, "unreachable", now=1000.0)
        # Under tærsklen → ingen lang karantæne
        assert not st.cooldown_until or st.cooldown_until < 1000.0 + 3600

    def test_karantaenet_slot_vejer_nul(self):
        """Karantænen virker kun hvis lodtrækningen faktisk udelukker slottet."""
        from core.services.cheap_lane_balancer import (
            BalancerSlot, _compute_weight, _register_failure,
        )

        st = self._state()
        _register_failure(st, "http-410", now=1000.0)
        slot = BalancerSlot(provider="p", model="m", auth_profile="default",
                            base_url="", rpm_limit=None, daily_limit=None,
                            is_public_proxy=False)
        assert _compute_weight(slot, st, 1000.0 + 60) == 0.0

    def test_slottet_kommer_tilbage_efter_karantaenen(self):
        from core.services.cheap_lane_balancer import (
            BalancerSlot, _compute_weight, _register_failure,
        )

        st = self._state()
        _register_failure(st, "http-410", now=1000.0)
        slot = BalancerSlot(provider="p", model="m", auth_profile="default",
                            base_url="", rpm_limit=None, daily_limit=None,
                            is_public_proxy=False)
        after = 1000.0 + pol.PERMANENT_QUARANTINE_S + 1
        assert _compute_weight(slot, st, after) > 0.0
