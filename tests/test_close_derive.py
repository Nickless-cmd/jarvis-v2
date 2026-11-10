"""Tests for close_derive.

Strengene i disse tests er KOPIERET fra `visible_runs.error` i den levende
database (målt 10/11-2026), ikke opfundet. Det er med vilje: en test der
bruger pæne eksempler beviser at parseren virker på pæne eksempler, ikke at
den virker på det producenten faktisk skriver.
"""

from __future__ import annotations

import pytest

from core.services.close_derive import (
    ABANDONED,
    COMPLETED,
    INFRA_SHUTDOWN,
    NETWORK_ERROR,
    PROVIDER_ERROR,
    PROVIDER_RATE_LIMIT,
    PROVIDER_TIMEOUT,
    RUNTIME_ERROR,
    UNKNOWN,
    USER_CANCELLED,
    derive_close,
    derive_for_run,
    summarize,
)


def test_completed_uden_error_er_ren():
    svar = derive_close("completed", None)
    assert svar["kind"] == COMPLETED
    assert svar["clean"] is True
    assert svar["actor"] == "none"


def test_tom_streng_taeller_som_ren_completed():
    assert derive_close("completed", "")["kind"] == COMPLETED


def test_bruger_afbrydelse():
    svar = derive_close("cancelled", "user-cancelled-during-agentic-loop")
    assert svar["kind"] == USER_CANCELLED
    assert svar["actor"] == "user"
    assert svar["clean"] is False


def test_bruger_afbrydelse_under_tool_exec():
    svar = derive_close("interrupted", "user-cancelled-during-tool-exec")
    assert svar["kind"] == USER_CANCELLED


@pytest.mark.parametrize(
    "streng",
    [
        "api-nedlukning",
        "shutdown",
        "afbrudt af container-genstart",
        "proces doede uden at afslutte koerslen",
    ],
)
def test_infrastruktur_nedlukning(streng):
    assert derive_close("interrupted", streng)["kind"] == INFRA_SHUTDOWN


def test_kan_ikke_schedule_efter_shutdown_er_infra():
    """Strengen er en Python-fejl, men årsagen er at processen lukkede."""
    svar = derive_close("failed", "cannot schedule new futures after shutdown")
    assert svar["kind"] == INFRA_SHUTDOWN
    assert svar["actor"] == "infra"


def test_de_tre_429_former_giver_samme_kind():
    """Kernen i modulet: samme årsag skrevet på tre måder skal tælle som ÉN.

    Målt i databasen som tre forskellige strenge på tre forskellige
    runde-navne. Uden normalisering ville en optælling vise tre årsager.
    """
    former = [
        "HTTP Error 429: Too Many Requests",
        "first-pass-provider-error: HTTP Error 429: Too Many Requests",
        "followup-round-7-provider-error: HTTP 429: Too Many Requests",
    ]
    kinds = {derive_close("interrupted", s)["kind"] for s in former}
    assert kinds == {PROVIDER_RATE_LIMIT}


def test_429_taeller_ikke_som_generisk_provider_error():
    """Regel-rækkefølgen: 429 skal ramme rate-limit FØR «HTTP Error» sluger den."""
    assert derive_close("failed", "HTTP Error 429")["kind"] == PROVIDER_RATE_LIMIT


def test_401_er_provider_error_ikke_rate_limit():
    assert derive_close("failed", "HTTP Error 401: Unauthorized")["kind"] == PROVIDER_ERROR


@pytest.mark.parametrize(
    "streng",
    [
        "timed out",
        "provider-silence-timeout: timed out waiting for provider stream item",
        "interrupted:agentic-round-1-provider-silence-timeout",
        "interrupted:agentic-round-26-provider-round-timeout",
    ],
)
def test_provider_timeout(streng):
    assert derive_close("interrupted", streng)["kind"] == PROVIDER_TIMEOUT


def test_netvaerksfejl_er_egen_kind():
    """Navneopløsning er ikke providerens svar — det er netværket imellem os."""
    svar = derive_close(
        "failed",
        "<urlopen error [Errno -3] Temporary failure in name resolution>",
    )
    assert svar["kind"] == NETWORK_ERROR


def test_connection_timed_out_er_netvaerk_ikke_provider_timeout():
    """«Connection timed out» er en netværksregel der ligger før timeout-reglen."""
    svar = derive_close("failed", "<urlopen error [Errno 110] Connection timed out>")
    assert svar["kind"] == NETWORK_ERROR


def test_ukendt_model_er_provider_error():
    svar = derive_close(
        "failed",
        "HTTP Error 404: Not Found: {\"error\":\"model 'glm-5.2' not found\"}",
    )
    assert svar["kind"] == PROVIDER_ERROR


@pytest.mark.parametrize(
    "streng",
    [
        "run-abandoned-before-finalization:CancelledError",
        "run-abandoned-before-finalization:GeneratorExit",
        "forced-finalize-unverified",
        "pending-tool-intent",
    ],
)
def test_efterladt_koersel(streng):
    assert derive_close("interrupted", streng)["kind"] == ABANDONED


def test_raa_python_exception_er_runtime_error():
    """Strengen er ikke en lukke-grund men en fejl i vores egen proces."""
    svar = derive_close("failed", "Object of type bytes is not JSON serializable")
    assert svar["kind"] == RUNTIME_ERROR
    assert svar["actor"] == "runtime"


def test_ikke_completed_uden_error_er_unknown_ikke_gaet():
    """Vi ved den ikke blev færdig — men ikke hvorfor. Det skal stå som ukendt."""
    svar = derive_close("cancelled", None)
    assert svar["kind"] == UNKNOWN
    assert svar["clean"] is False
    assert svar["raw"] == ""


def test_raa_streng_bevares_som_bevis_og_klippes():
    lang = "x" * 1000
    svar = derive_close("failed", lang)
    assert len(svar["raw"]) == 300


def test_error_kind_vinder_over_tekst():
    """En struktureret type slår tekst-matching når kalderen har den."""
    svar = derive_close(
        "interrupted",
        "noget der ligner en timeout",
        error_kind="rate_limit",
    )
    assert svar["kind"] == PROVIDER_RATE_LIMIT


def test_derive_for_run_laeser_raekkeform():
    svar = derive_for_run({"status": "interrupted", "error": "api-nedlukning"})
    assert svar["kind"] == INFRA_SHUTDOWN


def test_summarize_slaar_de_tre_429_former_sammen():
    """Slut-testen: optællingen viser ÉN årsag, ikke tre."""
    runs = [
        {"status": "interrupted", "error": "HTTP Error 429: Too Many Requests"},
        {"status": "failed", "error": "first-pass-provider-error: HTTP Error 429"},
        {"status": "interrupted", "error": "followup-round-3-provider-error: HTTP 429"},
        {"status": "completed", "error": None},
        {"status": "interrupted", "error": "api-nedlukning"},
    ]
    tælling = summarize(runs)
    assert tælling[PROVIDER_RATE_LIMIT] == 3
    assert tælling[COMPLETED] == 1
    assert tælling[INFRA_SHUTDOWN] == 1
    # Sorteret faldende — den største årsag står først.
    assert list(tælling)[0] == PROVIDER_RATE_LIMIT
