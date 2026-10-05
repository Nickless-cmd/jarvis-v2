"""Lageret bag indbakken: `inbox_items`.

Opgave 1 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.

Hvorfor en EGEN tabel, og ikke `session_inbox`:
`session_inbox` er en **leveringskø**. `flush_session` sætter
`status='delivered'`, hvorefter `pending_for_session` ikke længere viser posten
— og «leveret» er ikke «afgjort». En post skal kunne stå åben efter levering,
efter en procesgenstart og uden en aktiv session, indtil nogen træffer en
afgørelse om den. Derfor en separat, idempotent kvittering.

Tre ting i skemaet er valgt mod målte fejl i huset:

* **Ensure-én-gang-per-proces.** `CREATE TABLE IF NOT EXISTS` tager eksklusiv
  lås. Målt 9/9-2026: en ensure-funktion kaldt pr. brugerbesked fra en
  daemon-tråd gav `sqlite3.OperationalError: database is locked` med ~50 %
  frekvens i suiten, fordi en samtidig `INSERT INTO chat_messages` ikke kunne
  få låsen inden `busy_timeout`. Rettelsen (ensure én gang pr. proces) stod som
  en separat opgave for den gamle tabel; den nye tabel får den fra starten frem
  for at arve fejlen.
* **Ingen payload.** Posten bærer sti OG størrelse, aldrig indhold. Et jobs
  output kan være 112 kB; lander det her, lander det i promptens hale, og så er
  kontrolfladen blevet den byrde den skulle lette.
* **Bruger er altid eksplicit.** Uden bruger-id spørges der `1 = 0` — ingen
  liste over alle brugere. Husstanden har flere brugere, og de andres
  workspaces er krypterede; en indbakke der blander dem er et databrud.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)

# Åben = kan stadig gate (hvis ejeren er verificeret). Alt andet er terminalt.
STATUS_AABEN: Final[str] = "aaben"
STATUS_DONE: Final[str] = "done"
STATUS_DROP: Final[str] = "drop"
#: Opgave 8: posten døde af sig selv. Terminal, ikke en sletning.
STATUS_UDLOEBET: Final[str] = "udloebet"
#: Opgave 9: kilden meldte sig færdig. En NEDGRADERING — beviset slettes ikke.
STATUS_AFSLUTTET_AF_KILDE: Final[str] = "afsluttet_af_kilde"

TERMINALE_STATUSSER: Final[frozenset[str]] = frozenset({
    STATUS_DONE, STATUS_DROP, STATUS_UDLOEBET, STATUS_AFSLUTTET_AF_KILDE,
})

#: `jarvis` = verificeret som hans eget arbejde, må gate. `huset` = daemon,
#: heartbeat, recurring — må oprette, aldrig gate. `ukendt` = proveniensen kunne
#: ikke bevises; synlig, men aldrig blokerende.
EJER_JARVIS: Final[str] = "jarvis"
EJER_HUSET: Final[str] = "huset"
EJER_UKENDT: Final[str] = "ukendt"
#: `bruger` (4/10-2026): et MENNESKE har flagget posten. Egen værdi, ikke
#: `jarvis`, fordi de to har forskellig betydning i visningen og i gaten: en
#: Jarvis-post er noget HAN har lovet, en bruger-post er noget nogen har bedt
#: om. Og mærket skal kunne læses på linjen — `[dig]` mod `[bjørn]`.
EJER_BRUGER: Final[str] = "bruger"

_skema_klar = False
_skema_laas = threading.Lock()


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_skema(conn: sqlite3.Connection) -> None:
    """DDL ÉN gang pr. proces — se modulets docstring om den eksklusive lås."""
    global _skema_klar
    if _skema_klar:
        return
    with _skema_laas:
        if _skema_klar:  # en anden tråd kom først
            return
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inbox_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bruger_id TEXT NOT NULL,
                kildetype TEXT NOT NULL,
                kilde_id TEXT NOT NULL,
                oprettende_run_id TEXT NOT NULL DEFAULT '',
                verificeret_ejer TEXT NOT NULL DEFAULT 'ukendt',
                kraever_handling INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'aaben',
                beskrivelse TEXT NOT NULL DEFAULT '',
                output_sti TEXT NOT NULL DEFAULT '',
                output_bytes INTEGER,
                paamindelser INTEGER NOT NULL DEFAULT 0,
                sidste_paamindelse_at TEXT NOT NULL DEFAULT '',
                sidste_paamindelse_tur TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                afgjort_at TEXT NOT NULL DEFAULT '',
                afgjort_grund TEXT NOT NULL DEFAULT '',
                UNIQUE (bruger_id, kildetype, kilde_id)
            )
            """
        )
        _ensure_kolonner(conn)
        # Visningen spørger altid «åbne poster for DENNE bruger», og gaten
        # spørger det samme. Indekset bærer bruger først, fordi det er den
        # kolonne der ALDRIG er fri.
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_inbox_items_bruger_status
            ON inbox_items(bruger_id, status, id DESC)
            """
        )
        _skema_klar = True


#: Kolonner tilfoejet EFTER foerste udgave. Mønstret er husets:
#: `ALTER TABLE` i en idempotent ensure, ikke en migrations-fil.
#:
#: `expires_at` (Opgave 8): TOM streng = udløber ALDRIG, og det er et bevidst
#: valg frem for NULL. Tom streng sorterer FØR enhver ISO-dato, så en `<`-
#: sammenligning i SQL ville gøre hver post uden udløb til «udløbet» — derfor
#: har hver forespørgsel om udløb også et `expires_at != ''`.
#: `bloker` (4/10-2026, Opgave «bug-endpoint»): må DENNE post nægte en
#: mutation, selv om ejeren ikke er `jarvis`?
#:
#: Normalt kræver gating `verificeret_ejer == "jarvis"` — det du selv har
#: lovet kommer tilbage til dig. En post Bjørn flagger har HAM som ejer, så
#: den ville aldrig kunne gate under den regel.
#:
#: Bjørns valg 4/10: «synlig men gater ikke som standard». Så feltet er 0 som
#: default, og kun en eksplicit handling fra den autentificerede principal kan
#: sætte det. Det er den stærkeste proveniens der findes: huset kan informere,
#: Jarvis kan binde sig selv, og Bjørn kan kræve — men kun når han siger det.
_SENERE_KOLONNER: Final[tuple[tuple[str, str], ...]] = (
    ("expires_at", "TEXT NOT NULL DEFAULT ''"),
    ("bloker", "INTEGER NOT NULL DEFAULT 0"),
)


def _ensure_kolonner(conn: sqlite3.Connection) -> None:
    """Tilføj kolonner der kom senere. Idempotent; kaster ikke på en dublet."""
    kendte = {r[1] for r in conn.execute("PRAGMA table_info(inbox_items)")}
    for navn, type_ in _SENERE_KOLONNER:
        if navn in kendte:
            continue
        try:
            conn.execute(f"ALTER TABLE inbox_items ADD COLUMN {navn} {type_}")
        except sqlite3.OperationalError as exc:
            # En anden proces kan have tilfoejet den mellem PRAGMA og ALTER.
            # «duplicate column» er altsaa et NORMALT udfald her, ikke en fejl
            # — men alt ANDET skal ses.
            if "duplicate column" not in str(exc).lower():
                logger.warning("db_inbox: kunne ikke tilfoeje %s: %s", navn, exc)


def _post_fra_raekke(r: sqlite3.Row) -> dict[str, Any]:
    """Rækken som en typet post. `output_bytes` bevarer sin NULL.

    `None` og `0` betyder IKKE det samme: `0 B` er en ægte tom fil, mens `None`
    er «filen er væk, størrelsen kan ikke oplyses». Mappes de sammen, kan
    visningen ikke skelne dem — og så står «0 B» hvor der burde stå at
    artefaktet er forsvundet.
    """
    b = r["output_bytes"]
    post = {
        "id": str(r["kilde_id"]),
        "bruger_id": str(r["bruger_id"]),
        "kildetype": str(r["kildetype"]),
        "kilde_id": str(r["kilde_id"]),
        "oprettende_run_id": str(r["oprettende_run_id"] or ""),
        "verificeret_ejer": str(r["verificeret_ejer"] or EJER_UKENDT),
        "kraever_handling": bool(r["kraever_handling"]),
        "status": str(r["status"]),
        "beskrivelse": str(r["beskrivelse"] or ""),
        "output_sti": str(r["output_sti"] or ""),
        "output_bytes": None if b is None else int(b),
        "paamindelser": int(r["paamindelser"] or 0),
        "sidste_paamindelse_at": str(r["sidste_paamindelse_at"] or ""),
        "sidste_paamindelse_tur": str(r["sidste_paamindelse_tur"] or ""),
        "created_at": str(r["created_at"] or ""),
        "afgjort_at": str(r["afgjort_at"] or ""),
        "afgjort_grund": str(r["afgjort_grund"] or ""),
        "expires_at": _felt(r, "expires_at"),
        "bloker": _felt(r, "bloker") in ("1", "True", "true"),
    }
    # ── Opgave 8: udløb er en BEREGNET tilstand ─────────────────────────────
    #
    # Den sættes her, ved LÆSNINGEN — ikke kun i fejeren. Posten dør i det
    # øjeblik nogen læser den, uden at et job skal køre. Fejeren skriver
    # derefter den terminale tilstand, så en post INGEN læser også får den;
    # det er hele grunden til at Opgave 8 bygges som begge dele og ikke som
    # beregningen alene (se `fej_udloebne`).
    #
    # `kraever_handling` falder SAMME sted, og det er spec'ens egen
    # begrundelse: «en post ikke kan gate i det uendelige ved at ingen rører
    # den.» Uden det led ville en udløbet post blive ved med at nægte en
    # mutation — en død post der blokerer.
    #
    # MÅLT 5/10-2026: funktionen fandtes, men blev kaldt NUL steder i
    # produktionen, så enhver frist var virkningsløs. Samme fejlform som
    # `expire_stale` havde, før `approval_expiry_daemon` blev skrevet.
    post["udloebet"] = er_udloebet(post)
    if post["udloebet"]:
        post["kraever_handling"] = False
    return post


def _felt(r: sqlite3.Row, navn: str) -> str:
    """Læs en kolonne der måske ikke findes i DENNE række endnu.

    En proces der kører den gamle kode kan have læst rækken før `ALTER TABLE`
    nåede at køre. Fald mod tom streng — altså «udløber aldrig» — frem for at
    kaste: en manglende kolonne må ikke kunne vælte en visning.
    """
    try:
        v = r[navn]
    except (IndexError, KeyError):  # kolonnen findes ikke i DENNE raekke endnu
        return ""
    return "" if v is None else str(v)


#: Opgave 8: hvor længe en post der KAN nægte en mutation må leve.
#:
#: Tallet står ét sted og kan ændres uden at røre andet. 30 dage er valgt som
#: «længere end nogen forpligtelse i dette hus har levet målt, og kortere end
#: for evigt» — den eneste grænse der ikke kan være vilkårlig er den øvre.
_FRIST_DAGE: Final[int] = 30


def opret_eller_hent(
    *,
    bruger_id: str,
    kildetype: str,
    kilde_id: str,
    oprettende_run_id: str = "",
    verificeret_ejer: str = EJER_UKENDT,
    kraever_handling: bool = False,
    beskrivelse: str = "",
    output_sti: str = "",
    output_bytes: int | None = None,
    bloker: bool = False,
    expires_at: str = "",
) -> dict[str, Any]:
    """Idempotent registrering. Findes posten, returneres DEN — urørt.

    Genlevering af samme notifikation må ikke nulstille påmindelsestælleren
    eller en truffet afgørelse. `INSERT OR IGNORE` plus et efterfølgende opslag
    gør begge dele i én runde uden at læse-skrive-kapløbe: taber vi kapløbet om
    indsættelsen, finder opslaget den andens række, hvilket er netop det
    idempotente svar.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    kildetype = str(kildetype or "").strip()
    if not bruger_id or not kilde_id or not kildetype:
        return {"status": "fejl", "error": "bruger_id, kildetype og kilde_id kraeves"}
    # ── Produsenten for `expires_at` (Opgave 8, målt 5/10-2026) ─────────────
    #
    # Feltet havde nul skrivere i drift: `saet_udloeb()` fandtes, men blev
    # kaldt NUL steder uden for tests, og ingen post havde nogensinde båret en
    # frist. Reglen lægges HER og ikke hos de fire kaldere, fordi både
    # `kraever_handling` og `bloker` er kendt netop her — tre kopier ville
    # være tre steder at holde enige.
    #
    # HVEM får en frist: kun en post der KAN nægte en mutation. Det er
    # spec'ens egen sætning — «kraever_handling falder ved udløb, så en post
    # ikke kan gate i det uendelige ved at ingen rører den». En informerende
    # post uden frist er harmløs; en blokerende post uden frist er en
    # permanent lås.
    #
    # HVEM får den IKKE: de kildetyper der ikke kan gate. En beslutnings-post
    # genregistreres af sin kilde hver runde, og en frist ville slås mod
    # `genaabn_af_kilde` — posten ville udløbe og blive genåbnet i ét væk.
    if not str(expires_at or "").strip() and (kraever_handling or bloker):
        expires_at = (datetime.now(UTC) + timedelta(days=_FRIST_DAGE)).isoformat()
    with connect() as conn:
        _ensure_skema(conn)
        conn.execute(
            """
            INSERT OR IGNORE INTO inbox_items (
                bruger_id, kildetype, kilde_id, oprettende_run_id,
                verificeret_ejer, kraever_handling, status, beskrivelse,
                output_sti, output_bytes, created_at, bloker, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bruger_id, kildetype, kilde_id, str(oprettende_run_id or ""),
             str(verificeret_ejer or EJER_UKENDT), 1 if kraever_handling else 0,
             STATUS_AABEN, str(beskrivelse or ""), str(output_sti or ""),
             output_bytes, _nu(), 1 if bloker else 0, str(expires_at or "")),
        )
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kildetype = ? "
            "AND kilde_id = ?",
            (bruger_id, kildetype, kilde_id),
        ).fetchone()
    if r is None:
        # Skrivningen fejlede uden at kaste. Det er husets hyppigste fejlform:
        # en fejl der bliver en vaerdi man ikke kan skelne fra et lovligt svar.
        # Her bliver den en TYPET fejl, og kalderen skal laese den.
        return {"status": "fejl", "error": "posten kunne ikke skrives eller laeses"}
    return {"status": "ok", "post": _post_fra_raekke(r)}


def hent(*, bruger_id: str, kilde_id: str) -> dict[str, Any] | None:
    """Én post for ÉN bruger. Ingen bruger ⇒ None, aldrig en anden brugers."""
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    if not bruger_id or not kilde_id:
        return None
    with connect() as conn:
        _ensure_skema(conn)
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
    return None if r is None else _post_fra_raekke(r)


def liste(
    *,
    bruger_id: str,
    kun_aabne: bool = True,
    maks: int = 500,
) -> list[dict[str, Any]]:
    """Poster for ÉN bruger. Tom bruger ⇒ tom liste, ALDRIG alle brugeres.

    `list_pending_for_current_user()` læser alle ved tom kontekst, og
    `list_wakeups()` er global. Den slags implicit kontekst er grunden til at
    denne funktion kræver bruger-id som nøgleord uden standardværdi.
    """
    bruger_id = str(bruger_id or "").strip()
    if not bruger_id:
        return []
    sql = "SELECT * FROM inbox_items WHERE bruger_id = ?"
    p: list[Any] = [bruger_id]
    if kun_aabne:
        sql += " AND status = ?"
        p.append(STATUS_AABEN)
    sql += " ORDER BY id ASC LIMIT ?"
    p.append(max(int(maks), 1))
    with connect() as conn:
        _ensure_skema(conn)
        rows = conn.execute(sql, tuple(p)).fetchall()
    return [_post_fra_raekke(r) for r in rows]


def afgoer(
    *,
    bruger_id: str,
    kilde_id: str,
    ny_status: str,
    grund: str = "",
) -> dict[str, Any]:
    """Sæt en terminal status. Idempotent: en allerede afgjort post ændres IKKE.

    Returnerer typet: `ok` (vi afgjorde den nu), `allerede` (den var afgjort —
    med den status den HAR, ikke den vi bad om), `ukendt` (ingen sådan post for
    denne bruger) eller `fejl`. Aldrig prosa, og `ukendt` må aldrig komme ud som
    en succes: et ukendt id der melder «ok» er præcis den fejlform huset rammer
    oftest.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    if ny_status not in TERMINALE_STATUSSER:
        return {"status": "fejl", "error": f"ikke en terminal status: {ny_status}"}
    if not bruger_id or not kilde_id:
        return {"status": "fejl", "error": "bruger_id og kilde_id kraeves"}
    with connect() as conn:
        _ensure_skema(conn)
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
        if r is None:
            return {"status": "ukendt", "id": kilde_id}
        nuv = str(r["status"])
        if nuv in TERMINALE_STATUSSER:
            return {"status": "allerede", "id": kilde_id, "havde": nuv}
        # `status = 'aaben'` i WHERE gør skrivningen atomar mod en samtidig
        # afgørelse: taber vi kapløbet, rammer UPDATE nul rækker, og vi melder
        # `allerede` frem for at overskrive den andens afgørelse.
        cur = conn.execute(
            "UPDATE inbox_items SET status = ?, kraever_handling = 0, "
            "afgjort_at = ?, afgjort_grund = ? "
            "WHERE bruger_id = ? AND kilde_id = ? AND status = ?",
            (ny_status, _nu(), str(grund or ""), bruger_id, kilde_id, STATUS_AABEN),
        )
        if cur.rowcount == 0:
            r2 = conn.execute(
                "SELECT status FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
                (bruger_id, kilde_id),
            ).fetchone()
            return {"status": "allerede", "id": kilde_id,
                    "havde": str(r2["status"]) if r2 else "ukendt"}
    return {"status": "ok", "id": kilde_id, "ny_status": ny_status}


#: De to statusser der betyder UDSÆTTELSE, ikke afslutning. Kun de to må en
#: kilde genåbne: `done` er udført arbejde, og `afsluttet_af_kilde` betyder
#: kilden er væk — at genoplive nogen af dem ville genåbne noget afgjort.
GENAABNING_STATUSSER: Final[frozenset[str]] = frozenset({
    STATUS_DROP, STATUS_UDLOEBET,
})


def genaabn_af_kilde(*, bruger_id: str, kilde_id: str) -> dict[str, Any]:
    """Genåbn en post der blev UDSAT, når dens kilde stadig melder den aktuel.

    ## Hvorfor den findes (målt 5/10-2026)

    `registrer_i_indbakken`s docstring lovede at en droppet beslutnings-post
    «kommer tilbage ved næste registrering, fordi beslutningen stadig står under
    tærsklen». Det kunne den ikke — og ingen af de tre veje bar det:

    * `expires_at` blev aldrig sat (tom streng ⇒ udløber ALDRIG, se `er_udloebet`).
    * `saet_udloeb()` er den eneste skriver af feltet og havde NUL kaldere
      uden for tests.
    * `opret_eller_hent` er `INSERT OR IGNORE` + opslag og returnerer en
      EKSISTERENDE række urørt — så genregistrering var en no-op for en post der
      allerede fandtes.

    Målt i drift: 76 beslutnings-poster stod i `drop` og kom aldrig igen. Det er
    præcis den fejlform gatens egen begrundelse advarer mod: «et bånd der kan
    revoke, sletter systematisk de svære og beholder de lette — den modsatte af
    læring.»

    ## Grænsen, og hvorfor den er sikker

    Kun `drop` og `udloebet` kan genåbnes. Kalderen (`registrer_kilde`) gater
    desuden på KILDETYPEN: kun en post der ikke kan nægte en mutation må flyttes
    af sin kilde. Ellers kunne en daemon genåbne en blokerende post og dermed
    omgå skrive-kontrakten ad en ny vej.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    if not bruger_id or not kilde_id:
        return {"status": "fejl", "error": "bruger_id og kilde_id kraeves"}
    with connect() as conn:
        _ensure_skema(conn)
        # `status IN (…)` i WHERE gør skrivningen atomar mod en samtidig
        # afgørelse: rammer vi nul rækker, var posten ikke til at genåbne.
        cur = conn.execute(
            "UPDATE inbox_items SET status = ?, kraever_handling = 0, "
            "afgjort_at = '', afgjort_grund = '', paamindelser = 0, "
            "sidste_paamindelse_at = '', sidste_paamindelse_tur = '', "
            # Fristen ryddes SAMMEN med genåbningen (5/10-2026). Ellers arvede
            # en genåbnet post den frist der netop fik den til at udløbe, og
            # den ville være død igen i samme sekund — `er_udloebet` er
            # beregnet ved læsning. Genåbningen sætter samtidig
            # `kraever_handling = 0`, så posten ikke længere kan gate og
            # derfor heller ikke har brug for en frist.
            "expires_at = '' "
            "WHERE bruger_id = ? AND kilde_id = ? AND status IN (?, ?)",
            (STATUS_AABEN, bruger_id, kilde_id, STATUS_DROP, STATUS_UDLOEBET),
        )
        if cur.rowcount == 0:
            return {"status": "allerede", "id": kilde_id}
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
    if r is None:
        return {"status": "fejl", "error": "posten kunne ikke genaabnes"}
    return {"status": "ok", "id": kilde_id, "post": _post_fra_raekke(r)}


def opdater_beskrivelse(
    *, bruger_id: str, kilde_id: str, beskrivelse: str,
) -> dict[str, Any]:
    """Lad kilden rette TEKSTEN på en post der ikke er afgjort.

    ## Hvorfor den findes (målt 5/10-2026)

    `opret_eller_hent` er `INSERT OR IGNORE` plus et opslag, så en posts
    beskrivelse blev skrevet ÉN gang og derefter FROSSET. For en beslutnings-post
    er teksten «[<bånd> <score>%] <direktiv>» — og scoren er LEVENDE: den ændrer
    sig hver gang et review dømmer beslutningen. Målt i drift:
    `dec_b596dcde9db7` stod med «[imperativ 33%]» i indbakken mens
    `decision_adherence_section()` viste «Adherence 50% (advisory band)». Den
    flade Bjørn læser løj om båndet.

    Det er samme fejlform som `expires_at` (samme dag): en regel der kun gælder
    ved INSERT dækker ikke de rækker der allerede står der.

    ## Snapshot eller visning?

    Beskrivelsen er en VISNING, ikke et snapshot. Et snapshot beskriver hvad der
    skete på et tidspunkt, og dér er en frossen tekst korrekt. Denne post peger
    på en AKTUEL forpligtelse, og båndet er en egenskab ved beslutningen NU — så
    teksten skal følge den. Derfor opdateres den, frem for at visningen
    genberegner båndet: tærsklerne (`_CRITICAL_THRESHOLD`, `_ADVISORY_THRESHOLD`)
    bor i gaten, og en kopi i visningen ville drive fra dem.

    ## Grænsen

    Kun en post der er `aaben`. `done` er udført arbejde og
    `afsluttet_af_kilde` betyder kilden er væk; ny tekst ind i dem ville ændre
    en afsluttet historik. En `drop`/`udloebet`-post får sin tekst i samme runde
    den genåbnes — `genaabn_af_kilde` sætter `aaben` først, og kalderen
    (`inbox_state.registrer_kilde`) retter teksten EFTER genåbningen.

    Returnerer typet, aldrig prosa: `ok` (retter nu), `uaendret` (teksten var
    identisk — nul rækker, ingen skrivning), `afgjort` (posten er ikke aaben),
    `ukendt` (ingen sådan post) eller `fejl`.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    ny = str(beskrivelse or "")
    if not bruger_id or not kilde_id:
        return {"status": "fejl", "error": "bruger_id og kilde_id kraeves"}
    if not ny:
        # En tom tekst er ikke en rettelse. Uden dette led ville en kilde der et
        # øjeblik ikke KENDER sin tekst kunne slette den eneste posten har.
        return {"status": "allerede", "id": kilde_id, "grund": "tom beskrivelse"}
    with connect() as conn:
        _ensure_skema(conn)
        # `beskrivelse != ?` gør skrivningen idempotent: uændret tekst rører nul
        # rækker, så en kilde der melder det samme hvert tick er gratis.
        cur = conn.execute(
            "UPDATE inbox_items SET beskrivelse = ? "
            "WHERE bruger_id = ? AND kilde_id = ? AND status = ? "
            "AND beskrivelse != ?",
            (ny, bruger_id, kilde_id, STATUS_AABEN, ny),
        )
        if cur.rowcount == 0:
            # Nul rækker betyder ÉN af tre ting, og de er ikke det samme. Vi
            # skelner, fordi en kalder der læser «uaendret» om en post der ikke
            # findes bygger på et fravær der ikke er der — og `ukendt` må aldrig
            # komme ud som en succes.
            r0 = conn.execute(
                "SELECT status FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
                (bruger_id, kilde_id),
            ).fetchone()
            if r0 is None:
                return {"status": "ukendt", "id": kilde_id}
            if str(r0["status"]) != STATUS_AABEN:
                return {"status": "afgjort", "id": kilde_id,
                        "status_fundet": str(r0["status"])}
            return {"status": "uaendret", "id": kilde_id}
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
    if r is None:
        return {"status": "fejl", "error": "posten forsvandt under opdateringen"}
    return {"status": "ok", "id": kilde_id, "post": _post_fra_raekke(r)}


def noter_paamindelse(*, bruger_id: str, kilde_id: str, tur: str) -> dict[str, Any]:
    """Tæl ÉN leveret påmindelse. Samme tur to gange tæller ÉN gang.

    Tælleren skal være durabel og per post: en volatil tæller nulstillede sig
    ved en procesgenstart, og påmindelsen kom aldrig. Og `tur`-nøglen findes
    fordi trin 1 ikke må fyre i hver runde — uden den ville en enkelt tur kunne
    tælle sig op til tærsklen alene og springe hele den høflige anmodning over.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    tur = str(tur or "").strip()
    if not bruger_id or not kilde_id or not tur:
        return {"status": "fejl", "error": "bruger_id, kilde_id og tur kraeves"}
    with connect() as conn:
        _ensure_skema(conn)
        cur = conn.execute(
            "UPDATE inbox_items SET paamindelser = paamindelser + 1, "
            "sidste_paamindelse_at = ?, sidste_paamindelse_tur = ? "
            "WHERE bruger_id = ? AND kilde_id = ? AND status = ? "
            "AND sidste_paamindelse_tur != ?",
            (_nu(), tur, bruger_id, kilde_id, STATUS_AABEN, tur),
        )
        if cur.rowcount == 0:
            r = conn.execute(
                "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
                (bruger_id, kilde_id),
            ).fetchone()
            if r is None:
                return {"status": "ukendt", "id": kilde_id}
            if str(r["sidste_paamindelse_tur"]) == tur:
                return {"status": "samme_tur", "id": kilde_id,
                        "paamindelser": int(r["paamindelser"] or 0)}
            return {"status": "ikke_aaben", "id": kilde_id, "havde": str(r["status"])}
        r = conn.execute(
            "SELECT paamindelser FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
    return {"status": "ok", "id": kilde_id,
            "paamindelser": int(r["paamindelser"]) if r else 0}


# ── Opgave 8: udløb ─────────────────────────────────────────────────────────
#
# BESLUTNINGEN (trin 1): udløb bygges, og det bygges som **beregnet tilstand
# PLUS en fejer** — ikke beregnet alene.
#
# Præcedensen er godkendelsernes, men den siger det modsatte af hvad dens form
# antyder. `db_governance` beregner `effective_approval_state` ved læsning,
# præcis som en «doven» løsning ville. Og `sweep_expired_intents` blev
# TILFØJET bagefter, med sin egen begrundelse:
#
#   «Udloebet er DOVENT: det sker naar den samme intention slaas op paa ny. En
#    intention ingen spoerger til igen bliver derfor staaende `pending` for
#    evigt. MAALT 10/9-2026: fire raekker med udloeb 23, 50, 115 og 115 dage
#    tilbage i tiden, alle stadig `pending`.»
#
# Fejeren findes altså fordi beregningen ikke var nok. Indbakken er mindre
# udsat, fordi visningen læser alle åbne poster hver tur — men «hver tur»
# gælder kun for en bruger hvis session faktisk kører. En post der tilhører en
# inaktiv bruger rammes af samme kurve, bare langsommere.
#
# Beregningen er det der DRÆBER posten (med det samme, uden at noget job skal
# køre). Fejeren er det der sikrer at en post ingen læser også får sin
# terminale tilstand SKREVET, så Opgave 7 kan tælle den.

#: ISO-grænsen SKAL dannes med `strftime('%Y-%m-%dT%H:%M:%S', …)`, ikke med
#: `datetime('now', …)`. `created_at` er ISO **med `T`**, og `T` sorterer EFTER
#: mellemrum — så `datetime('now')` som grænse slipper hele dagen igennem.
#: Den fælde er ramt FIRE gange i dette hus.
_ISO_NU = "strftime('%Y-%m-%dT%H:%M:%S','now')"


def er_udloebet(post: dict[str, Any], nu: datetime | None = None) -> bool:
    """Er posten udløbet? Beregnet, så den dør uden at et job skal køre.

    Fald-retningen er **BEVAR**, ikke udløb:

    * tom `expires_at` ⇒ udløber ALDRIG. Et bevidst valg: en post uden frist
      skal kunne stå til nogen afgør den.
    * uparsabel tekst ⇒ posten bevares, og det logges på WARNING. Godkendelsernes
      egen præcedens gør det modsatte (`except ValueError: expires_at = now`,
      altså «udløbet NU»), og det er forkert her: en skrivefejl i et
      tidsstempel må ikke kunne lukke en forpligtelse.
    * naivt tidsstempel ⇒ læses som UTC, samme som `db_governance` gør. Ellers
      sammenlignes æbler og pærer.
    * `expires_at == nu` ⇒ **udløbet**. Én side valgt og pinnet.
    """
    s = str(post.get("expires_at") or "").strip()
    if not s:
        return False
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("db_inbox: uparsabelt expires_at %r paa %r — posten BEVARES",
                       s[:40], str(post.get("kilde_id") or "")[:40])
        return False
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d <= (nu or datetime.now(UTC))


def saet_udloeb(*, bruger_id: str, kilde_id: str, expires_at: str) -> dict[str, Any]:
    """Sæt (eller fjern, med tom streng) en posts frist."""
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    if not bruger_id or not kilde_id:
        return {"status": "fejl", "error": "bruger_id og kilde_id kraeves"}
    with connect() as conn:
        _ensure_skema(conn)
        cur = conn.execute(
            "UPDATE inbox_items SET expires_at = ? WHERE bruger_id = ? AND kilde_id = ?",
            (str(expires_at or ""), bruger_id, kilde_id))
    if cur.rowcount == 0:
        return {"status": "ukendt", "id": kilde_id}
    return {"status": "ok", "id": kilde_id, "expires_at": str(expires_at or "")}


def fej_udloebne(*, maks: int = 500) -> dict[str, Any]:
    """Skriv den terminale tilstand for åbne poster hvis frist er passeret.

    Fejeren gør ikke posten død — beregningen har allerede gjort det. Den
    sikrer at en post INGEN slår op igen også får sin tilstand skrevet, så
    Opgave 7 kan skelne `udloebet` fra `released` uden årsag.

    Kørt to gange tæller den ikke samme post to gange: `status = 'aaben'` i
    WHERE gør skrivningen idempotent.
    """
    with connect() as conn:
        _ensure_skema(conn)
        # ── Bagudfyldning af fristen (målt 5/10-2026) ───────────────────────
        #
        # Produsenten i `opret_eller_hent` sætter kun en frist ved INDSÆTTELSE.
        # En post der blev oprettet FØR reglen fandtes — eller af en kodevej
        # der ikke går gennem den — stod derfor med tom frist, og tom betyder
        # «udløber ALDRIG». Målt i drift: `wake-467df5d319` (oprettet 04:57,
        # før fixet kl. 06:34) GATEDE med tom frist. Det er præcis den
        # permanente lås Opgave 8 findes for at forhindre: «en post må ikke
        # kunne gate i det uendelige ved at ingen rører den».
        #
        # Reglen er den SAMME som produsentens — kun en post der kan nægte en
        # mutation får en frist — og den lægges her fordi fejeren er den
        # eneste vej der ser ALLE åbne poster, uanset hvem der skrev dem.
        # `kraever_handling = 1` er den præcise betingelse: en informerende
        # post uden frist er harmløs.
        frist = (datetime.now(UTC) + timedelta(days=_FRIST_DAGE)).isoformat()
        bagud = conn.execute(
            "UPDATE inbox_items SET expires_at = ? "
            "WHERE status = ? AND kraever_handling = 1 AND expires_at = ''",
            (frist, STATUS_AABEN))
        bagudfyldt = bagud.rowcount
        cur = conn.execute(
            # `expires_at != ''` er ikke pynt: tom streng sorterer FØR enhver
            # ISO-dato, så uden den ville HVER post uden frist blive fejet.
            f"UPDATE inbox_items SET status = ?, kraever_handling = 0, "
            f"afgjort_at = ?, afgjort_grund = ? "
            f"WHERE status = ? AND expires_at != '' AND expires_at <= {_ISO_NU} "
            f"AND id IN (SELECT id FROM inbox_items WHERE status = ? "
            f"           AND expires_at != '' AND expires_at <= {_ISO_NU} LIMIT ?)",
            (STATUS_UDLOEBET, _nu(), "udloebet", STATUS_AABEN, STATUS_AABEN,
             max(int(maks), 1)))
        n = cur.rowcount
    if bagudfyldt:
        logger.info("db_inbox: gav %d gatende post(er) en frist (bagudfyldning)",
                    bagudfyldt)
    if n:
        logger.info("db_inbox: fejede %d udloebet post(er)", n)
    return {"status": "ok", "fejet": int(n or 0), "bagudfyldt": int(bagudfyldt or 0)}


# ── Opgave 9: kildens terminale tilstand ────────────────────────────────────
#
# BESLUTNINGEN (trin 1): mulighed **(b)** — en indholdsregel nedgraderer posten
# når kilden er terminal. Ikke (a), fordi kilderne er mange og nogle af dem
# (supervisor-jobs, scout-agenter) ikke har noget sted at skrive til. Ikke (c),
# fordi det ER den blokerede ligevægt: intet lukker et job der er exit 0 af sig
# selv, og så står posten og gater indtil nogen rører den i hånden.
#
# **Nedgradering, ikke sletning.** Posten bliver `afsluttet_af_kilde` og kan
# stadig ses og findes. Beviset slettes ikke.


def meld_kilde_faerdig(
    *, bruger_id: str, kilde_id: str, exit_kode: int | None,
) -> dict[str, Any]:
    """Kilden melder sig færdig. Nedgradér posten — hvis den gik GODT.

    Kanterne, hver for sig, fordi en nedgradering der rammer forkert er værre
    end ingen:

    * `exit_kode != 0` ⇒ posten lukkes **IKKE**. En fejlet opgave er netop en
      der kræver handling, og det er hele grunden til at panelet findes.
    * `exit_kode is None` ⇒ kilden er forsvundet, ikke færdig. Posten står
      åben; visningen giver den `status_ukendt`, som er sin egen klasse.
    * meldt to gange ⇒ idempotent, og tælleren i Opgave 7 må ikke tælle
      dobbelt. `status = 'aaben'` i WHERE sørger for begge.
    * allerede `done` af mig ⇒ kildens melding genåbner den ikke.
    * mens den gater ⇒ `kraever_handling = 0` i SAMME `UPDATE`, så nægtelsen
      forsvinder i samme greb. Ellers blokerer en død post.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    if not bruger_id or not kilde_id:
        return {"status": "fejl", "error": "bruger_id og kilde_id kraeves"}
    if exit_kode is None:
        return {"status": "ikke_afgjort", "id": kilde_id, "grund": "kilden er forsvundet"}
    if int(exit_kode) != 0:
        return {"status": "ikke_afgjort", "id": kilde_id,
                "grund": f"exit {int(exit_kode)} — en fejlet opgave kraever handling"}
    with connect() as conn:
        _ensure_skema(conn)
        cur = conn.execute(
            "UPDATE inbox_items SET status = ?, kraever_handling = 0, "
            "afgjort_at = ?, afgjort_grund = ? "
            "WHERE bruger_id = ? AND kilde_id = ? AND status = ?",
            (STATUS_AFSLUTTET_AF_KILDE, _nu(), "kilden meldte exit 0",
             bruger_id, kilde_id, STATUS_AABEN))
        if cur.rowcount == 0:
            r = conn.execute(
                "SELECT status FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
                (bruger_id, kilde_id)).fetchone()
            if r is None:
                return {"status": "ukendt", "id": kilde_id}
            return {"status": "allerede", "id": kilde_id, "havde": str(r["status"])}
    return {"status": "ok", "id": kilde_id, "ny_status": STATUS_AFSLUTTET_AF_KILDE}


# ── Opgave 11: retention ────────────────────────────────────────────────────
#
# BESLUTNINGEN (trin 1): retention er en **LÆSE-REGEL**, ikke en sletning.
#
# En lukket post ældre end vinduet forsvinder fra den aktive visning, men kan
# stadig FINDES — «væk fra forsiden» er ikke «slettet». Sletning af et bevis
# kræver sin egen begrundelse, og den har vi ikke: `inbox_items` vokser med en
# række per kilde per bruger, altså i størrelsesordenen hundreder, ikke de 1.896
# kandidater der druknede den anden flade.
#
# Tredive dage: længe nok til at man kan se tilbage på en uge der gik skævt,
# kort nok til at den aktive visning ikke bærer en måneds historie.

_RETENTION_DAGE: Final[int] = 30


def liste_aktiv(*, bruger_id: str, maks: int = 500) -> list[dict[str, Any]]:
    """Den AKTIVE visning: åbne poster plus nyligt lukkede.

    Kanterne:

    * en post der stadig **gater** ⇒ altid med, uanset alder. Den er åben, og
      åbne poster har ingen aldersgrænse her.
    * en post **uden** lukke-tidspunkt ⇒ bevares. Mangler tidsstemplet, må den
      ikke falde ud af vinduet ved et uheld.
    * vinduets grænse ⇒ `afgjort_at == graense` er **inde**. Én side valgt.
    * `strftime`, ikke `datetime('now', …)`: tidsstemplerne er ISO med `T`, og
      `T` sorterer efter mellemrum, så den anden form slipper hele dagen
      igennem. Fjerde gang den fælde rammes i dette hus.
    """
    bruger_id = str(bruger_id or "").strip()
    if not bruger_id:
        return []
    with connect() as conn:
        _ensure_skema(conn)
        rows = conn.execute(
            f"SELECT * FROM inbox_items WHERE bruger_id = ? AND ("
            f"  status = ?"
            f"  OR afgjort_at = ''"
            f"  OR afgjort_at >= strftime('%Y-%m-%dT%H:%M:%S','now','-{_RETENTION_DAGE} days')"
            f") ORDER BY id ASC LIMIT ?",
            (bruger_id, STATUS_AABEN, max(int(maks), 1))).fetchall()
    return [_post_fra_raekke(r) for r in rows]
