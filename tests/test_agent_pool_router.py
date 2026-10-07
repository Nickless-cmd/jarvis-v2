"""Tests for core/services/agent_pool_router.py — agent-pool routing + kvalitets-læring."""
from __future__ import annotations
import core.services.agent_pool_router as apr


def test_route_agent_task_delegates_to_central_route(monkeypatch):
    """Task 11: route_agent_task router gennem central_route (lane=agent)."""
    seen = {}

    def fake_route(*, lane, task, exclude):
        seen.update({"lane": lane, "task": task})
        return {"provider": "cerebras", "model": "gemma-4-31b", "lane": lane,
                "is_floor": False}

    monkeypatch.setattr("core.services.central_route.route", fake_route)
    r = apr.route_agent_task(kind="coding")
    assert r["provider"] == "cerebras"
    assert seen["lane"] == "agent"
    assert seen["task"]["kind"] == "coding"


def test_update_task_score_ema(monkeypatch):
    """Task 12: EMA-opdatering af task_score fra outcome."""
    store = {}
    monkeypatch.setattr(apr, "_load_task_scores", lambda p, m: {"coding": 0.5})
    monkeypatch.setattr(apr, "_save_task_scores",
                        lambda p, m, s: store.update(s))
    apr.update_task_score(provider="cerebras", model="gemma-4-31b",
                          kind="coding", outcome_quality=1.0, lr=0.1)
    assert abs(store["coding"] - 0.55) < 1e-6      # (1-0.1)*0.5 + 0.1*1.0


def test_update_task_score_seeds_at_half(monkeypatch):
    store = {}
    monkeypatch.setattr(apr, "_load_task_scores", lambda p, m: {})   # ukendt
    monkeypatch.setattr(apr, "_save_task_scores", lambda p, m, s: store.update(s))
    apr.update_task_score(provider="x", model="y", kind="reasoning",
                          outcome_quality=1.0, lr=0.1)
    assert abs(store["reasoning"] - 0.55) < 1e-6   # seed 0.5 -> 0.55


# ── Ejerparameteren og fitnessvagten (7/10-2026) ────────────────────────────
#
# To garantier der ikke fandtes før i dag, og som begge skal kunne VISES at
# fejle: uden ejeren i kaldet kan §7.1 ikke håndhæves, og en fitness-kontrol
# der fejler må ikke se ud som en der godkendte.


def test_ejeren_baeres_med_ind_i_rutebeslutningen(monkeypatch):
    """§7.1: kun Bjørns opgaver må nå hans DeepSeek-API.

    Reglen kan ikke håndhæves hvis ejeren ikke følger med ind i beslutningen.
    Testen fejler hvis parameteren falder ud af `task`-ordbogen — så måler den
    den faktiske ledning og ikke sin egen opsætning.
    """
    seen = {}

    def fake_route(*, lane, task, exclude):
        seen.update(task)
        return {"provider": "cerebras", "model": "gemma-4-31b"}

    monkeypatch.setattr("core.services.central_route.route", fake_route)
    r = apr.route_agent_task(kind="coding", owner_user_id="bjorn")
    assert seen["owner_user_id"] == "bjorn"
    assert r["route_source"] == "agent_pool"


def test_uden_ejer_sendes_None_ikke_et_gaet(monkeypatch):
    """En ukendt ejer må ikke blive til en tilfældig. `None` er ærligt."""
    seen = {}
    monkeypatch.setattr("core.services.central_route.route",
                        lambda *, lane, task, exclude: seen.update(task) or
                        {"provider": "p", "model": "m"})
    apr.route_agent_task(kind="coding")
    assert "owner_user_id" in seen
    assert seen["owner_user_id"] is None


def test_fitness_fejl_er_synlig_ikke_tav(monkeypatch, caplog):
    """«Tom tabel» (ukendt → tilladt) og «kontrollen er i stykker» er to ting.

    Indtil 7/10-2026 endte begge i `except Exception: pass`, så en måling der
    ALDRIG kørte så ud som et lovligt svar. Testen fejler hvis grenen tier
    igen — den lytter på både loggen og returværdien.
    """
    import core.services.agent_model_fitness as amf

    monkeypatch.setattr("core.services.central_route.route",
                        lambda *, lane, task, exclude: {"provider": "p", "model": "m"})

    def bombe(*a, **kw):
        raise RuntimeError("fitness-tabellen er nede")

    monkeypatch.setattr(amf, "er_blokeret", bombe)
    with caplog.at_level("WARNING"):
        r = apr.route_agent_task(kind="coding")
    assert r.get("fitness_ukendt") is True, "fejlet kontrol må ikke se godkendt ud"
    assert any("fitness" in m.lower() for m in caplog.messages), \
        "den tavse gren er tilbage — fejlen skal kunne ses"


def test_fitness_ukendt_er_ikke_sat_naar_kontrollen_koerer(monkeypatch):
    """Den positive nabohændelse gennem samme søm: kører kontrollen, er der
    ingen `fitness_ukendt`. Uden den kunne flaget stå på i alle tilfælde."""
    import core.services.agent_model_fitness as amf

    monkeypatch.setattr("core.services.central_route.route",
                        lambda *, lane, task, exclude: {"provider": "p", "model": "m"})
    monkeypatch.setattr(amf, "er_blokeret", lambda p, m, rolle="": False)
    r = apr.route_agent_task(kind="coding")
    assert not r.get("fitness_ukendt")


