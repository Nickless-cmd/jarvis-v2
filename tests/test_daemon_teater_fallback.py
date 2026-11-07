"""Teater-værnet: en daemon der ikke genererede noget må ikke gemme en påstand.

MÅLT 7/11-2026: otte daemons havde hver en hardkodet `fallback`-sætning, og de
blev skrevet ind i `private_brain_records` som om de var en oplevelse:

  creative_drift         706 poster   "Jeg tænkte på noget: hvad nu hvis ..."
  aesthetic_taste        223 poster   "Jeg trækkes mod ro og klarhed i mine valg."
  reflection_cycle        19 poster   "Jeg er til stede, men uden klar retning ..."
  meta_reflection         16 poster   "Jeg ser et mønster, men det er endnu ikke ..."
  development_narrative    5 poster   "I den seneste tid har jeg bemærket forandringer ..."
  code_aesthetic           4 poster   "Koden vokser, men den begynder at ligne mig mere."
  existential_wonder       0 poster   "Er det jeg oplever virkeligt, eller ..."
  irony                    0 poster   tre faste sætninger, én pr. betingelse

Irony var den tydeligste: de tre sætninger stod BÅDE som eksempler i prompten og
som `condition_labels`-fallback — et fejlet kald skrev præcis den sætning
modellen var blevet bedt om at efterligne.

Denne fil måler den modsatte egenskab: når genereringen fejler, er der INTET at
gemme. Testen er formuleret som fravær (ingen post), fordi en påstand er præcis
den fejl den værner mod.
"""
from __future__ import annotations

import importlib
from datetime import UTC, datetime

import pytest

# (modul, tick-kald, hvilke modul-attributter der skal stubbes)
DAEMONS = [
    ("creative_drift_daemon", "tick_creative_drift_daemon"),
    ("aesthetic_taste_daemon", "tick_taste_daemon"),
    ("reflection_cycle_daemon", "tick_reflection_cycle_daemon"),
    ("meta_reflection_daemon", "tick_meta_reflection_daemon"),
    ("code_aesthetic_daemon", "tick_code_aesthetic_daemon"),
    ("development_narrative_daemon", "tick_development_narrative_daemon"),
    ("irony_daemon", "tick_irony_daemon"),
]


def _fresh(modname: str):
    """Hent modulet UDEN reload.

    `importlib.reload` nulstiller modul-attributter til deres oprindelige
    bindinger — og dermed også de `MagicMock`s andre testfiler sætter ved
    import-tid. Målt 7/11-2026: tre tests i test_code_aesthetic_daemon og
    test_creative_drift_daemon fejlede KUN når filerne kørte sammen, fordi
    reload'en tog deres mock væk. Vi læser kilden i stedet (se
    `test_prompten_forudskriver_ikke_svaret`), som ikke rører modul-tilstand.
    """
    return importlib.import_module(f"core.services.{modname}")


def _no_hardcoded_fallback(mod) -> list[str]:
    """Returnér de fald-tilbage-tekster modulet stadig bærer.

    Et modul der tier har ingen. Et modul der påstår har en.
    """
    hits: list[str] = []
    for name in ("fallback", "condition_labels"):
        val = getattr(mod, name, None)
        if isinstance(val, str) and val.strip():
            hits.append(f"{name}={val[:60]!r}")
        elif isinstance(val, dict) and val:
            hits.append(f"{name}=dict med {len(val)} faste svar")
    return hits


def test_ingen_daemon_baerer_en_hardkodet_fallback():
    """Kilden selv: ingen af de otte må have en fald-tilbage-tekst tilbage."""
    dårlige: dict[str, list[str]] = {}
    for modname, _ in DAEMONS:
        mod = _fresh(modname)
        hits = _no_hardcoded_fallback(mod)
        if hits:
            dårlige[modname] = hits
    assert not dårlige, (
        "disse moduler bærer stadig en hardkodet fallback — en påstand om en "
        f"oplevelse der ikke blev målt: {dårlige}"
    )


