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
import pathlib

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
