"""`session_id` skal naa cache-telemetrien — hele vejen, i alle tre hop.

Maalt 30/9-2026 paa CT105: `session_id` var TOM paa **3.115 af 3.115**
telemetri-raekker i det nye format, selvom adapteren sendte
`current_session_id()`. Aarsagen er at `stream_followup` er en GENERATOR —
dens krop koerer i forbrugerens kontekst, og ctxvar'en som
`visible_runs.py:1400` saetter naar ikke derind.

Konsekvensen var ikke kosmetisk: hele cache-analysen stod og manglede
netop det felt. «Er nogle sessioners praefiks stabilt hele vejen, og andres
ikke?» kunne kun gaettes ud fra run-naboskab, aldrig maales pr. session.

`run_id` blev traadt eksplicit igennem for praecis samme formaal — kommentaren
i `visible_followup.py` kalder det «Cache-telemetri-kontekst». `session_id`
blev bare aldrig foejet til det par. Denne vagt holder alle tre hop:

  visible_runs.py  ->  stream_visible_followup  ->  stream_followup  ->  telemetri

MUTATIONER der skal fanges:
  M11 — `_kwargs["session_id"] = session_id` fjernet   -> adfaerdstesten falder
  M12 — `session_id=run.session_id` fjernet            -> hop 3-testen falder
  M13 — adapteren tilbage til kun `current_session_id()` -> hop 1-testen falder
"""
from __future__ import annotations

import ast
from pathlib import Path


# ── Hop 2: ADFAERD. Dispatcheren skal videresende feltet. ─────────────────────

def test_dispatcheren_videresender_session_id(monkeypatch):
    """Rigtigt kald gennem `stream_visible_followup`, ingen kilde-laesning."""
    from core.services import visible_followup as vf

    set: dict = {}

    def _fang(**kwargs):
        set.update(kwargs)
        return iter(())

    monkeypatch.setattr(vf._ADAPTERS["groq"], "stream_followup", _fang)
    list(vf.stream_visible_followup(
        provider="groq", model="m", base_messages=[], exchanges=[],
        run_id="visible-abc", session_id="chat-deadbeef",
    ))
    assert set.get("session_id") == "chat-deadbeef", set.get("session_id")
    # Kontrollen: `run_id` naaede frem i forvejen. Uden den her kunne testen
    # bestaa fordi HELE kwargs-samlingen var brudt, ikke fordi feltet virker.
    assert set.get("run_id") == "visible-abc"


def test_kun_openai_compat_faar_telemetri_konteksten(monkeypatch):
    """Paritet med `run_id`: ollama-adapteren tager ikke imod feltet i dag.

    Sendte dispatcheren det til alle adaptere, ville ollama-stien kaste
    TypeError paa et ukendt kwarg — saa denne vagt beskytter en levende sti."""
    from core.services import visible_followup as vf

    set: dict = {}
    monkeypatch.setattr(vf._ADAPTERS["ollama"], "stream_followup",
                        lambda **kw: (set.update(kw), iter(()))[1])
    list(vf.stream_visible_followup(
        provider="ollama", model="m", base_messages=[], exchanges=[],
        run_id="visible-abc", session_id="chat-deadbeef",
    ))
    assert "session_id" not in set, "ollama-adapteren tager ikke imod feltet"
    assert "run_id" not in set


# ── Hop 3 og hop 1: KILDEN, parset som AST (ikke grep). ───────────────────────

def _kald_med_navn(sti: str, funk: str) -> list[ast.Call]:
    """Alle kald til `funk` i filen — uanset om det er `f()` eller `x.f()`."""
    træ = ast.parse(Path(sti).read_text(encoding="utf-8"))
    ud: list[ast.Call] = []
    for node in ast.walk(træ):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        navn = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if navn == funk:
            ud.append(node)
    return ud


def _kwarg(kald: ast.Call, navn: str) -> ast.expr | None:
    for kw in kald.keywords:
        if kw.arg == navn:
            return kw.value
    return None


def test_hop3_visible_runs_sender_runnets_session(monkeypatch):
    """M12-fangeren: kaldestedet skal give `run.session_id` med."""
    kald = _kald_med_navn("core/services/visible_runs.py", "stream_visible_followup")
    assert kald, "fandt ikke kaldet — er det flyttet?"
    traf = []
    for k in kald:
        v = _kwarg(k, "session_id")
        if isinstance(v, ast.Attribute) and v.attr == "session_id":
            traf.append(k)
    assert traf, "stream_visible_followup kaldes uden session_id=run.session_id"
    # Kontrollen: samme kald giver ogsaa run_id — saa testen ikke bare finder
    # et tilfaeldigt kald med det rigtige navn.
    assert any(_kwarg(k, "run_id") is not None for k in traf)


def test_hop1_adapteren_foretraekker_det_eksplicitte_felt():
    """M13-fangeren: telemetrien skal bruge parameteren, med ctxvar som fallback.

    `session_id=current_session_id()` alene er praecis fejlen — den laeser en
    ctxvar der ikke er sat i generatorens forbruger-kontekst."""
    kald = _kald_med_navn("core/services/visible_followup_adapters.py",
                          "record_visible_cache")
    assert kald, "fandt ikke telemetri-kaldet"
    v = _kwarg(kald[0], "session_id")
    assert isinstance(v, ast.BoolOp) and isinstance(v.op, ast.Or), \
        "session_id skal vaere `session_id or current_session_id()`"
    venstre = v.values[0]
    assert isinstance(venstre, ast.Name) and venstre.id == "session_id", \
        "parameteren skal staa FOERST — ellers vinder den tomme ctxvar"