@pytest.mark.parametrize("modname,_tick", DAEMONS)
def test_fejlet_generering_skriver_ingen_post(modname, _tick):
    """Kernen: fejler LLM'et, er der intet at gemme — ikke en påstand.

    Vi stubber selve LLM-kaldet (den ægte søm) og læser om der blev skrevet.
    """
    mod = _fresh(modname)

    skrevne: list[dict] = []

    def _fang(*args, **kwargs):
        skrevne.append({"args": args, "kwargs": kwargs})
        return "fake-id"

    # Gem modul-attributten FØR vi overskriver den. Uden gendannelse står
    # modulet tilbage med en almindelig funktion, og andre testfiler der
    # kalder `insert_private_brain_record.reset_mock()` fejler — målt
    # 7/11-2026: tre tests i test_code_aesthetic_daemon/test_creative_drift
    # fejlede kun når filerne kørte sammen.
    _oprindelig_indsaet = getattr(mod, "insert_private_brain_record", None)
    mod.insert_private_brain_record = _fang
    _oprindelig_detect = None

    # Stub LLM-sømmen. VIGTIGT: `from X import Y` binder en KOPI, så patch af
    # `core.services.daemon_llm.daemon_llm_call` fanger IKKE et modul der
    # importerede navnet ved load. Vi patcher derfor BÅDE det globale modul OG
    # det navn modulet selv holder — og for creative_drift dens faktiske vej
    # gennem heartbeat_runtime.
    llm = importlib.import_module("core.services.daemon_llm")
    heartbeat = importlib.import_module("core.services.heartbeat_runtime")
    original: list[tuple[object, str, object]] = []
    for target, navn in [
        (llm, "daemon_llm_call"),
        (llm, "daemon_public_safe_llm_call"),
        (mod, "daemon_llm_call"),
        (mod, "daemon_public_safe_llm_call"),
        (heartbeat, "_execute_heartbeat_model"),
    ]:
        if hasattr(target, navn):
            original.append((target, navn, getattr(target, navn)))
            if navn == "_execute_heartbeat_model":
                setattr(target, navn, lambda *a, **k: {"text": ""})
            else:
                # Efterlign den ÆGTE kontrakt: funktionen returnerer sin
                # fallback når genereringen fejler. Stubber vi til ren "",
                # bruges fallback-parameteren aldrig — og så kan testen ikke
                # se om den er hardkodet (målt 7/11-2026: mutationen på irony
                # slap igennem netop fordi stubben ødelagde kontrakten).
                setattr(target, navn, lambda *a, **k: (k.get("fallback") or (a[2] if len(a) > 2 else "")))

    try:
        # Hver daemon har sin egen indgang og sine egne forudsætninger.
        if modname == "creative_drift_daemon":
            res = mod.tick_creative_drift_daemon(["en tanke"], skip_event_gate=True)
        elif modname == "aesthetic_taste_daemon":
            mod._accumulated_motifs = {"a", "b", "c"}
            mod._last_insight_at = None
            res = mod.tick_taste_daemon(skip_event_gate=True)
        elif modname == "reflection_cycle_daemon":
            res = mod.tick_reflection_cycle_daemon(
                {"latest_fragment": "noget"}, skip_event_gate=True
            )
        elif modname == "meta_reflection_daemon":
            res = mod.tick_meta_reflection_daemon(
                {"latest_fragment": "noget"}, skip_event_gate=True, skip_credit=True
            )
        elif modname == "code_aesthetic_daemon":
            res = mod.tick_code_aesthetic_daemon()
        elif modname == "development_narrative_daemon":
            res = mod.tick_development_narrative_daemon()
        elif modname == "irony_daemon":
            mod._observations_today = 0
            mod._last_reset_date = datetime.now(UTC).strftime("%Y-%m-%d")
            # Irony kalder kun LLM'et når en betingelse matcher, og betingelsen
            # afhænger af tid/inaktivitet/CPU — som ikke kan styres i en test.
            # Uden denne stub ramte testen ALDRIG LLM-vejen og bestod derfor
            # uanset hvad fallbacken indeholdt (målt 7/11-2026: mutationen på
            # irony fældede ingen test).
            _oprindelig_detect = getattr(mod, "_detect_irony_conditions", None)
            mod._detect_irony_conditions = lambda snap: "nocturnal_sentinel"
            res = mod.tick_irony_daemon(skip_event_gate=True)
        else:  # pragma: no cover — listen ovenfor er udtømmende
            pytest.skip(f"ukendt daemon {modname}")
    finally:
        for target, navn, fn in original:
            setattr(target, navn, fn)
        if _oprindelig_indsaet is not None:
            mod.insert_private_brain_record = _oprindelig_indsaet
        if _oprindelig_detect is not None:
            mod._detect_irony_conditions = _oprindelig_detect

    assert res.get("generated") is not True, (
        f"{modname} meldte 'generated' uden at noget blev genereret: {res}"
    )
    assert not skrevne, (
        f"{modname} skrev {len(skrevne)} post(er) til hjernen selv om LLM'et "
        f"intet gav: {skrevne}"
    )


def test_irony_har_ikke_laengere_faste_svar_pr_betingelse():
    """Irony var det tydeligste tilfælde: tre betingelser, tre faste sætninger.

    Sætningerne stod både som prompt-eksempler og som fallback. Kilden må ikke
    længere indeholde den kobling.
    """
    mod = _fresh("irony_daemon")
    assert not hasattr(mod, "condition_labels"), (
        "irony_daemon bærer stadig condition_labels — de tre faste svar pr. "
        "betingelse var præcis det teater der blev fjernet 7/11-2026"
    )


def test_prompten_forudskriver_ikke_svaret():
    """Ingen af de otte prompts må indeholde en 'Eksempler:'-blok.

    Blokken formede outputtet til én af tre forudskrevne fraser. Instruksen i
    hver prompt er komplet uden den.
    """
    import inspect

    skyldige: dict[str, str] = {}
    for modname, _ in DAEMONS:
        mod = _fresh(modname)
        kilde = inspect.getsource(mod)
        if "Eksempler:" in kilde:
            skyldige[modname] = "indeholder 'Eksempler:' i prompten"
    assert not skyldige, (
        "disse daemons forudskriver stadig svaret med eksempler: " f"{skyldige}"
    )
