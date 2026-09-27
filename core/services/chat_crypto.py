"""Kryptering af chat-historik i databasen (spec §16.2, plan-task 3.3).

## Hvad der var galt

Målt på CT105 27/9-2026: `chat_messages.content` var KLARTEKST for alle — også
for de tre medlemmer. 778 beskeder fra Mikkel, 231 fra Lotte, 162 fra Michelle
lå læsbare i `jarvis.db`. Workspace-FILERNE var krypteret for non-owners; chat-
TABELLEN var det ikke. Grænsen var håndhævet ét sted og ikke det andet.

## Hvem der krypteres — og hvorfor gaten IKKE er fail-safe

`workspace_crypto.should_encrypt` krypterer alt der ikke beviseligt er owner:
ukendt bruger → krypter. Det er rigtigt for filer, hvor owner-skrivninger går
ad en anden vej.

Her ville den regel være en katastrofe. Målt: **25.212 af 74.411 chat-rækker
har tomt `user_id`**, og 62.306 ligger i Bjørns eget workspace. De er hans. En
fail-safe-krypter-alt-ukendt ville låse hans egen historik.

Derfor er gaten her vendt om: en række krypteres kun når den **beviseligt**
tilhører en registreret NON-owner. Workspace først, fordi det er den enhed
§16.2 taler om; derefter `user_id`, så en member der skriver i en delt session
også fanges. Alt andet — tomt, `default`, `public`, ukendt — er klartekst.

Det er ikke en slækkelse af fail-safe, det er en anden retning af den: her er
den farlige fejl at kryptere for meget, ikke for lidt, fordi ingen kan opdage
at 25.000 af ens egne beskeder er blevet ulæselige før man leder efter dem.

## Format og hvem der må læse

Indholdet gemmes som ``enc:v1:<base64>`` i den samme TEXT-kolonne. Kolonnen
``encrypted`` er den autoritative markør; præfikset er krydstjekket, så en
række ikke kan fejllæses hvis de to skulle komme ud af trit.

Der dekrypteres KUN i sessions-læserne i `chat_sessions` — altså når nogen
læser sin egen samtale. Alle andre læsere (statistik, artefakt-indeks,
modsigelses-sporing) ser cifferteksten, og det er MENINGEN: nordstjernen siger
at hverken Bjørn eller Jarvis må kunne læse andres private sessioner.

## Kontakten er tændt som standard

`JARVISX_ENCRYPT_WORKSPACES` styrer fil-krypteringen og har default FRA, så
readers og writers kunne migreres som en no-op. Den er i dag ikke sat i nogen
af systemd-unit'erne på CT105 — krypteringen af filer har været slukket siden
14. juni 2026.

Chat-krypteringen hænger med vilje IKKE på det flag. Her ændres skrive- og
læsesiden i samme commit, så der er ingen migrations-periode at beskytte, og et
default-FRA ville bare gøre dette til endnu et stykke kode der er bygget og
aldrig tilsluttet. Kontakten er `JARVIS_CHAT_ENCRYPTION` og er TÆNDT med mindre
den eksplicit sættes til "0"/"off" — en nødbremse, ikke en afbryder.
"""

from __future__ import annotations

import base64
import logging
import os

logger = logging.getLogger(__name__)

_PRAEFIKS = "enc:v1:"


def kryptering_slaaet_til() -> bool:
    """Nødbremse. Tændt med mindre nogen eksplicit slukker."""
    raa = str(os.environ.get("JARVIS_CHAT_ENCRYPTION", "")).strip().lower()
    return raa not in {"0", "false", "no", "off"}


def medlem_for_raekke(*, workspace_name: str = "", user_id: str = "") -> str | None:
    """`discord_id` for den registrerede NON-owner rækken tilhører, ellers None.

    None betyder klartekst. Se modulets docstring for hvorfor ukendt IKKE
    betyder «krypter».
    """
    ws = str(workspace_name or "").strip()
    uid = str(user_id or "").strip()
    if not ws and not uid:
        return None
    try:
        from core.identity.users import load_users
        brugere = [u for u in load_users() if getattr(u, "role", "") != "owner"]
    except Exception as exc:
        # Kan brugerlisten ikke læses, VED vi ikke om rækken er en members.
        # Så skriver vi klartekst — at kryptere på et gæt ville betyde at
        # rækken ikke kan læses igen hvis gættet var forkert om hvem den var.
        logger.warning("chat_crypto: kunne ikke læse brugerlisten: %s", exc)
        return None
    if ws:
        for u in brugere:
            if str(getattr(u, "workspace", "") or "").strip() == ws:
                return str(u.discord_id)
    if uid:
        for u in brugere:
            if str(getattr(u, "discord_id", "") or "").strip() == uid:
                return str(u.discord_id)
    return None


