# core/services/notifikations_emittere.py
"""Hvor notifikationer foedes (spec 2026-09-21).

Ét sted der baade laegger raekken og — hvis brugerens valg siger det — sender
pushet. Uden det ville hver kilde skulle huske begge dele, og den ene ville
blive glemt.

Feeden er den PAALIDELIGE del; telefonen er den upaalidelige. Et push der
fejler maa aldrig tage raekken med sig.
"""
from __future__ import annotations

import logging

from core.services import notifikationer as _lager
from core.services import notifikations_valg as _valg

_log = logging.getLogger(__name__)


def _owner_id() -> str | None:
    """Ejeren. Systemraekker hoerer til ham — de handler om maskinen.

    Slog FOER kun op i `users`-tabellen. Paa CT105 har den tabel ingen
    ejer-raekke (14 raekker, alle `member`) — Bjoern staar i `users.json`.
    Opslaget gav derfor None, `system()` returnerede uden at skrive, og
    resultatet var maalbart: NUL release-notifikationer nogensinde, fra
    0.6.43 til 0.6.94. `owner_user_id` spoerger begge lagre.
    """
    try:
        from core.identity.owner_resolver import owner_user_id
        uid = owner_user_id()
        if uid:
            return uid
        _log.warning("ingen ejer fundet i hverken users-tabellen eller users.json "
                     "— systemnotifikationen bliver ikke leveret")
        return None
    except Exception:
        _log.warning("kunne ikke finde owner til en systemnotifikation", exc_info=True)
        return None


def _maaske_push(user_id: str, slags: str, titel: str, tekst: str,
                 *, session_id: str | None = None) -> None:
    kanal = _valg.kanal_for(user_id, slags)
    if kanal == "ingen":
        return
    try:
        from core.services import notification_router
        # K1 (2026-09-22): payloaden brugte de DANSKE feltnavne (titel/tekst),
        # men routeren, desktop-koeen og FCM laeser title/preview/body —
        # samtlige OVRIGE elleve kaldere af route_proactive_notification()
        # bruger de navne. `fcm_gateway._build_message` tilfoejer kun en
        # synlig 'notification'-blok naar BAADE title OG body findes, saa
        # push-halvdelen var reelt doed: ingen synlig push paa telefonen,
        # "Jarvis" + tom krop paa desktoppen. `tekst or titel` sikrer en krop
        # ogsaa naar kalderen (fx `paa_godkendelse`) ikke selv satte tekst.
        # feed=False (routeren-foeder, 2026-09-22): `_foed()` har LIGE lagt
        # raekken faa linjer over dette kald — routeren skriver nu ellers selv
        # en raekke for enhver slags den ikke faar besked om, og uden dette
        # flag ville approval/run_failed/run_done/release/incident/quota alle
        # dubleres (dobbelt-fødsel).
        notification_router.route_proactive_notification(
            user_id, slags,
            {"title": titel, "preview": tekst or titel, "body": tekst or titel,
             "kind": slags, "session_id": session_id or ""},
            importance="high" if slags in ("approval", "question") else "normal",
            feed=False)
    except Exception:
        # Raekken staar allerede i feeden. Et brudt push maa ikke tage den med.
        _log.warning("push for %s til %s fejlede", slags, user_id, exc_info=True)


def _foed(*, user_id: str, slags: str, kilde: str, titel: str,
          tekst: str = "", ref: str | None = None,
          session_id: str | None = None) -> None:
    _lager.opret(user_id=user_id, slags=slags, kilde=kilde, titel=titel,
                 tekst=tekst, ref=ref, session_id=session_id)
    _maaske_push(user_id, slags, titel, tekst, session_id=session_id)


def paa_godkendelse(approval_id: str, *, user_id: str, session_id: str,
                    vaerktoej: str) -> None:
    # K1: uden `tekst` var pushets krop tom — `_maaske_push`s `tekst or titel`
    # daekker det generisk, men en ægte krop giver en bedre push end en
    # gentagelse af titlen.
    _foed(user_id=user_id, slags="approval", kilde="approval", ref=approval_id,
          session_id=session_id, titel=f"Vil du tillade {vaerktoej}?",
          tekst="Åbn feeden for at svare.")


def paa_koersel_fejlet(run_id: str, *, user_id: str, session_id: str,
                       titel: str) -> None:
    _foed(user_id=user_id, slags="run_failed", kilde="run", ref=run_id,
          session_id=session_id, titel=f"Noget gik galt i «{titel}»")


def paa_koersel_faerdig(run_id: str, *, user_id: str, session_id: str,
                        titel: str) -> None:
    _foed(user_id=user_id, slags="run_done", kilde="run", ref=run_id,
          session_id=session_id, titel=f"Svar klar i «{titel}»")


def fra_jarvis(user_id: str, slags: str, titel: str, tekst: str = "") -> None:
    """Det Jarvis selv sender. Har ingen ejer — raekken ER sandheden."""
    _foed(user_id=user_id, slags=slags, kilde="egen", titel=titel, tekst=tekst)


def system(slags: str, titel: str, tekst: str = "") -> None:
    uid = _owner_id()
    if not uid:
        return
    _foed(user_id=uid, slags=slags, kilde="egen", titel=titel, tekst=tekst)


def afstem_godkendelser(user_id: str) -> int:
    """Laeg raekker for ALLE ventende godkendelser der mangler. Returnerer
    antal nye/genaabnede.

    Afstemning frem for en krog ved foedslen: kortet foedes to steder i
    visible_runs.py, og en overset krog ville betyde en notifikation der ALDRIG
    fandtes — uden at nogen opdagede det. Den her kan ikke glemme noget, og den
    virker ogsaa for godkendelser der fandtes foer feeden blev bygget.

    `opret()` afdublerer paa (slags, ref), saa den er idempotent af sig selv.

    K2 (2026-09-22): brugte foer `pending_for_owner`, som med VILJE kun
    returnerer det NYESTE kort. Efterproevet: fire kort ventede samtidig, kun
    ét naaede feeden, stabilt. `alle_pending_for_owner` lister dem alle.

    Dedup-maengden (`aabne_refs`) slog foer op paa TVAERS af alle slags —
    filtreret her til `slags == "approval"`, saa en aaben raekke af en anden
    slags med samme `ref`-streng (usandsynligt, men umuligt at udelukke) ikke
    kunne skjule en ventende godkendelse.

    V1 (2026-09-22): findes raekken allerede, men LUKKET, betyder det at
    ejeren stadig venter paa noget feeden tidligere lukkede forkert (fx
    hydreringen der racede en async DB-skrivning, V2). `genaabn()` retter det
    — sikkert netop fordi afstemningen SPØRGER ejeren, modsat en gen-udsendt
    haendelse.
    """
    from core.services import approval_runtime
    kort_liste = approval_runtime.alle_pending_for_owner(user_id)
    if not kort_liste:
        return 0
    aabne_refs = {str(r["ref"]) for r in _lager.aabne(user_id, er_owner=False)
                  if str(r["slags"]) == "approval"}
    talt = 0
    for kort in kort_liste:
        aid = str(kort.get("approval_id") or "")
        if not aid or aid in aabne_refs:
            continue
        if _lager.genaabn("approval", aid):
            talt += 1
            continue
        paa_godkendelse(aid, user_id=user_id,
                        session_id=str(kort.get("session_id") or ""),
                        vaerktoej=str(kort.get("tool_name") or "et værktøj"))
        talt += 1
    return talt
