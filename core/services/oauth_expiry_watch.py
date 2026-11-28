"""Vagt for OAuth-refresh-tokens der udloeber — den advarsel der aldrig fandtes.

28/11-2026: Google-forbindelsen doede 25/11 og gav 14.724 fejllinjer i
`cache_warmer_cron.log` over knap tre doegn, foer nogen opdagede det. Aarsagen
var ikke kode: `refresh_token_expires_in` var 604798 s = 7,0 doegn praecis,
hvilket er Googles haarde loft for apps med publishing status «Testing».

Feltet har vaeret gemt i tokenet hele tiden. Maalt 28/11-2026: NUL steder i
`core/` eller `apps/` laeser det — det eneste hit var `core/cli/copilot_auth.py`,
som er en anden provider. Et felt der findes, som ingen ser paa, er samme
fejlklasse som `daemon_health_alert` (bygget, nul kald) og de to 0-byte
brain-poster (indekseret, ulaeselige): mekanismen ser ud som om den virker.

Vagten spoerger ikke «virker tokenet nu» — det goer `get_fresh_token` allerede,
og den fornyer access-tokenet paa 0,09 s. Den spoerger: «hvor laenge holder
det refresh-token jeg ikke selv kan forny». Det er det eneste spoergsmaal
koden ikke selv kan svare sig ud af.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Advarsel naar der er mindre end dette tilbage af refresh-tokenets levetid.
# 5 doegn paa et 7-doegns-loft giver to doegn til at handle — nok til at
# fornyelsen kan planlaegges i aabningstid i stedet for at blive opdaget af
# en log der skriger hvert 10. minut.
_ADVARSEL_DAGE = 5.0

# Under dette antal sekunder betragtes levetiden som ukendt: provideren har
# ikke oplyst den, og et gaet paa «uendelig» ville skjule praecis det vi leder
# efter. Vi advarer ikke, men vi rapporterer at vi ikke ved det.
_UKENDT = 0.0


def _levetid_resterende(tok: dict[str, Any], *, now: float | None = None) -> float | None:
    """Sekunder tilbage af refresh-tokenet, eller None hvis provideren ikke oplyser det.

    Google giver `refresh_token_expires_in` (relativt, ved udstedelsen) og vi
    gemmer `obtained_at`. Andre providere giver intet — der er svaret aerligt
    «ved det ikke» frem for et tal der ser praecist ud.
    """
    levetid = tok.get("refresh_token_expires_in")
    if not levetid:
        return None
    try:
        levetid_f = float(levetid)
    except (TypeError, ValueError):  # en ikke-numerisk levetid er «ukendt», ikke nul
        return None
    if levetid_f <= _UKENDT:
        return None
    udstedt = tok.get("obtained_at")
    if not udstedt:
        # Uden udstedelsestidspunkt kan vi ikke regne restlevetiden ud. At
        # antage «lige udstedt» ville vaere den mest optimistiske af alle
        # antagelser — og den forkerte retning at falde i.
        return None
    try:
        udstedt_f = float(udstedt)
    except (TypeError, ValueError):  # korrupt tidsstempel: vi kan ikke regne, saa vi gaetter ikke
        return None
    ur = float(now if now is not None else time.time())
    return levetid_f - (ur - udstedt_f)


def check_oauth_expiry(*, now: float | None = None) -> dict[str, Any]:
    """Gaa alle brugere og providere igennem; rapportér dem der er taet paa udloeb.

    Read-only: den fornyer intet og skriver intet til tokenet. Fornyelse af et
    refresh-token kraever brugerens samtykke og kan ikke goeres her — det er
    hele pointen med at advare i stedet.
    """
    from core.services import oauth_store

    ur = float(now if now is not None else time.time())
    advarsel_sek = _ADVARSEL_DAGE * 86400.0

    butik = oauth_store.get_runtime_state_value(oauth_store._KEY, {}) or {}
    if not isinstance(butik, dict):
        return {"status": "error", "error": "token-store er ikke et dict", "advarsler": []}

    advarsler: list[dict[str, Any]] = []
    ukendte: list[dict[str, str]] = []
    sunde = 0

    for uid in butik:
        for prov in oauth_store.list_providers(uid):
            tok = oauth_store.get_token(uid, prov)
            if not tok:
                # `None` betyder BEGGE dele: intet token OG dekrypteringen
                # fejlede. Vi kan ikke skelne dem her, saa vi melder det som
                # ulaeseligt i stedet for at gaette paa det ene.
                ukendte.append({"user_id": uid, "provider": prov, "grund": "token-ulaeseligt"})
                continue
            if not tok.get("refresh_token"):
                # Ingen refresh-token = forbindelsen doer med access-tokenet.
                # Det er ikke en udloebsadvarsel, men det er heller ikke sundt.
                ukendte.append({"user_id": uid, "provider": prov, "grund": "intet-refresh-token"})
                continue
            rest = _levetid_resterende(tok, now=ur)
            if rest is None:
                ukendte.append({"user_id": uid, "provider": prov, "grund": "levetid-ukendt"})
                continue
            if rest <= advarsel_sek:
                advarsler.append({
                    "user_id": uid,
                    "provider": prov,
                    "dage_tilbage": round(rest / 86400.0, 2),
                    "udloeber_om_timer": round(rest / 3600.0, 1),
                })
            else:
                sunde += 1

    return {
        "status": "ok",
        "advarsler": advarsler,
        "ukendte": ukendte,
        "sunde": sunde,
        "taerskel_dage": _ADVARSEL_DAGE,
    }


def varsle_om_udloeb(*, now: float | None = None) -> dict[str, Any]:
    """Kør checken og send advarslen til den durable indbakke.

    Samme vej som `daemon_health_alert` bruger: `report_background_outcome`
    med `create_side_task=True`. En ntfy-push forsvinder; en side-opgave
    bliver liggende til nogen har set paa den.
    """
    resultat = check_oauth_expiry(now=now)
    if resultat.get("status") != "ok":
        return resultat

    advarsler = resultat.get("advarsler") or []
    if not advarsler:
        return {**resultat, "varslet": False}

    linjer = [
        f"{a['provider']} (bruger {a['user_id']}): {a['dage_tilbage']} døgn tilbage"
        for a in advarsler
    ]
    tekst = "; ".join(linjer)

    try:
        from core.services.background_attention import report_background_outcome

        report_background_outcome(
            source_kind="oauth-expiry-watch",
            source_id="refresh-token-udloeb",
            status="failed",
            severity="high",
            summary=f"OAuth refresh-token udløber snart — {tekst}",
            suggested_next_step=(
                "Byg et nyt authorize-link med de fulde scopes og send det til brugeren, "
                "så forbindelsen kan fornyes før den dør. Access-tokenet fornyer sig selv; "
                "refresh-tokenet kan kun brugeren forny."
            ),
            requires_attention=True,
            create_side_task=True,
            autonomy_mode="inspect",
            safe_to_continue=True,
        )
    except Exception as exc:
        logger.warning("oauth_expiry_watch: kunne ikke rapportere til indbakken: %s", exc)
        return {**resultat, "varslet": False, "fejl": str(exc)}

    return {**resultat, "varslet": True, "tekst": tekst}
