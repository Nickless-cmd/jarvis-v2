"""Ugentlig gennemgang: hvilke modeller lever, og hvad kan de?

Bjørn 7/9-2026: «cheap lane må aldrig dø». Den var ved at gøre det i det
stille — syv udbydere kørte på 0,0 % success, over 7.000 spildte kald på syv
døgn, og ingen sagde fra. Modeller pensioneres, gratis-niveauer forsvinder,
værter flytter.

Fejemaskinen gør tre ting for hver udbyder i cheap lane:

  1. henter udbyderens EGEN modelliste, hvis den har en
  2. **prøver** hver kandidat med `model_probe` — for LISTET ER IKKE KALDBAR
     (LLM7 lister 46 og 3 svarer; NVIDIA lister 81 og én er brugbar)
  3. skriver resultatet i provider-registret: slår døde fra med en grund, og
     gemmer karakteren så modelvalg kan bygge på færdighed frem for et navn
     nogen skrev ind engang

Den skriver DIREKTE. Et forslag der venter på godkendelse er en pulje der
bliver ved med at ringe til døde numre indtil nogen har tid.

Hvad den IKKE gør: den slår aldrig den sidste fungerende model fra hos en
udbyder uden at sige det, og den rører ikke modeller den ikke kunne prøve.
En travl dag hos en udbyder må ikke koste ham hans pulje.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Hvor mange NYE modeller vi prøver pr. udbyder pr. kørsel. OpenRouter lister
# 430 — at prøve dem alle ville tage timer og brænde kvote hos en udbyder der
# ikke har gjort noget galt. De registrerede prøves ALTID; det her er kun
# hvor grådigt vi leder efter nye.
MAKS_NYE_PR_UDBYDER = 6

# Under denne karakter regnes en model ikke for brugbar til agent-arbejde.
# 40 = «svarer og kan skrive kode, men kalder ikke værktøjer» — den er fin i
# cheap lane til tekst, men ubrugelig for en agent. Derfor to tærskler.
MIN_SCORE_LEVENDE = 25      # under dette: slå fra
MIN_SCORE_AGENT = 60        # under dette: brugbar, men ikke til agent-arbejde


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _foretræk_gratis(navne: list[str]) -> list[str]:
    """`:free` først. En gratis model der virker er mere værd for cheap lane
    end en betalt der virker lidt bedre."""
    return sorted(navne, key=lambda n: (0 if ":free" in n else 1, n))


def kandidater_for(
    provider: str,
    *,
    registrerede: list[str],
    fra_api: list[str],
    statiske: list[str],
    maks_nye: int = MAKS_NYE_PR_UDBYDER,
) -> list[str]:
    """Hvad skal prøves hos denne udbyder?

    De registrerede altid — de er dem puljen faktisk bruger, og det er dem der
    kan være døde uden at nogen har opdaget det. Derefter et begrænset kig
    efter nye, med gratis først.
    """
    ud = list(dict.fromkeys(str(m).strip() for m in registrerede if str(m).strip()))
    kendte = set(ud)
    # Kataloget vejer tungere end API-listen: static_models er noget nogen har
    # verificeret, /v1/models er blot hvad udbyderen reklamerer med.
    nye = [str(m).strip() for m in (statiske or []) if str(m).strip() and str(m).strip() not in kendte]
    nye += [m for m in _foretræk_gratis(
        [str(x).strip() for x in (fra_api or []) if str(x).strip()]
    ) if m not in kendte and m not in nye]
    ud.extend(list(dict.fromkeys(nye))[:max(0, int(maks_nye))])
    return ud


def beslut(resultat: dict[str, Any]) -> tuple[bool | None, str]:
    """(skal_være_aktiv, grund). Ren funktion — al politik ét sted.

    `None` betyder RØR IKKE: vi kunne ikke afgøre noget, og tilstanden skal
    stå som den er.
    """
    from core.services.model_probe import _er_forbigaaende
    score = int(resultat.get("score") or 0)
    fejl = str(resultat.get("error") or "")
    sprunget = list(resultat.get("sprunget") or [])
    if not resultat.get("callable"):
        # Et rate limit er ikke en dom. Første kørsel slog
        # nvidia-nim/minimaxai/minimax-m3 fra på et 429 «Too Many Requests» —
        # en model jeg havde verificeret minutter forinden. Jeg beskyttede
        # delprøverne mod forbigående fejl og glemte den første. Uden det her
        # ville hver ugentlig fejning slå tilfældige raske modeller fra.
        if _er_forbigaaende(fejl):
            return None, f"kunne ikke prøves nu: {fejl[:100]}"
        return False, f"svarer ikke: {fejl[:120]}" or "svarer ikke"
    if score < MIN_SCORE_LEVENDE:
        return False, f"score {score} — under grænsen for brugbar ({fejl[:80]})".strip()
    if sprunget and score >= MIN_SCORE_LEVENDE:
        return True, f"score {score} (delprøver sprunget: {', '.join(sprunget)})"
    return True, f"score {score}"


def egnet_til_agentarbejde(resultat: dict[str, Any]) -> bool:
    """Explore og andre opgave-agenter må kun få modeller der kan bruge et
    værktøjsresultat. En der kalder og ignorerer svaret ligner en der
    arbejder — det var præcis 7/9-fejlen."""
    return bool(resultat.get("follows")) and int(resultat.get("score") or 0) >= MIN_SCORE_AGENT


def sweep_provider(
    provider: str,
    *,
    hent_modeller: Any = None,
    proev: Any = None,
    skriv: Any = None,
    maks_nye: int = MAKS_NYE_PR_UDBYDER,
) -> dict[str, Any]:
    """Gennemgå én udbyder. Returnerer en ændringsrapport.

    De tre kroge injiceres i tests; ellers bruges runtime'ens egne. Rapporten
    er det eneste kalderen behøver — den siger hvad der SKETE, ikke hvad der
    blev overvejet.
    """
    from core.services.model_probe import probe_model
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS

    if proev is None:
        proev = probe_model
    if hent_modeller is None:
        hent_modeller = _hent_modeller_fra_api
    if skriv is None:
        skriv = _skriv_registret

    cfg = CHEAP_PROVIDER_DEFAULTS.get(provider) or {}
    base_url = str(cfg.get("base_url") or "")
    fra_registret, profil = _registrerede_modeller(provider)
    # «Kendt» = alt puljen allerede tilbyder, altså registret PLUS kataloget.
    # Uden static_models ville en katalog-model blive meldt som NY hver eneste
    # uge — første kørsel meldte gemma4:31b-cloud som ny, selvom den stod i
    # puljen. En push man lærer at ignorere er værre end ingen push.
    statiske = [str(m).strip() for m in (cfg.get("static_models") or []) if str(m).strip()]
    registrerede = list(dict.fromkeys(fra_registret + statiske))
    fra_api = hent_modeller(provider, profil) if cfg.get("models_endpoint") else []

    rapport: dict[str, Any] = {
        "provider": provider, "tidspunkt": _now(),
        "proevet": 0, "slaaet_fra": [], "genoplivet": [], "nye": [],
        "agent_egnede": [], "uaendret": 0, "fejl": "",
    }
    kand = kandidater_for(provider, registrerede=registrerede, fra_api=fra_api,
                          statiske=[], maks_nye=maks_nye)
    if not kand:
        return rapport

    resultater: dict[str, dict] = {}
    for m in kand:
        r = proev(provider=provider, model=m, auth_profile=profil or "default", base_url=base_url)
        resultater[m] = r
        rapport["proevet"] += 1

    # VÆRN: slå aldrig ALT fra hos en udbyder på én kørsel. Rammer vi en travl
    # dag eller en netværkshikke, ville vi tømme puljen for en udbyder der er
    # rask i morgen — og cheap lane må aldrig dø.
    levende = [m for m, r in resultater.items() if beslut(r)[0] is not False]
    if registrerede and not levende:
        rapport["fejl"] = ("alle kandidater dumpede — rører intet. "
                           "Enten er udbyderen nede, eller vi er.")
        return rapport

    for m, r in resultater.items():
        aktiv, grund = beslut(r)
        if aktiv is None:
            # Kunne ikke afgøres — lad tilstanden stå.
            rapport["uaendret"] += 1
            rapport.setdefault("ikke_afgjort", []).append({"model": m, "grund": grund})
            continue
        var_registreret = m in registrerede
        ændret = skriv(provider=provider, model=m, aktiv=aktiv, grund=grund,
                       score=int(r.get("score") or 0), detalje=r, profil=profil or "default")
        if not var_registreret and aktiv:
            rapport["nye"].append({"model": m, "score": r.get("score")})
        elif ændret and not aktiv:
            rapport["slaaet_fra"].append({"model": m, "grund": grund})
        elif ændret and aktiv:
            rapport["genoplivet"].append({"model": m, "score": r.get("score")})
        else:
            rapport["uaendret"] += 1
        if egnet_til_agentarbejde(r):
            rapport["agent_egnede"].append(m)
    return rapport


def _registrerede_modeller(provider: str) -> tuple[list[str], str]:
    try:
        from core.runtime.provider_router import load_provider_router_registry
        reg = load_provider_router_registry() or {}
    except Exception:
        return [], "default"
    profil = ""
    for p in reg.get("providers") or []:
        if str(p.get("provider") or "") == provider:
            profil = str(p.get("auth_profile") or "")
            break
    ms = [str(m.get("model") or "") for m in (reg.get("models") or [])
          if str(m.get("provider") or "") == provider and str(m.get("model") or "")]
    return list(dict.fromkeys(ms)), profil or "default"


def _hent_modeller_fra_api(provider: str, profil: str) -> list[str]:
    try:
        from core.services.cheap_provider_runtime_adapters import list_provider_models
        d = list_provider_models(provider=provider, auth_profile=profil or "default") or {}
        ms = d.get("models") or []
        return [m if isinstance(m, str) else str(m.get("id") or m.get("model") or "") for m in ms]
    except Exception as exc:
        logger.debug("sweep: kunne ikke hente modeller for %s: %s", provider, exc)
        return []


def _skriv_registret(*, provider: str, model: str, aktiv: bool, grund: str,
                     score: int, detalje: dict, profil: str) -> bool:
    """Skriv én models tilstand. Returnerer True hvis noget ÆNDREDE sig.

    Karakteren gemmes med, så modelvalg senere kan bygge på færdighed frem for
    et navn nogen skrev ind engang.
    """
    import json
    try:
        from core.runtime.config import PROVIDER_ROUTER_FILE as F
        from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
        d = json.loads(F.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("sweep: kunne ikke læse registret: %s", exc)
        return False
    poster = d.get("models") or []
    fundet = None
    for m in poster:
        if str(m.get("provider") or "") == provider and str(m.get("model") or "") == model:
            fundet = m
            break
    ændret = False
    if fundet is None:
        if not aktiv:
            # BLIND VINKEL rettet 7/9-2026: «tilføj ikke en model der dumpede»
            # lød fornuftigt, men gjorde at en model der KUN lever i kataloget
            # aldrig kunne slås fra. Cerebras' modeller står i static_models og
            # ikke i registret — sonden dømte dem 0 («Payment required»), og
            # dommen blev tavst kasseret, så puljen blev ved med at vælge dem.
            #
            # En katalog-model skal derfor skrives IND som frakoblet. Det er
            # netop dem der ellers bliver ved i det uendelige. En tilfældig ny
            # model fra /v1/models der dumper, tilføjes stadig ikke — den har
            # ingen plads at miste.
            statiske = list((CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("static_models") or [])
            if model not in statiske:
                return False
        base = str((CHEAP_PROVIDER_DEFAULTS.get(provider) or {}).get("base_url") or "")
        try:
            from core.runtime.provider_router import configure_provider_router_entry as reg
            reg(provider=provider, model=model, auth_mode="api-key", auth_profile=profil,
                base_url=base, api_key="", lane="cheap", set_visible=False)
        except Exception as exc:
            logger.warning("sweep: kunne ikke tilføje %s/%s: %s", provider, model, exc)
            return False
        d = json.loads(F.read_text(encoding="utf-8"))
        poster = d.get("models") or []
        for m in poster:
            if str(m.get("provider") or "") == provider and str(m.get("model") or "") == model:
                fundet = m
                break
        ændret = True
    if fundet is None:
        return False
    if bool(fundet.get("enabled", True)) != aktiv:
        ændret = True
    fundet["enabled"] = aktiv
    fundet["probe_score"] = int(score)
    fundet["probe_at"] = _now()
    fundet["probe_detail"] = {k: detalje.get(k) for k in
                              ("callable", "tools", "follows", "code", "latency_ms", "sprunget")}
    if aktiv:
        fundet.pop("disabled_reason", None)
    else:
        fundet["disabled_reason"] = grund[:200]
    try:
        F.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        logger.warning("sweep: kunne ikke skrive registret: %s", exc)
        return False
    return ændret


def sammendrag(rapporter: list[dict[str, Any]]) -> str:
    """Én besked til mobilen. Kun ÆNDRINGER — en push der hver uge siger
    «alt er som før» bliver ignoreret indtil den uge hvor den ikke er det."""
    fra, ny, genopl, fejl = [], [], [], []
    for r in rapporter:
        p = r.get("provider")
        for x in r.get("slaaet_fra") or []:
            fra.append(f"{p}/{x['model']}")
        for x in r.get("nye") or []:
            ny.append(f"{p}/{x['model']} ({x.get('score')})")
        for x in r.get("genoplivet") or []:
            genopl.append(f"{p}/{x['model']}")
        if r.get("fejl"):
            fejl.append(f"{p}: {r['fejl']}")
    if not (fra or ny or genopl or fejl):
        return ""
    dele = []
    if fra:
        dele.append(f"Slået fra ({len(fra)}): " + ", ".join(fra[:6]))
    if ny:
        dele.append(f"Nye ({len(ny)}): " + ", ".join(ny[:6]))
    if genopl:
        dele.append(f"Tilbage ({len(genopl)}): " + ", ".join(genopl[:6]))
    if fejl:
        dele.append("Rørte ikke: " + "; ".join(fejl[:3]))
    return " · ".join(dele)[:600]


def underret_ejeren(besked: str, *, send: Any = None) -> bool:
    """Kun ejeren. Cheap-lane-helbred er driftsdata om HANS konti og penge —
    det hører ikke til hos andre brugere, og der er ingen anden modtager der
    kan gøre noget ved det."""
    if not str(besked or "").strip():
        return False
    try:
        if send is None:
            from core.services.push_dispatcher import send_companion_push as send
        from core.identity.users import get_owner
        ejer = get_owner()
        uid = str(getattr(ejer, "discord_id", "") or "") if ejer else ""
        if not uid:
            logger.warning("sweep: ingen ejer at underrette")
            return False
        return bool(send(uid, besked, "Cheap lane"))
    except Exception as exc:
        logger.warning("sweep: kunne ikke underrette ejeren: %s", exc)
        return False


def sweep_alle(*, providers: list[str] | None = None, underret: bool = True,
               proev: Any = None, skriv: Any = None) -> dict[str, Any]:
    """Gennemgå hele cheap lane. Returnerer rapporter + den sendte besked."""
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    navne = providers if providers is not None else sorted(CHEAP_PROVIDER_DEFAULTS)
    rapporter: list[dict[str, Any]] = []
    for p in navne:
        try:
            rapporter.append(sweep_provider(p, proev=proev, skriv=skriv))
        except Exception as exc:
            logger.warning("sweep: %s væltede: %s", p, exc)
            rapporter.append({"provider": p, "fejl": f"{type(exc).__name__}: {exc}",
                              "proevet": 0, "slaaet_fra": [], "nye": [],
                              "genoplivet": [], "agent_egnede": [], "uaendret": 0})
    besked = sammendrag(rapporter)
    sendt = underret_ejeren(besked) if (underret and besked) else False
    return {"rapporter": rapporter, "besked": besked, "underrettet": sendt}
