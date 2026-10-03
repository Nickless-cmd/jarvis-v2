#!/usr/bin/env python3
"""Hvor meget af Jarvis' synlige prompt er VENTENDE TILSTAND?

Opgave 0 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.
Den er FØRST med vilje: hele spec'ens begrundelse er at ventende tilstand er
spredt ud over prompten, og at en kontrolflade kan samle den og gøre halen
mindre. Det er en PÅSTAND indtil nogen måler den — og R2's punkt 2 ventede fra
13. juni på en måling der aldrig blev lavet.

Hvad den måler, og hvorfor netop det:

* **Andelen** af ventende tilstand, delt i STABILT PREFIX og DYNAMISK HALE.
  Delingen er ikke kosmetisk: en uændret sektion i prefixet får cache-hit og er
  næsten gratis, mens den samme tekst i halen betales hver tur. Et samlet
  procenttal over hele prompten kan derfor pege helt forkert.
  Grænsen er `DYNAMIC_TAIL_SENTINEL`, ikke et gæt.
* **Hvor ofte sektionerne ÆNDRER sig** mellem to ture. En sektion der er
  identisk fra tur til tur kan ligge i prefixet uden pris; en der skifter
  buster cachen fra sit eget sted og alt efter den.

Den skriver INTET. Den bygger en ægte assembly ad den samme vej runtime bruger
(`build_visible_chat_prompt_assembly` gennem `_build_visible_prompt_assembly`,
så `runtime_self_report_context` bliver sat som i drift) — ikke en
rekonstruktion, jf. `verify_visual_before_done`.

Brug (på CT105, med HANS interpreter — mine proces-starter arver en anden
profil, og «den kører hos mig» beviser intet om hans):

    /home/bs/miniconda3/envs/ai/bin/python scripts/maal_ventende_i_prompten.py
    ... --session-id <uuid>          # en ægte samtale frem for en tom
    ... --ture 3                     # byg N gange og mål hvad der skifter
    ... --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Genbrug frem for at skrive det igen: sektions-splittet og token-tællingen
# findes allerede og bruges af `measure_prompt_payload`. To kopier af samme
# regel driver fra hinanden, og så måler de to scripts forskelligt uden at
# nogen kan se hvilket der er sandt.
from scripts.measure_prompt_payload import (  # noqa: E402
    count_tokens,
    split_system_by_sections,
)

# ── Klassifikationen ────────────────────────────────────────────────────────
#
# «Ventende tilstand» er spec'ens ord: vækninger, åbne opgaver, igangværende
# jobs, hvad der vakte ham, agent-status. Altså det en indbakke kunne SAMLE.
#
# Nøglerne matches mod sektionens navn i SMÅ bogstaver, som delstreng. Navnene
# er hentet fra de faktiske `[SECTION]`-overskrifter og fra hale-blokkenes egne
# første linjer; en liste over sektionsnavne forfalder hurtigere end koden, så
# scriptet rapporterer ALTID de uklassificerede for sig (se `_ukendte`) frem for
# at stoppe dem tavst i «andet». Et aggregat læst uden at spørge hvilke rækker
# det dækkede er husets hyppigste målefejl.
_VENTENDE_MOENSTRE: tuple[str, ...] = (
    "wake",          # vækninger: ▲ WAKE, WAKEUP, wakeup_digest
    "vaekning", "vækning",
    "job",           # baggrundsjobs
    "task",          # scheduled_tasks / recurring_tasks
    "opgave",
    "agent",         # agent-status
    "approval", "godkend",
    "pending", "venter",
    "inbox", "indbakke",
    "unfinished", "ufuldendt",
    "intent",
)


def _er_ventende(navn: str) -> bool:
    n = navn.lower()
    return any(m in n for m in _VENTENDE_MOENSTRE)


def _del_ved_halen(tekst: str) -> tuple[str, str]:
    """(stabilt prefix, dynamisk hale). Halen er det EFTER sentinel'en.

    Findes sentinel'en ikke, er hele teksten prefix — og det skal siges, ikke
    gættes: en prompt uden hale er et legitimt udfald (ingen hale-blokke denne
    tur), men den må ikke forveksles med «jeg kunne ikke finde grænsen».
    """
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL

    i = tekst.find(DYNAMIC_TAIL_SENTINEL)
    if i < 0:
        return tekst, ""
    return tekst[:i], tekst[i:]


def _byg(provider: str, model: str, besked: str, session_id: str | None):
    from core.services.visible_model import _build_visible_prompt_assembly

    return _build_visible_prompt_assembly(
        provider=provider, model=model, user_message=besked, session_id=session_id,
    )


def _maal_en_del(navn: str, tekst: str) -> dict:
    """Sektionér én del (prefix eller hale) og del tokens i ventende/andet."""
    sektioner = split_system_by_sections(tekst)
    ventende: list[dict] = []
    andet: list[dict] = []
    for sek_navn, tegn, toks in sektioner:
        post = {"sektion": sek_navn, "tegn": tegn, "tokens": toks}
        (ventende if _er_ventende(sek_navn) else andet).append(post)
    v_toks = sum(int(p["tokens"]) for p in ventende)
    a_toks = sum(int(p["tokens"]) for p in andet)
    i_alt = v_toks + a_toks
    return {
        "del": navn,
        "tokens_i_alt": i_alt,
        "tokens_ventende": v_toks,
        "tokens_andet": a_toks,
        # Nævneren er DENNE dels tokens. Spec'en siger det eksplicit: «en
        # grænse på 8 % af halen kan ikke udledes af at historikken bruger
        # 3,1 % af et 1M-vindue; nævner og cacheadfærd er forskellige.»
        "andel_ventende_pct": round(100.0 * v_toks / i_alt, 1) if i_alt else 0.0,
        "ventende": sorted(ventende, key=lambda p: -int(p["tokens"])),
        "andet_top": sorted(andet, key=lambda p: -int(p["tokens"]))[:10],
        "antal_sektioner": len(sektioner),
    }


def _maal_aendring(tekster: list[str]) -> dict:
    """Hvilke sektioner ændrede sig mellem bygningerne?

    Pr. sektionsnavn: var dens INDHOLD identisk hver gang? Et navn der dukker op
    i nogle bygninger og ikke andre tælles også som ændret — en sektion der
    kommer og går flytter alt efter sig og buster cachen lige så effektivt som
    en der ændrer tekst.
    """
    if len(tekster) < 2:
        return {"maalt": False, "grund": "kun én bygning — kør med --ture 2 eller mere"}

    import re
    per_bygning: list[dict[str, str]] = []
    for t in tekster:
        d: dict[str, str] = {}
        matches = list(re.finditer(r"^(\[[A-Z][A-Z0-9 _\-/]+\])\s*$", t, re.MULTILINE))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(t)
            d[m.group(1)] = t[m.start():end]
        per_bygning.append(d)

    alle_navne = sorted({n for d in per_bygning for n in d})
    stabile: list[str] = []
    ustabile: list[dict] = []
    for navn in alle_navne:
        vaerdier = [d.get(navn) for d in per_bygning]
        if any(v is None for v in vaerdier):
            ustabile.append({"sektion": navn, "grund": "mangler i mindst én bygning",
                             "ventende": _er_ventende(navn)})
        elif len(set(vaerdier)) > 1:
            ustabile.append({"sektion": navn, "grund": "indhold skiftede",
                             "tokens": count_tokens(vaerdier[0] or ""),
                             "ventende": _er_ventende(navn)})
        else:
            stabile.append(navn)

    ust_v = [u for u in ustabile if u.get("ventende")]
    return {
        "maalt": True,
        "bygninger": len(tekster),
        "sektioner_i_alt": len(alle_navne),
        "stabile": len(stabile),
        "ustabile": len(ustabile),
        "ustabile_der_er_ventende": len(ust_v),
        # Det tal der betyder noget: hvor mange tokens ventende tilstand
        # koster FORDI den skifter. En stabil ventende-sektion i prefixet er
        # næsten gratis.
        "tokens_ustabil_ventende": sum(int(u.get("tokens") or 0) for u in ust_v),
        "ustabile_liste": ustabile[:25],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user-message", default="hej, hvordan har du det?")
    ap.add_argument("--session-id", default=None)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--ture", type=int, default=2,
                    help="byg N gange og mål hvad der skifter mellem dem")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.provider or not args.model:
        from core.services.visible_model import resolve_provider_router_target
        t = resolve_provider_router_target(lane="visible")
        args.provider = args.provider or str(t.get("provider", "") or "")
        args.model = args.model or str(t.get("model", "") or "")

    # Tur-cachen i `build_visible_chat_prompt_assembly` er nøglet på den
    # NYESTE user-besked-id, ikke på teksten. Med samme session og samme
    # besked ville bygning 2..N kunne komme fra cachen og vise «intet
    # skiftede» — en måling af cachen frem for af prompten. Derfor ryddes
    # den mellem bygningerne.
    from core.services import prompt_contract as _pc

    tekster: list[str] = []
    haler: list[str] = []
    for _ in range(max(1, args.ture)):
        try:
            _pc._ASSEMBLY_TURN_CACHE.clear()
        except Exception as exc:  # noqa: BLE001
            print(f"ADVARSEL: kunne ikke rydde tur-cachen ({exc}) — "
                  "ændrings-målingen kan være for optimistisk", file=sys.stderr)
        a = _byg(args.provider, args.model, args.user_message, args.session_id)
        tekster.append(a.text or "")
        haler.append(_del_ved_halen(a.text or "")[1])

    prefix, hale = _del_ved_halen(tekster[0])
    samlet_toks = count_tokens(tekster[0])

    # Uklassificerede sektionsnavne skal SES. Et mønster-sæt forfalder, og en
    # ny ventende-sektion der falder i «andet» ville gøre andelen for lav uden
    # at nogen kunne se det.
    _alle = [s for s, _, _ in split_system_by_sections(tekster[0])]
    rapport = {
        "dato": __import__("datetime").datetime.now(
            __import__("datetime").UTC).isoformat(timespec="seconds"),
        "provider": args.provider,
        "model": args.model,
        "session_id": args.session_id or "(tom samtale)",
        "system_tokens_i_alt": samlet_toks,
        "hale_fundet": bool(hale),
        "prefix": _maal_en_del("stabilt prefix", prefix),
        "hale": _maal_en_del("dynamisk hale", hale),
        "aendring": _maal_aendring(tekster),
        "halen_skiftede_mellem_bygninger": len(set(haler)) > 1 if len(haler) > 1 else None,
        "sektionsnavne": _alle,
    }

    if args.json:
        print(json.dumps(rapport, ensure_ascii=False, indent=2))
        return 0

    p, h, ae = rapport["prefix"], rapport["hale"], rapport["aendring"]
    print(f"VENTENDE TILSTAND I PROMPTEN — {rapport['dato']}")
    print(f"  {args.provider}/{args.model}  session={rapport['session_id']}")
    print(f"  system i alt: {samlet_toks} tokens"
          f"   hale fundet: {'ja' if rapport['hale_fundet'] else 'NEJ'}")
    for d in (p, h):
        print(f"\n  {d['del'].upper()}: {d['tokens_i_alt']} tokens "
              f"i {d['antal_sektioner']} sektioner")
        print(f"    ventende tilstand: {d['tokens_ventende']} tokens "
              f"= {d['andel_ventende_pct']} %")
        for s in d["ventende"][:8]:
            print(f"      {s['tokens']:>6}  {s['sektion']}")
        if not d["ventende"]:
            print("      (ingen)")
    if ae.get("maalt"):
        print(f"\n  ÆNDRING over {ae['bygninger']} bygninger: "
              f"{ae['ustabile']}/{ae['sektioner_i_alt']} sektioner skiftede, "
              f"heraf {ae['ustabile_der_er_ventende']} ventende "
              f"({ae['tokens_ustabil_ventende']} tokens)")
        for u in ae["ustabile_liste"][:10]:
            mark = "VENTENDE " if u.get("ventende") else "         "
            print(f"      {mark}{u['sektion']}  — {u['grund']}")
    else:
        print(f"\n  ÆNDRING: ikke målt ({ae.get('grund')})")
    print(f"\n  sektionsnavne i alt: {len(rapport['sektionsnavne'])} "
          "(tjek for ventende der faldt i «andet»)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
