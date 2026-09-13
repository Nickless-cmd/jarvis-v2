"""Fortsæt automatisk når turen blev klippet af sit eget budget.

## Hvorfor

Bjørn skrev «Forsæt» 24 gange den 12.–13. september. Syv af de fjorten ture
den nat stoppede på præcis 30 runder — rundebudgettets loft — og løkken
bogførte det som `reason=completed`, nøjagtig samme ord som en tur der var
færdig. Hverken han eller systemet kunne skelne «gjort» fra «løbet tør».

Løkken bryder ud af sig selv så snart Jarvis skriver prosa uden at kalde
værktøjer. Bruger han HELE budgettet, arbejdede han altså stadig da døren
smækkede. Det er signalet: **budgettet opbrugt = turen blev klippet**, ikke
afsluttet.

## Hvorfor det er en ren funktion

Fordi det er en beslutning med mange kanter, og kanterne er det farlige — ikke
mekanikken. En fortsættelse der fyrer forkert er værre end ingen: den koster
penge, den kan løbe i ring, og den kan komme til at påstå at brugeren bad om
noget han ikke bad om.

## Kanterne, og hvorfor hver enkelt findes

- **Kæde-loft.** En tur der bliver ved med at opbruge sit budget ville ellers
  føde sig selv i det uendelige. Efter `MAKS_KAEDE` fortsættelser i træk
  stopper vi og lader mennesket bestemme.
- **Kun opbrugt budget.** Afbrudt, fejlet, annulleret, nedlukning: alt andet
  end «løb tør» betyder at nogen eller noget greb ind, og så skal vi ikke
  fortsætte af os selv.
- **Aldrig autonome runs.** De har deres egen kadence og deres eget budget.
- **Aldrig hvis brugeren selv har skrevet imens.** Han har taget over.
- **Killswitch.** Én flag-værdi slår hele mekanikken fra uden en udrulning.

## Hvorfor beskeden ikke må ligne brugerens

Auto-fortsættelsen har fejlet i dette hus før ved at **fabrikere samtykke** —
en maskinskrevet besked der stod som om Bjørn havde skrevet den. Fortsættelsen
her bærer sin egen rolle og sin egen tekst, så det altid kan ses hvem der bad
om hvad.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Hvor mange gange en tur må fortsætte sig selv i træk.
MAKS_KAEDE = 3

#: De udfald der betyder «løb tør», og ikke «nogen greb ind».
OPBRUGT = "budget-opbrugt"

#: Der stod INTET under nogen af noeglerne. Det er ikke det samme som et udfald
#: der blev bogfoert tomt.
#:
#: Maalt 13/9-2026: fire beslutninger loed «udfald=ukendt», og det ene ord
#: daekkede to helt forskellige tilstande — «turen naaede aldrig
#: bogfoerings-punktet» (et korrekt nej) og «udfaldet blev noteret under en
#: noegle vi ikke slog op» (en fejl). Med ét ord for begge kan man ikke se
#: hvilken man har, og saa bliver den anden aldrig fundet.
IKKE_BOGFOERT = "ikke-bogfoert"


@dataclass(frozen=True)
class Beslutning:
    """Svaret, med grunden. Grunden er ikke pynt — den skal i loggen, så en
    fortsættelse der udebliver kan forklares uden at læse koden."""

    fortsaet: bool
    grund: str


def beslut(
    *,
    exit_reason: str,
    slaaet_til: bool,
    autonom: bool,
    kaede_nr: int,
    bruger_skrev_imens: bool,
    maks_kaede: int = MAKS_KAEDE,
) -> Beslutning:
    """Skal denne tur fortsætte af sig selv?

    `kaede_nr` er hvor mange auto-fortsættelser der allerede er sket i træk
    (0 = dette er en tur brugeren selv startede).
    """
    if not slaaet_til:
        return Beslutning(False, "slaaet fra")
    if autonom:
        return Beslutning(False, "autonomt run")
    if str(exit_reason or "") != OPBRUGT:
        return Beslutning(False, f"udfald={exit_reason or 'ukendt'}")
    if bruger_skrev_imens:
        return Beslutning(False, "brugeren har selv skrevet videre")
    try:
        nr = int(kaede_nr)
        maks = int(maks_kaede)
    except Exception:
        return Beslutning(False, "ugyldigt kaede-tal")
    if nr >= maks:
        return Beslutning(False, f"kaede-loft naaet ({nr}/{maks})")
    return Beslutning(True, f"budget opbrugt, fortsaettelse {nr + 1}/{maks}")


def fortsaettelses_besked(kaede_nr: int, maks_kaede: int = MAKS_KAEDE) -> str:
    """Teksten Jarvis får. Den siger hvor han er, og at han skal sige til når
    han er faerdig — ellers ved han ikke at der er en graense."""
    return (
        "⏭️ Din forrige tur brugte hele sit rundebudget og blev afbrudt midt i "
        f"arbejdet — dette er automatisk fortsættelse {kaede_nr}/{maks_kaede}. "
        "Fortsæt præcis hvor du slap. Er arbejdet færdigt, så sig det kort i "
        "stedet for at kalde flere værktøjer."
    )


# ── Bogholderi ───────────────────────────────────────────────────────────────
# To små registre, med vilje i hukommelsen: begge dør med processen, og det er
# den rigtige levetid. Et kæde-tal der overlever en genstart ville kunne
# blokere en fortsættelse timer senere af en grund ingen kan se længere.

import threading

_laas = threading.Lock()
#: run_id → loekkens exit-grund. Skrives af visible_runs, laeses af den
#: detached traad naar runnet er faerdigt.
_UDFALD: dict[str, str] = {}
#: session_id → antal auto-fortsaettelser i traek.
_KAEDE: dict[str, int] = {}

#: Hvor mange udfald vi husker. Nok til et dybt arbejdsforloeb, lille nok til
#: at ordbogen ikke vokser i en proces der koerer i uger.
_UDFALD_LOFT = 200


def noter_udfald(run_id: str, exit_reason: str, session_id: str = "") -> None:
    """Noter under BEGGE noegler: runnets eget id og sessionen.

    Relayet og `start_visible_run` bruger IKKE samme run-id for samme tur.
    Maalt i produktion 13/9-2026 kl. 08:09: relayet kaldte turen
    `visible-41cd6759…` (over 4000 frames), mens `visible_runs` bogfoerte den
    som `visible-b1da4321…`. Den detached traad kender kun det YDRE id, og
    udfaldet blev noteret under det indre — saa opslaget gav altid «ukendt», og
    fortsaettelsen kunne aldrig fyre.

    Sessionen er den faelles noegle de to sider ER enige om, og single-flight
    garanterer at der hoejst er ét levende run pr. session.
    """
    rid = (run_id or "").strip()
    sid = (session_id or "").strip()
    if not rid and not sid:
        return
    with _laas:
        if rid:
            _UDFALD[rid] = str(exit_reason or "")
        if sid:
            _UDFALD["session:" + sid] = str(exit_reason or "")
        if len(_UDFALD) > _UDFALD_LOFT:
            for k in list(_UDFALD.keys())[: len(_UDFALD) - _UDFALD_LOFT]:
                _UDFALD.pop(k, None)


def hent_udfald(run_id: str, session_id: str = "") -> str:
    """Udfaldet for et run — slaa op paa run-id, og fald tilbage paa sessionen.

    Fallbacken er ikke pynt: de to sider af en tur bruger forskellige run-id'er
    (se `noter_udfald`), og sessionen er den eneste noegle de deler.
    """
    with _laas:
        rid = (run_id or "").strip()
        if rid and rid in _UDFALD:
            return _UDFALD[rid]
        sid = (session_id or "").strip()
        nøgle = "session:" + sid
        if sid and nøgle in _UDFALD:
            return _UDFALD[nøgle]
        # Ingen af noeglerne fandtes. Det er en ANDEN tilstand end et bogfoert
        # tomt udfald, og de to maa ikke smelte sammen til ét ord i loggen.
        return IKKE_BOGFOERT


def kaede_nr(session_id: str) -> int:
    with _laas:
        return int(_KAEDE.get((session_id or "").strip(), 0))


def saet_kaede(session_id: str, nr: int) -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    with _laas:
        _KAEDE[sid] = max(0, int(nr))



#: session_id → tidspunkt (monotont) for den seneste ÆGTE brugerbesked.
_SIDSTE_BRUGER: dict[str, float] = {}


def noter_brugerbesked(session_id: str) -> None:
    """Brugeren skrev selv. Bruges til to ting: nulstille kæden, og afgøre om
    han tog over MENS et run kørte."""
    import time
    sid = (session_id or "").strip()
    if not sid:
        return
    with _laas:
        _SIDSTE_BRUGER[sid] = time.monotonic()
        _KAEDE.pop(sid, None)


def bruger_skrev_efter(session_id: str, tidspunkt: float) -> bool:
    """Har brugeren skrevet efter `tidspunkt`? Så har han taget over, og en
    auto-fortsættelse ville tale i munden på ham."""
    with _laas:
        t = _SIDSTE_BRUGER.get((session_id or "").strip())
    if t is None:
        return False
    try:
        return float(t) > float(tidspunkt)
    except Exception:
        return False
