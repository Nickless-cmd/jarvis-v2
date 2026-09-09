"""Samme politik-kontrakt paa begge shell-stier — Fase 3, K10.

«persistent and one-shot shell paths obey the same policy contract, and no
approval mode silently widens sandbox authority.»

## Hvad denne fil VOGTER, og hvad den ikke goer

Den anden halvdel — «ingen godkendelses-tilstand udvider tavst
sandkasse-myndighed» — er en sikkerheds-egenskab der ikke kan ses ved at laese
koden én gang. Nogen kunne tilfoeje `if trust: spring sandkassen over` og
INTET ville fejle. Derfor staar den her som en test.

Den foerste halvdel — at de to stier er lige indespaerrede — er IKKE lukket, og
det er et bevidst valg: den vedvarende shell er Bjoerns vej udenom systemet, og
den staar urort efter hans staaende instruks. Det der ER lukket, er at den
LYVER: begge stier rapporterer, og den vedvarende siger hoejt at den ikke kan
indespaerres pr. kommando. Forskellen mellem «ikke indespaerret» og «troede den
var det» er hele forskellen paa en aaben doer og en man ikke vidste var aaben.
"""
from __future__ import annotations

import pytest

from core.services import bash_sandbox as SB


# ── godkendelse maa ALDRIG give mere sandkasse-myndighed ─────────────────

def test_enforcement_kender_hverken_trust_eller_godkendelse():
    """Signaturen er selve vaernet: der er intet flag at saette."""
    import inspect
    sig = inspect.signature(SB.enforcement)
    forbudte = {"trust", "trust_all", "approved", "owner_approved",
                "skip_approval", "force"}
    assert not forbudte & set(sig.parameters), (
        "enforcement() har faaet et godkendelses-flag — det er praecis den vej "
        "hvor en godkendelse tavst kunne udvide sandkassen")


def test_en_GODKENDT_kommando_faar_samme_indespaerring_som_en_ugodkendt(
        isolated_runtime, monkeypatch):
    """`_force_bash` saetter `_runtime_trust_all=True`. Det maa springe
    GODKENDELSEN over — og kun den."""
    from core.tools import simple_tools_web as W

    set_af: list[tuple] = []
    ægte = SB.enforcement
    monkeypatch.setattr(SB, "enforcement",
                        lambda cmd, cwd, **kw: set_af.append((cmd, cwd, kw))
                        or ægte(cmd, cwd, **kw))
    # Tving engangs-stien: den vedvarende session naas ved at aabne en
    # default-session, saa den slaas fra ved at lade aabningen give None.
    monkeypatch.setattr(W, "_get_or_open_default_bash_session", lambda: None)

    W._exec_bash({"command": "echo k10"})
    W._exec_bash({"command": "echo k10", "_runtime_trust_all": True})

    assert len(set_af) == 2, set_af
    assert set_af[0] == set_af[1], (
        "den godkendte vej bad om en ANDEN indespaerring end den ugodkendte")


def test_force_bash_gaar_gennem_den_SAMME_exec(monkeypatch):
    """Den gamle `_force_bash` var en PARALLEL implementation uden sandkasse.
    En kommando opfoerte sig forskelligt alt efter hvem der kaldte den."""
    import inspect
    from core.tools import force_handlers as F
    kilde = inspect.getsource(F._force_bash)
    krop = kilde.split('"""')[-1]      # docstringen NAEVNER den gamle subprocess
    assert "_exec_bash(" in krop
    assert "subprocess" not in krop, "force-stien koerer sin egen subprocess igen"


def test_trust_springer_ikke_DESTRUKTIVT_over():
    """Maalt 7/9: `rm -rf /` klassificeres som destructive, ikke blocked, og
    slap derfor igennem i autonome runs. Ejer-godkendelsen baeres i en
    ContextVar — ikke i argumenterne, som modellen selv skriver."""
    import inspect
    from core.tools import simple_tools_web as W
    kilde = inspect.getsource(W._exec_bash)
    i_destruktiv = kilde.index('classification == "destructive"')
    i_godkendelse = kilde.index('classification == "approval"')
    assert i_destruktiv < i_godkendelse, "destruktiv-tjekket er flyttet efter trust"
    assert "er_ejer_godkendt()" in kilde


# ── begge stier RAPPORTERER — ingen af dem lader som ingenting ───────────

def test_den_vedvarende_sti_siger_HOEJT_at_den_ikke_er_indespaerret(
        isolated_runtime, monkeypatch):
    """Uden den linje ville en taendt sandkasse se ud som om den daekkede bash,
    mens den normale vej gik udenom."""
    import inspect
    from core.tools import simple_tools_web as W
    kilde = inspect.getsource(W._exec_bash)
    assert '"actual": False' in kilde and '"honored": False' in kilde
    assert "kan ikke indespaerres" in kilde.replace("æ", "ae")


def test_engangs_stien_rapporterer_sin_faktiske_indespaerring():
    import inspect
    from core.tools import simple_tools_web as W
    kilde = inspect.getsource(W._exec_bash)
    assert "enforcement(command" in kilde
    assert 'svar["confinement"] = _indespaerring' in kilde


def test_en_kollapset_sandkasse_rapporteres_frem_for_at_tie(isolated_runtime,
                                                            monkeypatch):
    """Retningen er fail-OPEN med vilje — en manglende mekanisme maa ikke goere
    bash ubrugelig — men den maa ikke vaere tavs."""
    from core.tools import simple_tools_web as W
    monkeypatch.setattr(SB, "enforcement",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bwrap vaek")))
    monkeypatch.setattr(W, "_get_or_open_default_bash_session", lambda: None)
    svar = W._exec_bash({"command": "echo k10"})
    assert svar["status"] == "ok"
    assert svar["confinement"]["honored"] is False
    assert "bwrap vaek" in str(svar["confinement"]["reason"])


# ── og selve fail-closed-vejen findes for dem der vil have den ───────────

def test_require_er_den_ENESTE_vej_til_fail_closed(monkeypatch):
    monkeypatch.setattr(SB, "is_available", lambda: False)
    monkeypatch.setattr(SB, "is_enabled", lambda: True)
    assert SB.enforcement("echo x", "/tmp").honored is False
    with pytest.raises(SB.ConfinementUnavailable):
        SB.enforcement("echo x", "/tmp", require=True)
