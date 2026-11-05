"""Kvote for de to dispatch-CLI'er — målt, aldrig gættet.

## Hvorfor det ikke kan være et CLI-kald

Ingen af CLI'erne har en kvote-kommando. `claude usage` behandler «usage» som
en prompt og fejler med 401; `codex debug` har models/app-server/prompt-input
og intet om forbrug. Kilden er derfor HTTP for Claude og en fil for Codex —
målt 4/11-2026 med ægte kald, ikke antaget.

    Claude  GET https://api.anthropic.com/api/oauth/usage
            Authorization: Bearer <CLAUDE_CODE_OAUTH_TOKEN>
            anthropic-beta: oauth-2025-04-20   ← UDEN den er svaret ikke til at stole på
            → five_hour.utilization / .resets_at, seven_day.utilization / .resets_at

    Codex   ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl, hver token_count-event:
            primary   {used_percent, window_minutes: 300,   resets_at <epoch>}  ← 5 timer
            secondary {used_percent, window_minutes: 10080, resets_at <epoch>}  ← 7 dage

## Kontrakten

En læsning er enten `ok=True` med tal, eller `ok=False` med en grund. Der
findes ingen tredje tilstand og ingen standardværdi der ligner et svar. Et
gæt om kvoten er værre end ingen kvote, fordi det ser ud som om nogen har
målt.

## Preflight-beslutningen (skrevet ned, ikke underforstået)

`quota_preflight()` er BLOKERENDE ved ≥100 % af 5-timers-vinduet og kun
ADVARENDE ved ≥90 %. Ved målefejl går den igennem (fail-open).

Begrundelsen er den billigste der faktisk fanger problemet: ved 100 % er
dispatchen dødsdømt — den ville oprette et worktree, spawn'e, og dø efter
sekunder med en fejl der ligner en kodefejl. At blokere der sparer worktreet
og forvirringen. Men en netværksfejl må ikke blokere alt arbejde, for så
bliver preflighten selv den ting der holder systemet nede — og en preflight
der aldrig kaldes er teater. Derfor: bloker på viden, fortsæt på uvidenhed.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
_CLAUDE_BETA = "oauth-2025-04-20"
_CLAUDE_ENV_FILE = "~/.jarvis-v2/config/claude_dispatch.env"
_CLAUDE_CREDENTIALS_FILE = "~/.claude/.credentials.json"
_CODEX_SESSIONS = "~/.codex/sessions"

CACHE_TTL_SECONDS = 60.0
HTTP_TIMEOUT_SECONDS = 5.0

# Tærskler for preflight. 100 = «der er intet tilbage»; 90 = «næste opgave
# kan meget vel være den der rammer loftet».
WARN_PCT = 90.0
BLOCK_PCT = 100.0


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _epoch_iso(value: float) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


@dataclass(frozen=True)
class QuotaReading:
    """Én måling. `ok=False` betyder «jeg ved det ikke», ikke «nul brugt»."""

    ok: bool
    backend: str
    values: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    observed_at: str = ""
    cached: bool = False
    # True = «jeg VED den er doed» (udloebet token, usage limit), ikke
    # «jeg ved det ikke». Preflight blokerer paa den foerste.
    hard_block: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


_CACHE: dict[str, tuple[float, QuotaReading]] = {}


def reset_cache() -> None:
    """Til tests og til når et token er skiftet og cachen lyver."""
    _CACHE.clear()


def _cached(backend: str, loader: Callable[[], QuotaReading]) -> QuotaReading:
    hit = _CACHE.get(backend)
    if hit is not None and (time.monotonic() - hit[0]) < CACHE_TTL_SECONDS:
        prev = hit[1]
        return QuotaReading(
            ok=prev.ok, backend=prev.backend, values=dict(prev.values),
            error=prev.error, observed_at=prev.observed_at, cached=True,
            # Uden denne linje taber et cache-hit «maalt doed»-flaget, og
            # preflighten blokerer kun det FOERSTE kald — derefter siger
            # cachen «tillad» i CACHE_TTL_SECONDS. Maalt 4/11-2026.
            hard_block=prev.hard_block,
        )
    reading = loader()
    _CACHE[backend] = (time.monotonic(), reading)
    return reading


# ── Claude ──────────────────────────────────────────────────────────────────

def _claude_token() -> tuple[str, str]:
    """Token + hvor det kom fra. Miljøet vinder; env-filen er fallback.

    Roterer med CheifOnes Claude Desktop-session, så det må aldrig antages
    evigt. Kilden returneres, så en død fallback kan måles i stedet for at
    blive formodet.
    """
    token = (os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or "").strip()
    if token:
        return token, "env"
    path = Path(os.path.expanduser(_CLAUDE_ENV_FILE))
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:  # env-filen er valgfri — naeste kilde kan baere tokenet
        text = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value, "env_file"
    return _claude_credentials_token()


def _claude_credentials_token() -> tuple[str, str]:
    """Claude Codes egen credentials-fil — den kilde CLI'en selv bruger.

    Målt 4/11-2026 på CheifOne: `claudeAiOauth.accessToken` + `expiresAt`
    (ms). Et udløbet token giver 401 fra både usage-endpointet og
    `claude -p`, så tilstanden rapporteres som MÅLT død med udløbstidspunktet
    i stedet for at ligne «kvoten kunne ikke måles».
    """
    path = Path(os.path.expanduser(_CLAUDE_CREDENTIALS_FILE))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:  # filen findes ikke — saa er der ingen kilde tilbage
        return "", (
            "CLAUDE_CODE_OAUTH_TOKEN mangler i miljøet, i "
            f"{_CLAUDE_ENV_FILE} og i {path}"
        )
    except ValueError:  # filen er ikke JSON — behandl som ingen kilde
        return "", f"{path} kunne ikke parses som JSON"
    oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
    if not isinstance(oauth, dict):
        return "", f"{path} havde ingen claudeAiOauth-sektion"
    value = str(oauth.get("accessToken") or "").strip()
    if not value:
        return "", f"{path} havde intet accessToken"
    expires_ms = float(oauth.get("expiresAt") or 0.0)
    if expires_ms and expires_ms / 1000.0 <= time.time():
        return "", (
            f"Claude-tokenet i {path} er udløbet "
            f"({_epoch_iso(expires_ms / 1000.0)}) — log ind med `claude` igen"
        )
    return value, "credentials_file"


def _load_claude_quota() -> QuotaReading:
    token, source = _claude_token()
    if not token:
        return QuotaReading(
            ok=False, backend="claude", error=source,
            hard_block="udløbet" in source,
        )

    request = urllib.request.Request(_CLAUDE_USAGE_URL, headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": _CLAUDE_BETA,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:  # body er kun ekstra kontekst — HTTP-koden baerer aarsagen
            pass
        # 2026-11-05, maalt med et `claude setup-token`-token: det giver kun
        # inference-scopes. Det KAN koere `claude -p` (verificeret: svar OK,
        # exit 0), men kvote-endpointet kraever `user:profile` og svarer 403
        # `oauth_scope_insufficient`. Det er hverken et doedt token eller en
        # netvaerksfejl — og det maa ALDRIG blive hard_block, for saa blokerer
        # preflighten en backend der virker. Beskeden skal navngive det der
        # mangler, saa den ikke bliver jagtet som et netvaerksproblem.
        if "oauth_scope_insufficient" in detail or "required_scopes" in detail:
            return QuotaReading(
                ok=False, backend="claude",
                error=(
                    "tokenet mangler scopet user:profile "
                    "(et `claude setup-token` har kun inference — kald virker)"
                ),
            )
        if e.code == 401:
            # Afvist token. Det ER viden, ikke uvidenhed: `claude -p` vil
            # fejle med samme token, saa preflighten skal blokere og spare
            # worktreet. Uden hard_block her blev et doedt token meldt som
            # «kunne ikke måles» og sluppet igennem.
            return QuotaReading(
                ok=False, backend="claude", hard_block=True,
                error=(
                    "tokenet blev afvist (HTTP 401) — forny "
                    f"CLAUDE_CODE_OAUTH_TOKEN i {_CLAUDE_ENV_FILE}: {detail.strip()}"
                ),
            )
        return QuotaReading(
            ok=False, backend="claude",
            error=f"HTTP {e.code} fra kvote-endpointet: {detail.strip()}",
        )
    except Exception as e:  # netvaerksfejl maa ikke blive et falsk «kvoten er brugt»
        return QuotaReading(
            ok=False, backend="claude",
            error=f"kvote-endpointet kunne ikke nås ({type(e).__name__}: {e})",
        )

    try:
        data = json.loads(body)
    except ValueError as e:  # endpointet kan svare HTML ved proxy-fejl
        return QuotaReading(
            ok=False, backend="claude",
            error=f"svaret fra kvote-endpointet var ikke JSON: {e}",
        )
    if not isinstance(data, dict):
        return QuotaReading(ok=False, backend="claude", error="svaret var ikke et objekt")

    five = data.get("five_hour") or {}
    week = data.get("seven_day") or {}
    if not five and not week:
        return QuotaReading(
            ok=False, backend="claude",
            error="svaret havde hverken five_hour eller seven_day",
        )

    values = {
        "five_hour_pct": float(five.get("utilization") or 0.0),
        "five_hour_resets_at": str(five.get("resets_at") or ""),
        "seven_day_pct": float(week.get("utilization") or 0.0),
        "seven_day_resets_at": str(week.get("resets_at") or ""),
        "token_source": source,
    }
    return QuotaReading(
        ok=True, backend="claude", values=values, observed_at=_now_iso(),
    )


def claude_quota() -> QuotaReading:
    """5-timers og ugentlig kvote for Claude. Cachet i 60 s."""
    return _cached("claude", _load_claude_quota)


# ── Codex ───────────────────────────────────────────────────────────────────

_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

_CODEX_RESET_RE = re.compile(
    r"try again at ([A-Z][a-z]{2}) (\d{1,2})(?:st|nd|rd|th)?,? (\d{4}) (\d{1,2}):(\d{2}) (AM|PM)"
)


def _codex_usage_limit_reset(tail: str) -> float | None:
    """Epoch for «try again at …» naar den seneste rollout doede paa usage limit.

    Tiden i beskeden er LOKAL (målt 4/11-2026: «2:09 AM» svarede til 01:09 UTC
    i rate_limits), så den parses som naiv lokal tid og konverteres af
    `timestamp()`.
    """
    if "usage limit" not in tail:
        return None
    matches = _CODEX_RESET_RE.findall(tail)
    if not matches:
        return None
    mon, day, year, hour, minute, ampm = matches[-1]
    # Maaneden mappes eksplicit: `%b` er LOCALE-afhaengig, og paa en dansk
    # LC_TIME fejler strptime paa «Nov». Det ville goere vagten tavst
    # inaktiv paa netop den maskine den skal vogte.
    month = _MONTHS.get(mon)
    if month is None:
        return None
    try:
        parsed = datetime(
            int(year), month, int(day),
            int(hour) % 12 + (12 if ampm == "PM" else 0),
            int(minute),
        )
    except ValueError:  # ugyldig dato i beskeden — ingen paalidelig reset-tid
        return None
    return parsed.timestamp()


def _latest_rollout() -> Path | None:
    root = Path(os.path.expanduser(_CODEX_SESSIONS))
    if not root.is_dir():
        return None
    newest: Path | None = None
    newest_mtime = -1.0
    for candidate in root.glob("*/*/*/rollout-*.jsonl"):
        try:
            mtime = candidate.stat().st_mtime
        except OSError:  # filen kan vaere slettet midt i glob — spring over
            continue
        if mtime > newest_mtime:
            newest, newest_mtime = candidate, mtime
    return newest


def _tail_text(path: Path, limit: int = 200_000) -> str:
    """Rollout-filer kan være store; rate_limits står i den nyeste hale."""
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > limit:
            handle.seek(size - limit)
        return handle.read().decode("utf-8", errors="replace")


def _find_key(node: Any, key: str) -> dict[str, Any] | None:
    """Event-strukturen er pakket ind; vi leder efter nøglen, ikke efter en sti."""
    if isinstance(node, dict):
        value = node.get(key)
        if isinstance(value, dict):
            return value
        for child in node.values():
            found = _find_key(child, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for child in node:
            found = _find_key(child, key)
            if found is not None:
                return found
    return None


def _load_codex_quota() -> QuotaReading:
    path = _latest_rollout()
    if path is None:
        return QuotaReading(
            ok=False, backend="codex",
            error=f"ingen rollout-fil under {_CODEX_SESSIONS} — codex er ikke kørt her",
        )
    try:
        tail = _tail_text(path)
    except OSError as e:  # filen kan vaere ryddet mellem glob og laesning
        return QuotaReading(ok=False, backend="codex", error=f"kunne ikke læse {path}: {e}")
    try:
        mtime = path.stat().st_mtime
    except OSError as e:  # samme kaploeb som ovenfor
        return QuotaReading(ok=False, backend="codex", error=f"kunne ikke statte {path}: {e}")

    limits: dict[str, Any] | None = None
    for line in reversed(tail.splitlines()):
        if '"rate_limits"' not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:  # ikke-JSON-linje i rollout — spring over
            continue
        limits = _find_key(event, "rate_limits")
        if limits:
            break

    if not limits:
        return QuotaReading(
            ok=False, backend="codex",
            error=f"ingen rate_limits i {path.name} — filen er muligvis fra før feltet fandtes",
        )

    now = time.time()
    # Codex melder «opbrugt» som primary=null/secondary=null PLUS en
    # task_complete med usage-limit-fejl. Uden dette læses null som 0 % —
    # altså «der er masser tilbage» — og preflighten slipper en dispatch
    # igennem der dør efter sekunder. Målt 4/11-2026: kvoten var tør, mens
    # læseren svarede «0 % brugt».
    blocked_until = _codex_usage_limit_reset(tail)
    if blocked_until is not None and blocked_until > now:
        return QuotaReading(
            ok=True, backend="codex",
            values={
                "primary_pct": 100.0,
                "primary_resets_at": _epoch_iso(blocked_until),
                "primary_expired": False,
                "secondary_pct": 0.0,
                "secondary_resets_at": "",
                "secondary_expired": False,
                "plan_type": str(limits.get("plan_type") or ""),
                "rate_limit_reached_type": "usage_limit",
                "age_seconds": round(now - mtime, 1),
                "source_file": str(path),
                "evidence": "task_complete usage limit",
            },
            observed_at=_epoch_iso(mtime),
            hard_block=True,
        )

    primary = limits.get("primary") or {}
    secondary = limits.get("secondary") or {}

    p_reset = float(primary.get("resets_at") or 0.0)
    s_reset = float(secondary.get("resets_at") or 0.0)
    p_pct = float(primary.get("used_percent") or 0.0)
    s_pct = float(secondary.get("used_percent") or 0.0)

    # Et vindue hvis reset-tidspunkt er passeret, er nulstillet. Det er
    # aritmetik på et målt tidspunkt — ikke et gæt på forbruget.
    p_expired = bool(p_reset and p_reset < now)
    s_expired = bool(s_reset and s_reset < now)
    if p_expired:
        p_pct = 0.0
    if s_expired:
        s_pct = 0.0

    values = {
        "primary_pct": p_pct,
        "primary_resets_at": _epoch_iso(p_reset),
        "primary_expired": p_expired,
        "primary_window_minutes": primary.get("window_minutes"),
        "secondary_pct": s_pct,
        "secondary_resets_at": _epoch_iso(s_reset),
        "secondary_expired": s_expired,
        "secondary_window_minutes": secondary.get("window_minutes"),
        "plan_type": str(limits.get("plan_type") or ""),
        "rate_limit_reached_type": limits.get("rate_limit_reached_type"),
        "age_seconds": round(now - mtime, 1),
        "source_file": str(path),
    }
    return QuotaReading(
        ok=True, backend="codex", values=values, observed_at=_epoch_iso(mtime),
    )


def codex_quota() -> QuotaReading:
    """5-timers (300 min) og ugentlig (10080 min) kvote for Codex."""
    return _cached("codex", _load_codex_quota)


# ── Preflight ──────────────────────────────────────────────────────────────

def _window(reading: QuotaReading) -> tuple[float, str]:
    if reading.backend == "claude":
        return (
            float(reading.get("five_hour_pct") or 0.0),
            str(reading.get("five_hour_resets_at") or ""),
        )
    return (
        float(reading.get("primary_pct") or 0.0),
        str(reading.get("primary_resets_at") or ""),
    )


def quota_preflight(backend: str) -> dict[str, Any]:
    """Skal denne dispatch startes? Svar FØR worktreet oprettes.

    `severity`: ok · warn · block · unknown. `unknown` betyder at kvoten ikke
    kunne måles — og der fortsættes, fordi en målefejl ikke er et bevis for
    at kvoten er opbrugt.
    """
    reading = claude_quota() if backend == "claude" else codex_quota()
    if not reading.ok:
        if reading.hard_block:
            # Maalt doed (fx udloebet token). Det er viden, ikke uvidenhed —
            # og kontrakten siger bloker paa viden.
            return {
                "allow": False, "severity": "block",
                "reason": reading.error,
                "pct": None, "resets_at": "", "reading": reading,
            }
        return {
            "allow": True, "severity": "unknown",
            "reason": f"kvoten kunne ikke måles ({reading.error}) — dispatchen fortsætter",
            "pct": None, "resets_at": "", "reading": reading,
        }

    pct, resets_at = _window(reading)
    label = "5-timers-kvoten" if backend == "claude" else "Codex' 5-timers-vindue"
    if pct >= BLOCK_PCT:
        return {
            "allow": False, "severity": "block",
            "reason": f"{pct:.0f} % af {label} er brugt — reset {resets_at or 'ukendt'}",
            "pct": pct, "resets_at": resets_at, "reading": reading,
        }
    if pct >= WARN_PCT:
        return {
            "allow": True, "severity": "warn",
            "reason": f"{pct:.0f} % af {label} er brugt — reset {resets_at or 'ukendt'}",
            "pct": pct, "resets_at": resets_at, "reading": reading,
        }
    return {
        "allow": True, "severity": "ok",
        "reason": f"{pct:.0f} % af {label} er brugt — reset {resets_at or 'ukendt'}",
        "pct": pct, "resets_at": resets_at, "reading": reading,
    }
