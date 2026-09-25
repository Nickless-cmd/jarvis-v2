"""Ingen kørende kode må pege på en ollama-model der er væk.

Målt 25/9-2026: `deepseek-v4-flash:cloud` svarede **HTTP 410 Gone**. 334 ægte
410-fejl på tre døgn, de fleste `inner-llm-enrichment: ollama chat failed`.
`personality_vector` faldt derfor tilbage til sin deterministiske sti hver
gang, og `confidence_by_domain` stod tomt efter **38.758 versioner** — hvilket
gjorde `learning_curriculum` permanent tom.

Fejlen var én tegnforskel: Ollama havde `deepseek-v4**.1**-flash:cloud`.

HVORFOR INGEN OPDAGEDE DET: den gamle tag står STADIG i `ollama list`. Et tjek
der spørger «findes modellen?» får ja. Kun et rigtigt kald giver 410.

Den betalte deepseek-bane (`visible`, provider `deepseek`) er en ANDEN rute og
er urørt — den er Bjørns alene.
"""
from __future__ import annotations

import ast
import json
import pathlib

from core.runtime.config import PROVIDER_ROUTER_FILE, SETTINGS_FILE

#: Modeller der ikke laengere findes paa ollama cloud.
DOEDE_OLLAMA_MODELLER = ("deepseek-v4-flash:cloud",)

#: Filer der OPTEGNER hvad et forsoeg brugte. De maa ikke rettes — saa ville
#: de paastaa at forsoeget koerte paa en model det ikke koerte paa.
OPTEGNELSER = {
    "scripts/interlanguage_binary_jarvis_vs_ollama.py",
    "scripts/jarvis_bare_practice_runner.py",
}


def _kode_strenge(sti: pathlib.Path):
    """Kun strenge der FAKTISK er kode — ikke docstrings og kommentarer."""
    try:
        traen = ast.parse(sti.read_text(encoding="utf-8"))
    except Exception:
        return
    docstrings = set()
    for n in ast.walk(traen):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = ast.get_docstring(n, clean=False)
            if d:
                docstrings.add(d)
    for n in ast.walk(traen):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                and n.value not in docstrings:
            yield n.lineno, n.value


def test_ingen_koerende_kode_peger_paa_en_doed_ollama_model():
    """DEN vagt. En kommentar må gerne nævne den; et kald må ikke bruge den."""
    rod = pathlib.Path(__file__).resolve().parents[1]
    syndere = []
    for mappe in ("core", "apps", "scripts"):
        for f in (rod / mappe).rglob("*.py"):
            rel = str(f.relative_to(rod))
            if rel in OPTEGNELSER or ".worktrees" in rel:
                continue
            for linje, vaerdi in _kode_strenge(f):
                if any(d in vaerdi for d in DOEDE_OLLAMA_MODELLER):
                    syndere.append(f"{rel}:{linje}")
    assert not syndere, (
        "disse peger paa en ollama-model der svarer HTTP 410:\n  " + "\n  ".join(syndere))


def test_de_levende_konstanter_er_opdaterede():
    from core.runtime.settings import RuntimeSettings
    from core.services.central_router_adapt import _AUTONOMOUS_FALLBACK_MODEL
    from core.services.visible_followup import _FAILOVER_FALLBACK_MODEL
    assert RuntimeSettings().autonomous_model_name == "deepseek-v4.1-flash:cloud"
    assert _AUTONOMOUS_FALLBACK_MODEL == "deepseek-v4.1-flash:cloud"
    assert _FAILOVER_FALLBACK_MODEL == "deepseek-v4.1-flash:cloud"


def test_den_BETALTE_deepseek_bane_er_uroert():
    """Den er Bjørns alene, i den synlige bane, og den virker. Et navneskift
    dér ville være et valg — ikke en reparation."""
    rod = pathlib.Path(__file__).resolve().parents[1]
    tekst = (rod / "core/services/llm_pricing.py").read_text(encoding="utf-8")
    assert '"deepseek-v4-flash"' in tekst or "'deepseek-v4-flash'" in tekst