def medlem_for_session(session_id: str, conn=None) -> str | None:
    """Samme svar som `medlem_for_raekke`, men udledt af sessionen.

    Kompakt-markører skrives uden `workspace_name` og `user_id` — de er en
    `chat_messages`-række med rolle `compact_marker` og ellers næsten ingenting.
    Men en markør sammenfatter samtalen omkring sig, så for en members session
    er den lige så følsom som beskederne. Ejerskabet hentes derfor fra
    sessionens egne beskeder.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return None

    def _slaa_op(c):
        return c.execute(
            "SELECT DISTINCT workspace_name, user_id FROM chat_messages "
            "WHERE session_id = ?", (sid,),
        ).fetchall()

    try:
        if conn is not None:
            raekker = _slaa_op(conn)
        else:
            from core.runtime.db import connect
            with connect() as c:
                raekker = _slaa_op(c)
    except Exception as exc:
        logger.warning("chat_crypto: kunne ikke slå sessionen %s op: %s", sid, exc)
        return None

    # ALLE parrene, ikke det første. Målt 27/9-2026: Michelles session havde
    # sine `user`-rækker tagget `default` og kun `assistant`-rækkerne tagget
    # `michelle`. Et `LIMIT 1` fandt `default`, svarede «ingen ejer», og lod
    # hendes egne ord ligge i klartekst.
    fundne = {
        m for r in raekker
        if (m := medlem_for_raekke(workspace_name=r[0] or "", user_id=r[1] or ""))
    }
    if len(fundne) > 1:
        # To medlemmer i én session findes ikke i dataene i dag (målt: nul).
        # Skulle det opstå, er der ikke ét rigtigt svar — så siges det højt i
        # stedet for at vælge en af dem.
        logger.warning(
            "chat_crypto: session %s har FLERE medlemmer (%s) — krypterer ikke",
            sid, sorted(fundne))
        return None
    return next(iter(fundne), None)


def er_krypteret(raa: object) -> bool:
    return isinstance(raa, str) and raa.startswith(_PRAEFIKS)


def krypter(tekst: str, medlem_id: str) -> str:
    """``enc:v1:<base64>``. Allerede krypteret tekst røres ikke."""
    if not tekst or er_krypteret(tekst):
        return tekst
    from core.services.encryption import encrypt
    from core.services.keyring_store import get_user_key
    blob = encrypt(tekst.encode("utf-8"), get_user_key(medlem_id))
    return _PRAEFIKS + base64.b64encode(blob).decode("ascii")


def dekrypter(raa: str, medlem_id: str) -> str:
    """Modsat `krypter`. Klartekst ind → klartekst ud, uændret.

    Kan den ikke dekrypteres — forkert nøgle, slettet bruger (GDPR §15.2), en
    beskadiget række — returneres cifferteksten SOM DEN ER. Der kastes ikke,
    fordi en enkelt ulæselig besked ikke må vælte visningen af en hel samtale,
    og der gættes ikke på en klartekst der ikke findes.
    """
    if not er_krypteret(raa):
        return raa
    from core.services.encryption import decrypt
    from core.services.keyring_store import get_user_key
    try:
        blob = base64.b64decode(raa[len(_PRAEFIKS):].encode("ascii"))
        return decrypt(blob, get_user_key(medlem_id)).decode("utf-8")
    except Exception as exc:
        logger.warning("chat_crypto: kunne ikke dekryptere en besked: %s", exc)
        return raa


def medlem_for_skrivning(raekke: dict, *, session_id: str = "", conn=None) -> str | None:
    """Hvem rækken tilhører — rækkens egne felter først, ellers SESSIONEN.

    EN SESSION HAR ÉN EJER. Det er ikke en forenkling, det er hvad dataene
    viser. Målt 27/9-2026 på de seks sessioner der involverer et medlem:

    * to havde medlemmets EGNE beskeder tagget `default` og kun Jarvis' svar
      tagget med workspace'et — 19 rækker af deres samtale blev derfor ikke
      fanget af en ren rækkevis regel;
    * én havde elleve `tool`-rækker og ét `assistant`-svar tagget `bjorn`
      INDE I Mikkels session. Ingen `user`-rækker. Det er altså ikke Bjørn der
      skriver — det er Jarvis' eget output der har fået ejerens mærkat.

    Taggingen på skrivestien er med andre ord upålidelig, og samtalen er
    enheden folk oplever. Derfor: findes der ét medlem i sessionen, tilhører
    hele sessionen det medlem.

    Er sessionen ukendt eller tom, falder den tilbage til rækken alene — det er
    tilfældet ved den allerførste besked i en ny session.
    """
    eget = medlem_for_raekke(
        workspace_name=str(raekke.get("workspace_name") or ""),
        user_id=str(raekke.get("user_id") or ""),
    )
    if eget is not None:
        return eget
    sid = str(session_id or raekke.get("session_id") or "")
    if not sid:
        return None
    return medlem_for_session(sid, conn=conn)


def krypter_raekke(raekke: dict, *, session_id: str = "", conn=None) -> dict:
    """Krypter de tekstbærende felter i en chat-række, hvis den er en members.

    Returnerer en NY dict med `encrypted` sat. Rækken ændres ikke på stedet —
    kalderen kan stadig bruge sin egen klartekst til fx at sætte en titel.
    """
    ud = dict(raekke)
    ud.setdefault("encrypted", 0)
    if not kryptering_slaaet_til():
        return ud
    medlem = medlem_for_skrivning(ud, session_id=session_id, conn=conn)
    if medlem is None:
        return ud
    for felt in ("content", "reasoning_content", "content_json"):
        vaerdi = ud.get(felt)
        if isinstance(vaerdi, str) and vaerdi:
            ud[felt] = krypter(vaerdi, medlem)
    ud["encrypted"] = 1
    return ud


def dekrypter_sessionsraekker(
    raekker: list[dict], session_id: str, conn=None
) -> list[dict]:
    """Dekryptér en sessions egne rækker. Kun til sessions-læserne.

    Ejerskabet slås op ÉN gang for sessionen i stedet for pr. række: alle
    rækker i en session tilhører samme bruger, og et opslag pr. besked ville
    koste et brugerfil-læs for hver linje i historikken.

    No-op når intet er krypteret — hvilket er tilfældet for hele Bjørns egen
    historik, altså langt de fleste kald.
    """
    if not raekker:
        return raekker
    if not any(er_krypteret(r.get(f))
               for r in raekker
               for f in ("content", "reasoning_content", "content_json")):
        return raekker
    medlem = medlem_for_session(session_id, conn=conn)
    if medlem is None:
        # Rækkerne ER krypterede, men sessionen kan ikke knyttes til en
        # registreret bruger — fx efter en GDPR-sletning. Så bliver de stående
        # som ciffertekst; der gættes ikke på en nøgle.
        logger.warning(
            "chat_crypto: session %s har krypterede raekker men ingen kendt ejer",
            session_id)
        return raekker
    ud = []
    for r in raekker:
        ny_r = dict(r)
        for felt in ("content", "reasoning_content", "content_json"):
            vaerdi = ny_r.get(felt)
            if isinstance(vaerdi, str):
                ny_r[felt] = dekrypter(vaerdi, medlem)
        ud.append(ny_r)
    return ud


def dekrypter_raekke(raekke: dict) -> dict:
    """Modsat `krypter_raekke`. Bruges KUN af sessions-læserne."""
    if not any(er_krypteret(raekke.get(f))
               for f in ("content", "reasoning_content", "content_json")):
        return raekke
    medlem = medlem_for_raekke(
        workspace_name=str(raekke.get("workspace_name") or ""),
        user_id=str(raekke.get("user_id") or ""),
    )
    if medlem is None:
        return raekke
    ud = dict(raekke)
    for felt in ("content", "reasoning_content", "content_json"):
        vaerdi = ud.get(felt)
        if isinstance(vaerdi, str):
            ud[felt] = dekrypter(vaerdi, medlem)
    return ud
