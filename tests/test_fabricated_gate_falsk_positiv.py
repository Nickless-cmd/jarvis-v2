"""Gaten anklagede ham for at tale om emnet.

MAALT i produktion 12/9-2026, incident 8839 (gentaget ×4, sidst 18:28:51):

    gate fabricated_tool_result → error: 2 fabrikeret, 0 laekket;
    ids=tool-result-visning, tool-result-rendering

«visning» og «rendering» er danske ord. Den aften byggede vi netop
tool-result-visningen i mobilappen, saa Jarvis skrev om den — og moenstret
`[A-Za-z0-9_-]{6,}` udtrak ordene som resultat-id'er. De findes ikke i storen,
saa gaten bogfoerte dem som FABRIKEREDE: anklagen for «den ene loegn der ikke
kan bortforklares», udloest af at naevne emnet.

Kommentaren ved moenstret paastod «snaevert nok til ikke at ramme almindelig
prosa» og «nul falske positiver paa fabrikation». Begge dele var forkerte.
"""
import pytest

from core.services.fabricated_tool_result_gate import _TOOL_RESULT_ID_RE


@pytest.mark.parametrize("prosa", [
    "tool-result-visning",                    # ordret fra incident 8839
    "tool-result-rendering",                  # ordret fra incident 8839
    "Jeg retter tool-result-visning i appen.",
    "tool-result-haandtering og tool-result-opsummering",
])
def test_dansk_prosa_om_tool_resultater_er_IKKE_et_id(prosa):
    assert _TOOL_RESULT_ID_RE.findall(prosa) == []


def test_et_AEGTE_id_fanges_stadig():
    """`tool-result-{uuid4().hex}` — 32 tegn hex (tool_result_store:41)."""
    ægte = "tool-result-cea3b4c38abd42bf827c68a9e1fa829a"
    assert _TOOL_RESULT_ID_RE.findall(ægte) == ["cea3b4c38abd42bf827c68a9e1fa829a"]


def test_den_DOKUMENTEREDE_fabrikation_fanges_stadig():
    """Rod-tilfaeldet 18/8-2026: fem opfundne resultater med sekventielle
    hex-moenstre. Skaerper man til praecis 32 tegn, slipper de kortere igennem."""
    for opfundet in ("tool-result-4f0a1b2c", "tool-result-5a6b7c8d", "tool-result-6b7c8d9e"):
        assert _TOOL_RESULT_ID_RE.findall(opfundet), f"{opfundet} slap forbi"


def test_id_i_den_fulde_markoer_form_fanges():
    linje = "([tool_result:tool-result-4f0a1b2c3d4e5f60 — bash_session_open: {...}])"
    assert _TOOL_RESULT_ID_RE.findall(linje) == ["4f0a1b2c3d4e5f60"]


def test_for_kort_hex_er_ikke_et_id():
    """Otte tegn er gulvet. Under det er «dead» og «beef» almindelige ord."""
    assert _TOOL_RESULT_ID_RE.findall("tool-result-dead") == []


# ── Sporbarheden ────────────────────────────────────────────────────────────

def test_incidenten_baerer_run_id_og_session(monkeypatch):
    """Incident 8839 og 6798 stod begge med TOMT run_id og session_id.

    Feltet fandtes i `record_central_incident` hele tiden — kalderen sendte det
    bare ikke. To alvorlige haendelser (en honesty-gate der fyrede, en guard der
    blokerede en overskrivning af MEMORY.md) uden spor til nogen koersel, og
    derfor umulige at efterforske.
    """
    import core.runtime.db_central_incidents as dbi
    import core.services.claim_scanner as cs
    import core.services.session_context_resolve as sc

    fanget = {}
    monkeypatch.setattr(dbi, "record_central_incident",
                        lambda **kw: fanget.update(kw) or 1)
    monkeypatch.setattr(sc, "aktivt_run_id", lambda standard="": "visible-TEST")
    monkeypatch.setattr(sc, "aktiv_session_id", lambda standard="": "chat-TEST")
    monkeypatch.setattr(cs, "scan_enabled", lambda: True, raising=False)

    cs._fabricated_tool_result_footnote(
        "her er [tool_result:tool-result-4f0a1b2c3d4e5f60] som aldrig blev kaldt")

    assert fanget.get("run_id") == "visible-TEST", "incidenten kan ikke spores til en koersel"
    assert fanget.get("session_id") == "chat-TEST"


def test_manglende_kontekst_vaelter_ikke_gaten():
    """Opslaget er self-safe: en gate maa aldrig kunne doe af at sporet mangler."""
    from core.services.session_context_resolve import aktivt_run_id
    assert aktivt_run_id("(intet)") in ("(intet)",) or isinstance(aktivt_run_id(), str)


def test_ALLE_gate_incidenter_kan_spores_til_en_koersel():
    """Invariant, ikke ét sted.

    Incident 6798 (`exec_command_guard` blokerede en overskrivning af MEMORY.md)
    stod uden run_id. Da jeg gik efter dét ene kald, viste `gate_execution` sig
    at have TRE — og de to andre manglede ogsaa. Det tredje var det vaerste:
    «exec-gate kollaps → sidste-udvej GREEN (enforcement-tab)», severity
    `severe`. En SIKKERHEDS-gate der falder aaben, uden spor til hvad der slap
    igennem.

    Testen laeser AST'et, ikke teksten: foerste udgave delte kilden paa
    ")"-tegnet og ramte en parentes inde i `str(nerve or "exec")`, saa den var
    roed paa uroert kode og blind for det den skulle maale.
    """
    import ast
    import pathlib as _p

    træ = ast.parse(_p.Path("core/services/gate_execution.py").read_text())
    kald = [n for n in ast.walk(træ)
            if isinstance(n, ast.Call)
            and getattr(n.func, "id", "") == "record_central_incident"]
    assert len(kald) >= 3, "forventede flere incident-kald — er filen delt op?"
    for n in kald:
        navne = {k.arg for k in n.keywords}
        assert "run_id" in navne, f"incident paa linje {n.lineno} kan ikke spores"
        assert "session_id" in navne, f"incident paa linje {n.lineno} mangler session"
