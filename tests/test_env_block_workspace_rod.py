"""Blokken skal sige hvor hans workspace ER, ikke kun hvor han staar.

MAALT 12/9-2026 kl. 20:04 (incident 6798), i Bjoerns EGEN chat-session — ikke
et autonomt run, som inspektionen ellers skrev:

    read_before_write_guard: BLOCKED bash overwrite of MEMORY.md
    (/media/projects/jarvis-v2/workspaces/bjorn/MEMORY.md)

Den fil findes ikke. Den rigtige er /home/bs/.jarvis-v2/workspaces/bjorn/
MEMORY.md — 124 KB, aendret samme dag.

Regnestykket bag fejlen har to led, og begge er vores:

  1. Blokken fortalte `mappe=/media/projects/jarvis-v2` — hvor han STAAR.
  2. Repoet omtaler workspacet RELATIVT: `workspaces/<bruger>/MEMORY.md` staar
     saadan i kommentarer, tests og planer, aldrig forankret til JARVIS_HOME.

Repo-rod + relativ sti = den forkerte absolutte sti. Han gaettede ikke; han
regnede rigtigt paa forkerte tal.
"""
import core.services.env_block as eb


def test_blokken_naevner_den_absolutte_workspace_rod(monkeypatch):
    monkeypatch.setattr(eb, "is_enabled", lambda: True)
    blok = eb.render_env_block()
    assert "workspace=" in blok, "blokken siger stadig ikke hvor workspacet er"
    assert "/workspaces/" in blok


def test_roden_er_ABSOLUT_ikke_relativ(monkeypatch):
    """En relativ sti er praecis det problem der skal loeses. Siger vi
    «workspaces/bjorn», har vi gentaget fejlen i den besked der skulle rette
    den."""
    rod = eb._workspace_rod()
    assert rod.startswith("/"), f"roden er ikke absolut: {rod}"


def test_roden_peger_paa_JARVIS_HOME_ikke_paa_repoet():
    from core.runtime.config import WORKSPACES_DIR
    assert eb._workspace_rod().startswith(str(WORKSPACES_DIR))
    assert "/media/projects/jarvis-v2/workspaces" not in eb._workspace_rod()


def test_et_opslag_der_fejler_vaelter_ikke_blokken(monkeypatch):
    """Blokken sidder i HVER prompt. En fejl her maa aldrig koste en tur."""
    def _boom():
        raise RuntimeError("ingen kontekst")
    monkeypatch.setattr(
        "core.identity.workspace_context.current_workspace_name", _boom)
    assert eb._workspace_rod() == ""
    monkeypatch.setattr(eb, "is_enabled", lambda: True)
    assert "HER STÅR DU" in eb.render_env_block()
