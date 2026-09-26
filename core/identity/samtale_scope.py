"""Hvis samtaler må denne kørsel læse?

LÆKKEN, 26/9-2026. Bjørn opdagede at en Discord-samtale mellem Jarvis og
Michelle var endt inde i hans egen session: «Det er brud på gpdr».

Roden er at `chat_messages` er ÉN pulje for alle brugere. Enhver forespørgsel
uden `workspace_name`-filter henter alles beskeder. Jarvis lukkede
`user_temperature_engine` (a9c8e8794) og de to beslutnings-kanaler
(4236f8a71); en AST-scan bagefter fandt **18 tilbage**, hvoraf fem hentede
andre brugeres EGNE ord.

## Hvorfor en fælles hjælper og ikke fjorten kopier

`user_temperature_engine` fik sin workspace som PARAMETER, fordi dens indgang
havde en. De øvrige er daemons uden: de kører i hjerteslaget og har kun den
omgivende kontekst. Den er der til gengæld altid —
`workspace_context._DEFAULT_STATE.workspace_name` er `"bjorn"`, så en daemon
uden kontekst lander på ejerens egen workspace af sig selv, og en daemon der
kører inde i et medlems forespørgsel lander på medlemmets.

## Fail-closed, og hvorfor det er det rigtige valg her

Kan workspace ikke bestemmes, læses INTET. Et tomt signal er forkert på den
måde der kan måles og rettes; et signal bygget på en fremmeds ord er forkert
på den måde ingen opdager. Det var netop sådan lækken overlevede: motoren
sendte alles beskeder til deepseek under overskriften «Bjørns sidste 24
timer», og resultatet lignede et gyldigt svar.

## Hvad der IKKE tælles med

`workspace_name = 'default'` er ikke et synonym for Bjørn. Målt 26/9-2026 i
produktionen: 9.198 rækker, 108 sessioner, **stadig skrevet samme dag**, og
142 af dem bærer et Discord-bruger-id. Bucket'en er blandet. At lade den tælle
som ejerens ville genåbne lækken under et andet navn. Samme gælder de 2.379
rækker med tom `workspace_name`.

Prisen er kendt og bevidst: ældre rækker fra før omdøbningen til `"bjorn"`
falder ud af disse signaler. Det er et tab af historik, ikke af korrekthed,
og det kan rettes bagud med en migrering der kun flytter rækker der beviseligt
er hans. Det er en anden opgave end at lukke lækken.
"""
from __future__ import annotations


def aktuel_samtale_workspace() -> str:
    """Workspace hvis samtaler denne kørsel må læse. Tom streng = ingen.

    Kalderen SKAL behandle den tomme streng som «hent intet» — ikke som
    «hent alt». Se `tests/test_samtale_scope.py`, som pinner netop den
    forskel.
    """
    try:
        from core.identity.workspace_context import current_workspace_name
        return (current_workspace_name() or "").strip()
    except Exception:
        # Kan konteksten ikke læses, VED vi ikke hvis samtaler det er.
        # Fail-closed: den tomme streng, ikke et gæt.
        return ""
