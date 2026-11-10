"""Udled en normaliseret lukke-grund for en kørsel.

HVORFOR DEN FINDES (målt 10/11-2026 mod `~/.jarvis-v2/state/jarvis.db`):

`visible_runs` har ingen lukke-grund som felt. Den har `status` og `error`,
og `error` er fri tekst. Målt over hele basen:

    25.038  completed   (tom error)
      219  failed      (tom error)
      ~800 interrupted
      ~187 cancelled

De ikke-completed kørsler bærer 40+ DISTINKTE strenge, hvor den samme
årsag optræder i mange former:

    HTTP Error 429: Too Many Requests
    first-pass-provider-error: HTTP Error 429: Too Many Requests
    followup-round-7-provider-error: HTTP 429: Too Many Requests
    ... samme årsag, tre forskellige strenge.

Og nogle strenge er ikke en lukke-grund men en rå Python-exception
(«Object of type bytes is not JSON serializable»). Uden et normaliserende
lag kan man ikke svare på «hvorfor stoppede de 800 kørsler?» uden at
regex-parre fri tekst — og svaret bliver forkert, fordi de tre
429-former tælles som tre forskellige årsager.

Dette modul er laget: en lille fast taksonomi + den rå streng bevaret som
bevis. Det ÆNDRER ingen adfærd — det læser kun de felter der findes.

Bevidst IKKE her: gæt på årsager der ikke står i dataene. Er strengen
ukendt, bliver kind `runtime_error` eller `unknown` — ikke en påstand.
"""

from __future__ import annotations

from typing import Any, Iterable

# Lukke-typer. Værdierne er stabile strenge (de skrives til logs/events),
# så de må ikke omdøbes uden at læsere opdateres.
COMPLETED = "completed"
USER_CANCELLED = "user_cancelled"
ABANDONED = "abandoned"
INFRA_SHUTDOWN = "infra_shutdown"
PROVIDER_RATE_LIMIT = "provider_rate_limit"
PROVIDER_TIMEOUT = "provider_timeout"
PROVIDER_ERROR = "provider_error"
NETWORK_ERROR = "network_error"
RUNTIME_ERROR = "runtime_error"
UNKNOWN = "unknown"

# Hvem/hvad der lukkede kørslen. Bruges til at skelne «vores fejl» fra
# «omverdenens» i en optælling.
AKTOER_BRUGER = "user"
AKTOER_INFRA = "infra"
AKTOER_PROVIDER = "provider"
AKTOER_RUNTIME = "runtime"
AKTOER_INGEN = "none"

# Rækkefølgen er prioriteret: den FØRSTE regel der matcher vinder.
# Mest specifik først — ellers sluger «provider_error» en 429, fordi
# «HTTP Error» også står i den streng.
_REGLER: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        USER_CANCELLED,
        ("user-cancelled", "user_cancelled", "user cancelled"),
        AKTOER_BRUGER,
    ),
    (
        ABANDONED,
        (
            "run-abandoned-before-finalization",
            "forced-finalize-unverified",
            "pending-tool-intent",
        ),
        AKTOER_RUNTIME,
    ),
    (
        INFRA_SHUTDOWN,
        (
            "api-nedlukning",
            "shutdown",
            "container-genstart",
            "proces doede uden at afslutte",
            "proces døde uden at afslutte",
        ),
        AKTOER_INFRA,
    ),
    (
        PROVIDER_RATE_LIMIT,
        ("429", "too many requests", "rate limit", "rate_limit", "rate-limit"),
        AKTOER_PROVIDER,
    ),
    # Netværksreglen ligger FØR timeout-reglen. Målt 10/11-2026: strengen
    # «<urlopen error [Errno 110] Connection timed out>» indeholder «timed out»,
    # så med timeout først blev en netværksfejl rapporteret som et
    # provider-timeout — altså forkert aktør på en fejl vi ikke selv ejer.
    (
        NETWORK_ERROR,
        (
            "urlopen error",
            "name resolution",
            "connection timed out",
            "connection refused",
            "connection reset",
        ),
        AKTOER_PROVIDER,
    ),
    (
        PROVIDER_TIMEOUT,
        (
            "timed out",
            "timeout",
            "silence-timeout",
            "round-timeout",
        ),
        AKTOER_PROVIDER,
    ),
    (
        PROVIDER_ERROR,
        (
            "provider-error",
            "provider_silence",
            "http error",
            "holdt for",
            "returned no",
            "returned empty",
            "model not found",
            "credentials missing",
            "context_length_exceeded",
        ),
        AKTOER_PROVIDER,
    ),
)


def derive_close(
    status: str | None,
    error: str | None,
    *,
    error_kind: str | None = None,
) -> dict[str, Any]:
    """Udled lukke-grunden for én kørsel.

    ``status`` og ``error`` er de to felter `visible_runs` faktisk har.
    ``error_kind`` er valgfri og bruges kun hvis kalderen allerede har en
    struktureret type — den vinder over tekst-matching.

    Returnerer et dict, ikke et objekt: det skal kunne lægges direkte i et
    event-payload eller en log-linje uden serialisering.
    """
    status_s = (status or "").strip().lower()
    error_s = (error or "").strip()
    error_l = error_s.lower()

    if status_s == "completed" and not error_s:
        return _svar(COMPLETED, AKTOER_INGEN, error_s, clean=True)

    # En struktureret type slår tekst-matching, når den findes.
    if error_kind:
        kind_l = error_kind.strip().lower()
        for kind, moenstre, aktor in _REGLER:
            if any(m in kind_l for m in moenstre):
                return _svar(kind, aktor, error_s, clean=False)

    if error_s:
        for kind, moenstre, aktor in _REGLER:
            if any(m in error_l for m in moenstre):
                return _svar(kind, aktor, error_s, clean=False)
        # En ikke-tom streng vi ikke kender: det er en fejl fra vores egen
        # proces (typisk en rå exception), ikke fra omverdenen.
        return _svar(RUNTIME_ERROR, AKTOER_RUNTIME, error_s, clean=False)

    # Ikke-completed UDEN error-streng. Vi ved at den ikke blev færdig, men
    # ikke hvorfor — og så siger vi det, frem for at vælge en plausibel grund.
    return _svar(UNKNOWN, AKTOER_INGEN, "", clean=False)


def _svar(kind: str, aktor: str, raw: str, *, clean: bool) -> dict[str, Any]:
    return {
        "kind": kind,
        "actor": aktor,
        "clean": clean,
        "raw": raw[:300],
    }


def derive_for_run(run: dict[str, Any]) -> dict[str, Any]:
    """Convenience: udled fra en række/dict der ligner `visible_runs`."""
    return derive_close(
        run.get("status"),
        run.get("error"),
        error_kind=run.get("error_kind"),
    )


def summarize(runs: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Tæl kørsler pr. lukke-type.

    Det er her de tre 429-former bliver til ÉT tal — og det er hele pointen
    med modulet.
    """
    tælling: dict[str, int] = {}
    for run in runs:
        kind = derive_for_run(run)["kind"]
        tælling[kind] = tælling.get(kind, 0) + 1
    return dict(sorted(tælling.items(), key=lambda kv: kv[1], reverse=True))
