"""Tests for core/services/cheap_provider_breaker_adapters.py.

Udskilt fra ``cheap_provider_runtime_adapters`` 2026-09-01 (Boy Scout — filen
var 2.046 linjer). Adapterne er tynde oversættere: de konfigurerer den delte
``provider_circuit_breaker`` med hver providers HISTORISKE tærskel og
delegerer. Testene fastholder netop de tærskler, for det er dem udskillelsen
kunne komme til at tabe.
"""

from __future__ import annotations

import pytest

import core.services.cheap_provider_breaker_adapters as ba


@pytest.fixture
def spy(monkeypatch):
    """Fang kaldene til den delte breaker uden at røre rigtig tilstand."""
    calls: list[tuple] = []

    class _Fake:
        @staticmethod
        def pp_configure(pid, *, threshold, cooldown_s):
            calls.append(("configure", pid, threshold, cooldown_s))

        @staticmethod
        def pp_is_open(pid):
            calls.append(("is_open", pid))
            return True

        @staticmethod
        def pp_record_failure(pid):
            calls.append(("failure", pid))

        @staticmethod
        def pp_record_success(pid):
            calls.append(("success", pid))

    import core.services as services
    monkeypatch.setattr(services, "provider_circuit_breaker", _Fake, raising=False)
    import sys
    monkeypatch.setitem(sys.modules, "core.services.provider_circuit_breaker", _Fake)
    return calls


class TestHistoricalThresholds:
    """Tærsklerne er bevaret adfærd — de må ikke drive under en flytning."""

    def test_ollamafreeapi_keeps_3_failures_and_5_minutes(self) -> None:
        assert ba._OFA_CB_THRESHOLD == 3
        assert ba._OFA_CB_OPEN_DURATION_S == 300.0
        assert ba._OFA_PROVIDER_ID == "ollamafreeapi"

    def test_arko_keeps_3_failures_and_3_minutes(self) -> None:
        assert ba._ARKO_CB_THRESHOLD == 3
        assert ba._ARKO_CB_OPEN_DURATION_S == 180
        assert ba._ARKO_PROVIDER_ID == "arko"

    def test_the_two_providers_have_distinct_ids(self) -> None:
        """Delt store, keyed på provider_id — sammenfald ville koble dem."""
        assert ba._OFA_PROVIDER_ID != ba._ARKO_PROVIDER_ID


class TestOllamaFreeApiAdapter:
    def test_open_configures_before_asking(self, spy) -> None:
        """Konfiguration SKAL ske før opslaget, ellers gælder en fremmed tærskel."""
        assert ba._ofa_circuit_open() is True
        assert spy[0] == ("configure", "ollamafreeapi", 3, 300.0)
        assert spy[1] == ("is_open", "ollamafreeapi")

    def test_failure_configures_then_records(self, spy) -> None:
        ba._ofa_circuit_record_failure()
        assert spy[0][0] == "configure"
        assert spy[1] == ("failure", "ollamafreeapi")

    def test_success_delegates_without_reconfiguring(self, spy) -> None:
        """Et held kræver ingen tærskel — kun nulstilling."""
        ba._ofa_circuit_record_success()
        assert spy == [("success", "ollamafreeapi")]


class TestArkoAdapter:
    def test_open_configures_before_asking(self, spy) -> None:
        assert ba._arko_circuit_open() is True
        assert spy[0] == ("configure", "arko", 3, 180.0)
        assert spy[1] == ("is_open", "arko")

    def test_cooldown_is_passed_as_float(self, spy) -> None:
        """Arkos konstant er int; den delte store forventer sekunder som float."""
        ba._arko_circuit_record_failure()
        assert isinstance(spy[0][3], float)

    def test_success_delegates_without_reconfiguring(self, spy) -> None:
        ba._arko_circuit_record_success()
        assert spy == [("success", "arko")]


class TestBackwardCompatibility:
    @pytest.mark.parametrize("name", [
        "_ofa_circuit_open", "_ofa_circuit_record_failure",
        "_ofa_circuit_record_success", "_arko_circuit_open",
        "_arko_circuit_record_failure", "_arko_circuit_record_success",
    ])
    def test_still_importable_from_the_old_module(self, name: str) -> None:
        """Udskillelsen må ikke bryde eksisterende imports."""
        import core.services.cheap_provider_runtime_adapters as old
        assert getattr(old, name) is getattr(ba, name)
