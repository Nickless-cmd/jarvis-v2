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
from typing import Any

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
          session_id: str | None = None,
          data: dict[str, Any] | None = None) -> None:
    _lager.opret(user_id=user_id, slags=slags, kilde=kilde, titel=titel,
                 tekst=tekst, ref=ref, session_id=session_id, data=data)
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


def system(slags: str, titel: str, tekst: str = "", *, ref: str | None = None,
           data: dict[str, Any] | None = None) -> None:
    uid = _owner_id()
    if not uid:
        return
    _foed(user_id=uid, slags=slags, kilde="egen", titel=titel, tekst=tekst,
          ref=ref, data=data)


def _forslag_er_foraeldet(forslag: dict[str, Any]) -> bool:
    """Er forslagets anker stadig i koden? (Bjørn 2/11-2026)

    MAALT 2/11-2026: 57 forslag laa `pending`, og 0 af 14 source-edit
    matchede deres `base_fingerprint`. Fire af dem ville slette 69-152 linjer
    — inklusive `_MAX_ATTEMPTS`-loftet i initiative_queue.py, altsaa rulle
    fixet fra 1/11 tilbage. Uden denne markering ser en raadden aendring ud
    som en godkendelsesklar forbedring, og den kan godkendes blindt fra en
    toast. Det er praecis den fejlform Bjørn kalder teater.

    Kun source-edit baerer et fingerprint. Andre kinds (instrument_fix,
    git-commit, memory-rewrite) har intet anker at maale mod og regnes
    derfor ikke som foraeldede her — de skal ikke skjules, blot ikke
    paastaa en friskhed de ikke har.
    """
    if str(forslag.get("kind") or "") != "source-edit":
        return False
    payload = forslag.get("payload") or {}
    if not isinstance(payload, dict):
        return False
    base = str(payload.get("base_fingerprint") or "")
    sti = str(payload.get("target_path") or "")
    if not base or not sti:
        return False
    try:
        import hashlib
        from pathlib import Path
        # SHA1 paa TEKST, ikke SHA256 paa bytes (rettet 2/11-2026):
        # `autonomy_proposal_queue._fp` skriver `sha1(text)[:16]` ind i
        # `base_fingerprint`. Brugte jeg sha256 her, kunne de to ALDRIG
        # matche — og saa blev HVERT source-edit-forslag markeret foraeldet,
        # ogsaa de gyldige. Maalt i en koerende browser: to friske forslag
        # med korrekt fingerprint blev begge skjult af toasten, fordi
        # `!p.foraeldet` filtrerede dem fra. En detektion der altid siger
        # «foraeldet» er ikke forsigtig, den er doed.
        raa = Path(sti).read_text(encoding="utf-8", errors="replace")
        return hashlib.sha1(raa.encode("utf-8"), usedforsecurity=False).hexdigest()[:16] != base
    except Exception:
        # Kan filen ikke laeses, er ankeret ikke bevist frisk. Vi siger
        # foraeldet frem for at paastaa det modsatte — en forkert
        # «godkendelsesklar» er den dyre fejl.
        return True


def paa_forslag(forslag: dict[str, Any], *, user_id: str) -> None:
    """Én raekke pr. ventende forslag. `ref` = proposal_id, saa `opret()`
    afdublerer af sig selv og en gen-koersel ikke giver dobbelte raekker."""
    pid = str(forslag.get("proposal_id") or "")
    if not pid:
        return
    kind = str(forslag.get("kind") or "forslag")
    titel_tekst = str(forslag.get("title") or "").strip() or "(uden titel)"
    foraeldet = _forslag_er_foraeldet(forslag)
    payload = forslag.get("payload") or {}
    sti = str(payload.get("target_path") or "") if isinstance(payload, dict) else ""
    tekst = f"{kind}"
    if sti:
        tekst += f" · {sti.rsplit('/', 1)[-1]}"
    tekst += " · FORÆLDET — ankeret findes ikke i koden længere" if foraeldet else " · afventer afgørelse"
    _foed(user_id=user_id, slags="proposal", kilde="proposal", ref=pid,
          titel=titel_tekst, tekst=tekst,
          data={"proposal_id": pid, "proposal_kind": kind,
                "target_path": sti, "foraeldet": foraeldet})


def afstem_forslag(user_id: str) -> int:
    """Laeg raekker for ALLE ventende forslag der mangler. Returnerer antal
    nye/genaabnede.

    Samme begrundelse som `afstem_godkendelser`: afstemning frem for en krog
    ved foedslen. Forslag bliver til i mindst fire forskellige daemons
    (instrument_fix, source-edit, git-commit, memory-rewrite), og en krog pr.
    kilde ville blive glemt i mindst én af dem — det er maalt: 57 forslag laa
    usynlige, det aeldste fra 22/10.

    `opret()` afdublerer paa (slags, ref), saa den er idempotent.
    """
    try:
        from core.services.autonomy_proposal_queue import list_pending_proposals
        forslag_liste = list_pending_proposals(limit=200)
    except Exception:
        _log.warning("kunne ikke liste ventende forslag", exc_info=True)
        return 0
    if not forslag_liste:
        return 0
    aabne_refs = {str(r["ref"]) for r in _lager.aabne(user_id, er_owner=False)
                  if str(r["slags"]) == "proposal"}
    talt = 0
    for forslag in forslag_liste:
        pid = str(forslag.get("proposal_id") or "")
        if not pid or pid in aabne_refs:
            continue
        if _lager.genaabn("proposal", pid):
            talt += 1
            continue
        paa_forslag(forslag, user_id=user_id)
        talt += 1
    return talt


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
