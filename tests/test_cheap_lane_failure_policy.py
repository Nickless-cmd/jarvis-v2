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


class TestRetryDybde:
    def test_seks_forsoeg_mod_en_stor_pool(self):
        """Tre forsøg mod 106 slots gjorde udmattelse til et uheldigt træk, ikke et udfald."""
        import inspect

        from core.services.cheap_lane_balancer import _DEFAULT_MAX_RETRIES, call_balanced

        assert _DEFAULT_MAX_RETRIES >= 6
        sig = inspect.signature(call_balanced)
        assert sig.parameters["max_retries"].default == _DEFAULT_MAX_RETRIES

    def test_retries_er_stadig_bundet(self):
        """Ubundet retry ville gøre ét daemon-kald til en minutlang kaskade."""
        from core.services.cheap_lane_balancer import _DEFAULT_MAX_RETRIES

        assert _DEFAULT_MAX_RETRIES <= 10


class TestBeskedenVejerTungereEndKoden:
    """Udbyderne er ikke enige om hvilken kode en pensioneret model giver.

    Målt 19. aug 2026: opencode svarede `auth-rejected` på "Model north-mini-code-free
    is not supported" — hvilket sendte fejlsøgningen efter NØGLER. aionlabs svarede
    `http-400` på "Unknown model: aion-labs/aion-2.5" — klassificeret transient, så
    slottet kom tilbage i lodtrækningen igen og igen. Koden løj; beskeden ikke.
    """

    def test_ikke_understoettet_bag_auth_kode(self):
        assert pol.classify("auth-rejected", "Model north-mini-code-free is not supported") == "permanent"

    def test_ukendt_model_bag_http_400(self):
        assert pol.classify("http-400", "Unknown model: aion-labs/aion-2.5") == "permanent"
        assert pol.quarantine_seconds("http-400", message="Unknown model: x") == pol.PERMANENT_QUARANTINE_S

    def test_arkiveret_model_genkendes(self):
        assert pol.classify("model-archived", "Model zai-glm-4.7 is archived") == "permanent"

    def test_retirement_brownout_genkendes(self):
        assert pol.classify("http-410", "scheduled retirement brownout") == "permanent"

    def test_uskyldig_besked_aendrer_ikke_klassifikationen(self):
        """En transient fejl må ikke blive permanent, blot fordi den har en tekst."""
        assert pol.classify("unreachable", "connection reset by peer") == "transient"
        assert pol.classify("rate-limited", "too many requests, slow down") == "transient"

    def test_retry_after_vinder_stadig_over_beskeden(self):
        assert pol.quarantine_seconds("http-400", retry_after_s=30, message="Unknown model") == 0

    def test_uden_besked_er_adfaerden_uaendret(self):
        assert pol.classify("http-400") == "transient"
        assert pol.classify("model-not-found") == "permanent"


class TestBundKaeden:
    """Bunden skal kunne svare når alt andet brænder — ellers er den dekoration.

    Målt 19. aug 2026: primæret var `pollinations/openai`, men providerens eneste model
    hedder `openai-fast`. Bundens FØRSTE target pegede altså på et modelnavn der ikke
    fandtes, og backup'en (ovhcloud, anonym) er 2 RPM med 12,4 s svartid.
    """

    def test_alle_targets_er_keyless(self):
        """En bund der kræver en nøgle kan fejle af en grund vi ikke kontrollerer."""
        from core.services.cheap_lane_floor import floor_targets
        from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS

        for prov, _ in floor_targets():
            meta = CHEAP_PROVIDER_DEFAULTS.get(prov) or {}
            assert str(meta.get("auth_kind")) == "none", f"{prov} er ikke keyless"

    def test_alle_targets_navngiver_en_model_provideren_faktisk_har(self):
        """Præcis den fejl der gjorde bundens primære target ubrugelig."""
        from core.services.cheap_lane_floor import floor_targets
        from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS

        for prov, model in floor_targets():
            meta = CHEAP_PROVIDER_DEFAULTS.get(prov) or {}
            static = meta.get("static_models")
            if not static:
                continue  # dynamisk model-liste → kan ikke tjekkes statisk
            assert model in static, (
                f"bund-target {prov}/{model!r} findes ikke i providerens "
                f"static_models {static}"
            )

    def test_kaeden_har_dybde(self):
        """Ét target er ikke en bund; det er et enkelt fejlpunkt."""
        from core.services.cheap_lane_floor import floor_targets

        assert len(floor_targets()) >= 2

    def test_ingen_dublet_provider_i_kaeden(self):
        """To targets hos samme provider deler skæbne ved kvote/nedbrud."""
        from core.services.cheap_lane_floor import floor_targets

        provs = [p for p, _ in floor_targets()]
        assert len(provs) == len(set(provs)), f"dublet-provider i bund-kæden: {provs}"