def test_optegnelserne_staar_uroerte():
    """De siger hvad Fase 3 og 4 FAKTISK brugte. At rette dem ville forfalske
    forsøget."""
    rod = pathlib.Path(__file__).resolve().parents[1]
    for rel in OPTEGNELSER:
        assert "deepseek-v4-flash:cloud" in (rod / rel).read_text(encoding="utf-8"), rel


# ── Den halvdel der manglede (25/9-2026) ─────────────────────────────────────
#
# Vagten ovenfor parser `.py`-filer. Men `inner-llm-enrichment` henter sin model
# fra `resolve_provider_router_target(lane="local")` — altsaa fra
# `provider_router.json`, en JSON-fil i `~/.jarvis-v2/config/`. En vagt der kun
# læser Python kunne hverken forhindre eller opdage fejlen: den stod i
# KONFIGURATIONEN, ikke i koden. Maalt: 339 410-fejl i drift indtil kl. 18:30 —
# config'en var rettet kl. 17:39, men processen havde den gamle i hukommelsen
# indtil genstarten. Vagten herunder ville have fanget den den 17.
#
# `.bak`-filer læses ALDRIG. De er optegnelser over hvad der VAR; runtime rører
# dem ikke, og en vagt der fejler paa dem ville skrige i aarvis.


def _strenge(vaerdi, sti="$"):
    """Alle strenge i et JSON-dokument, med deres sti — saa en fejl kan peges ud."""
    if isinstance(vaerdi, str):
        yield sti, vaerdi
    elif isinstance(vaerdi, dict):
        for navn, v in vaerdi.items():
            yield from _strenge(v, f"{sti}.{navn}")
    elif isinstance(vaerdi, list):
        for i, v in enumerate(vaerdi):
            yield from _strenge(v, f"{sti}[{i}]")


def _scan_config(stier=None) -> list[str]:
    """Doede model-tags i de AKTIVE config-filer."""
    fund: list[str] = []
    for sti in (stier if stier is not None else (PROVIDER_ROUTER_FILE, SETTINGS_FILE)):
        sti = pathlib.Path(sti)
        if not sti.exists():
            continue
        try:
            data = json.loads(sti.read_text(encoding="utf-8"))
        except Exception:
            continue
        for json_sti, vaerdi in _strenge(data):
            if any(d in vaerdi for d in DOEDE_OLLAMA_MODELLER):
                fund.append(f"{sti.name}:{json_sti} = {vaerdi!r}")
    return fund


def test_aktiv_config_peger_ikke_paa_en_doed_ollama_model():
    """DEN anden vagt: konfigurationen, ikke koden.

    Fejlen boede i `provider_router.json`. En `.py`-scan kunne ikke se den.
    """
    fund = _scan_config()
    assert not fund, (
        "aktiv config peger paa en ollama-model der svarer HTTP 410:\n  "
        + "\n  ".join(fund)
    )


def test_vagten_kan_faktisk_fange_en_doed_tag(tmp_path):
    """Beviset. Uden det kunne vagten staa grøn fordi den læser intet.

    Samme fejl blev lavet i boot-reconciler-testen samme dag: fixturen svarede
    det samme uanset hvad der blev spurgt, saa testen maalte det lette.
    """
    falsk = tmp_path / "provider_router.json"
    falsk.write_text(
        json.dumps(
            {"lanes": {"local": {"provider": "ollama",
                                 "model": "deepseek-v4-flash:cloud"}}}
        ),
        encoding="utf-8",
    )
    fund = _scan_config([falsk])
    assert fund, "vagten fandt intet i en fil der ER fyldt med den doede tag"
    assert "deepseek-v4-flash:cloud" in fund[0], fund


def test_lokal_lanen_resolverer_ikke_til_en_doed_model():
    """Den kode-vej der faktisk fejlede — ikke en efterligning af den.

    `inner-llm-enrichment` kalder praecis denne funktion med lane='local'.
    """
    from core.runtime.provider_router import resolve_provider_router_target

    maal = resolve_provider_router_target(lane="local")
    model = str(maal.get("model") or "")
    assert not any(d in model for d in DOEDE_OLLAMA_MODELLER), model
    if str(maal.get("provider") or "") == "ollama":
        assert model, "ollama-lanen resolverede uden model"
