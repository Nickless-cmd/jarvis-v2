"""Én vej ud for driftsalarmer — gennem routeren, ikke direkte til telefonen.

## Hvorfor den findes (målt 7/10-2026)

`notification_router` har altid haft ntfy som **sidste udvej**: prøv brugerens
enheder først, og kun hvis ingen af dem svarer, ring på telefonen. Men ti
moduler kaldte `ntfy_gateway.send_notification()` direkte og sprang routeren
over. Konsekvensen var målt i beskedhistorikken:

- **Ingen device-awareness.** Alarmen gik til telefonen, uanset om Bjørn sad
  ved desktoppen.
- **Ingen eskalering.** Nåede beskeden ikke frem, skete der intet.
- **Ingen kvittering.** Ingen ack, ingen sporing, ingen genforsøg.
- **Ingen præference.** Slukkede han en slags i indstillinger, kom den
  alligevel — den direkte vej kendte ikke hans valg.
- **Ingen feed-række.** Alarmen stod ingen steder bagefter.

Og fordi `ntfy_topic` er en **offentlig** ntfy.sh-adresse, betød hvert direkte
kald at alarmen også lå frit tilgængeligt for enhver der kendte navnet.

## Hvad helperen gør

Den er ikke et nyt system — den er den vej der allerede fandtes, gjort nem at
kalde. `route_proactive_notification` gør resten: device-aware levering,
eskalering efter 180 s, quiet hours, brugerens kanalvalg, feed-række, og ntfy
som sidste udvej.

## Hvorfor den ikke kaster

Kalderne er daemons og baggrundsveje. En alarm der ikke kan leveres må ikke
vælte den opgave der udløste den — `central_core` skriver en incident, og
`config_drift` markerer drift. De skal kunne fortsætte. Fejlen logges, og
returværdien siger sandt hvad der skete.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def send_alert(
    *,
    titel: str,
    tekst: str,
    slags: str = "infra_security",
    importance: str = "high",
    session_id: str = "",
) -> bool:
    """Send en driftsalarm gennem routeren. Returnerer True hvis den blev leveret.

    `slags` er routerens kanal-nøgle: en ukendt slags falder til `auto`, som er
    device-aware med ntfy som sidste udvej — præcis den opførsel en alarm skal
    have. `infra_security` er standarden fordi den allerede er defineret som
    «altid importance=high: vært/net i fare».

    `importance="critical"` omgår quiet hours. Brug det kun når alarmen ikke
    kan vente til kl. 07 — en CPU-temperatur kan, et kompromitteret system kan
    ikke.
    """
    try:
        from core.identity.owner_resolver import owner_user_id
        uid = owner_user_id()
        if not uid:
            log.warning("alarm uden ejer — kan ikke leveres: %s", titel)
            return False
        from core.services import notification_router
        result = notification_router.route_proactive_notification(
            uid,
            slags,
            {"title": titel, "preview": tekst, "body": tekst, "kind": slags,
             "session_id": session_id},
            importance=importance,
        )
        leveret = bool(result.get("delivered"))
        if not leveret:
            # Ikke en fejl i sig selv — quiet hours lægger den i kø, og det er
            # den rigtige opførsel. Logges så et vedvarende «failed» kan ses.
            log.warning("alarm ikke leveret (kanal=%s): %s",
                        result.get("channel"), titel)
        return leveret
    except Exception:
        log.warning("alarm kunne ikke routes: %s", titel, exc_info=True)
        return False
