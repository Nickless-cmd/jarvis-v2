"""Kortlivede, signerede links til udgivne filer.

## Hvorfor de findes

Bjørn 4/10-2026: «når han publicerer filer i chatview er det også uden
brugerens token så links ikke kan åbnes». Målt samme dag: hvert markdown-link
i desk går gennem `openExternal()` til hans OS-browser
(`MarkdownRenderer.tsx:36`), og en ekstern browser kan ikke sættes en
`Authorization`-header på. Filen findes, den er hans egen, og linket giver 401.

En desk-rettelse kan ikke løse det. Enten rejser beviset med i adressen, eller
kan en ekstern browser ikke hente filen. Derfor et signeret link.

## Hvad signaturen dækker, og hvorfor netop det

HMAC over `filnavn|udloeb`. **Begge** led er nødvendige:

* Uden filnavnet kunne ét gyldigt link hente enhver af de 158 filer i
  `~/.jarvis-v2/files/`.
* Uden udløbet i signaturen kunne udløbet selv skrues op i URL'en, og
  «kortlivet» ville være en tekst i en querystring frem for en egenskab.

## Hvad den IKKE dækker: hvem

Signaturen binder ikke et bruger-id, og det er et bevidst valg frem for en
udeladelse. `/files/{filnavn}` har ingen bruger-afgrænsning overhovedet —
målt 4/10: 158 filer i én delt mappe, og enhver autentificeret bruger i huset
kan hente dem alle med sit eget token. Et bruger-bundet link ville altså se ud
som en afgrænsning der ikke findes nedenunder, og det er værre end ingen: man
ville tro filen var privat.

Det signerede link gør derfor ikke adgangen bredere end i dag — det flytter et
60-sekunders vindue ud i en adresse. At lageret er delt er en SELVSTÆNDIG
beslutning, og den ligger hos Bjørn.

## Nøglen

Udledt af `system_api_token` med en domæne-etiket, samme mønster som
`jarvisx_bridge._dispatch_noegle`. To grunde: der skal ikke vedligeholdes et
nyt secret, og en lækket fil-nøgle kan ikke bruges til at forfalske noget
andet. Roteres system-tokenet, dør de gamle links — hvilket er det rigtige.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

#: Domæne-etiket. Ændres den, ugyldiggøres alle udestående links.
_ETIKET: bytes = b"jarvis-fil-link-v1"

#: Standard-levetid. 60 sekunder er nok til at en browser åbner en fane og
#: henter, og for lidt til at linket kan deles videre som en adresse.
STANDARD_LEVETID_S: int = 60

#: Loft. En kalder må gerne bede om kortere, aldrig om længere — ellers er
#: «kortlivet» kalderens valg frem for systemets.
MAKS_LEVETID_S: int = 300


def _noegle() -> bytes:
    """Signerings-nøglen. Tom bytes når den ikke kan udledes.

    Tom frem for en undtagelse, fordi både `signer` og `verificer` skal kunne
    fejle LUKKET: uden nøgle udstedes intet link, og intet link verificerer.
    Kastede den, ville en manglende nøgle blive en 500 på en flade der i
    stedet skal opføre sig som om funktionen ikke findes.
    """
    try:
        from core.runtime.secrets import read_runtime_key
        base = str(read_runtime_key("system_api_token") or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("file_links: kunne ikke laese signerings-grundlaget: %s", exc)
        return b""
    if not base:
        logger.warning("file_links: system_api_token er tom — signerede "
                       "fil-links er slaaet fra")
        return b""
    return hmac.new(base.encode("utf-8"), _ETIKET, hashlib.sha256).digest()


def _rent_navn(filnavn: str) -> str:
    """Filnavnet som det MÅ signeres. Tom streng når det ikke er et blot navn.

    `Path(x).name` på signerings-siden OG på verifikations-siden, så de to
    aldrig kan være uenige om hvad der blev signeret. Var det kun det ene
    sted, kunne `../../etc/passwd` signeres som sig selv og verificeres som
    `passwd`.
    """
    navn = str(filnavn or "").strip()
    if not navn or navn != Path(navn).name or navn in (".", ".."):
        return ""
    return navn


def _signatur(navn: str, udloeb: int, noegle: bytes) -> str:
    besked = f"{navn}|{udloeb}".encode("utf-8")
    return hmac.new(noegle, besked, hashlib.sha256).hexdigest()


def signer(filnavn: str, *, levetid_s: int = STANDARD_LEVETID_S,
           nu: float | None = None) -> dict[str, object]:
    """Udsted et link. `{"status": "ok", "sig": ..., "udloeb": ...}` eller en fejl.

    Typet svar frem for en undtagelse: kalderen er en rute, og et manglende
    secret skal blive en ærlig 503 frem for en stakspor.
    """
    navn = _rent_navn(filnavn)
    if not navn:
        return {"status": "fejl", "error": "ugyldigt filnavn"}
    noegle = _noegle()
    if not noegle:
        return {"status": "fejl", "error": "signering er ikke konfigureret"}
    levetid = max(1, min(int(levetid_s or STANDARD_LEVETID_S), MAKS_LEVETID_S))
    udloeb = int((nu if nu is not None else time.time()) + levetid)
    return {"status": "ok", "navn": navn, "udloeb": udloeb,
            "sig": _signatur(navn, udloeb, noegle), "levetid_s": levetid}


def verificer(filnavn: str, udloeb: object, sig: object,
              *, nu: float | None = None) -> bool:
    """Holder signaturen, og er den stadig i live? Falsk ved enhver tvivl.

    Rækkefølgen er med vilje: formen først, så udløbet, så signaturen. Et
    udløbet link skal ikke koste en HMAC-beregning, og en malformet
    `udloeb` skal ikke nå frem til sammenligningen.

    `compare_digest`, ikke `==`: en almindelig streng-sammenligning afslutter
    ved første forskellige tegn, og den forskel er målbar over mange forsøg.
    """
    navn = _rent_navn(filnavn)
    if not navn:
        return False
    try:
        udl = int(str(udloeb or "").strip())
    except (TypeError, ValueError):
        # Ikke et tal ⇒ ikke et link vi har udstedt. Ingen log: en forkert
        # querystring er normal trafik, ikke en hændelse.
        return False
    sig_s = str(sig or "").strip()
    if not sig_s:
        return False
    if (nu if nu is not None else time.time()) > udl:
        return False
    noegle = _noegle()
    if not noegle:
        return False
    return hmac.compare_digest(_signatur(navn, udl, noegle), sig_s)


__all__ = ["signer", "verificer", "STANDARD_LEVETID_S", "MAKS_LEVETID_S"]
