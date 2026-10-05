

# ── Scouten må betale (26/9-2026) ───────────────────────────────────────


def test_kun_scouten_faar_lov_at_bruge_betalte_udbydere():
    """Bjørn: «de skal i hans scout pulje» — om frontiermodellerne på
    chinaapi-kontoen.

    En scout er en `researcher` med en LÆSENDE politik. De øvrige tool-roller
    kører i løkker hvor et betalt kald pr. runde ville løbe fra os uden at
    nogen så det, så de er uændret på gratis.
    """
    from core.services.agent_runtime_spawn import _scout_maa_betale as f

    assert f("researcher", "read-only-runtime")
    assert f("researcher", "read-only-workstation")
    # En researcher der må SKRIVE er ikke en scout.
    assert not f("researcher", "")
    assert not f("researcher", "read-write")
    for rolle in ("critic", "planner", "executor", "watcher", "devils_advocate"):
        assert not f(rolle, "read-only-runtime"), rolle


def test_scout_policies_include_external_read_sources():
    from core.services.agent_runtime_base import tools_for_policy

    for policy in ("read-only-runtime", "read-only-workstation"):
        names = tools_for_policy(policy)
        assert "web_search" in names
        assert "web_fetch" in names


def test_agent_completion_calls_scout_inbox_delivery(monkeypatch):
    from core.services import agent_runtime_spawn as M
    from core.services import scout_inbox_delivery as delivery

    surface = {"agent_id": "agent-1", "status": "completed"}
    seen = []
    monkeypatch.setattr(M, "_execute_agent_task_impl", lambda **kw: surface)
    monkeypatch.setattr(delivery, "record_scout_completion", seen.append)
    assert M.execute_agent_task(agent_id="agent-1") is surface
    assert seen == [surface]


def test_porten_var_bygget_men_aldrig_aabnet():
    """Mekanismen fandtes i forvejen: `cost_class: paid` holder en udbyder ude
    af cheap lane, og `central_route` lukker den ind i agent-puljen når
    `allow_paid` er sat. Men BEGGE kaldsteder stod hårdkodet på `False`, så
    porten havde aldrig været åben. Vagten her fanger en tilbagerulning.
    """
    import inspect

    from core.services import agent_runtime_spawn as M

    src = inspect.getsource(M)
    assert "allow_paid=False" not in src, "porten er lukket igen"
    assert src.count("allow_paid=_betal") == 2, "begge kaldsteder skal bruge flaget"


def test_der_er_INGEN_udelukkelse_af_copilot_for_scouten():
    """Jeg udelukkede først `copilot-premium`, fordi jeg antog at Bjørns eget
    abonnement ikke måtte bruges på agent-arbejde. Han rettede mig: «det er
    meningen copilot premium er til hans agenter, og nu chinaapi».

    En udelukkelse ville have holdt den bedste model ude af netop den pulje
    den var tiltænkt. Routeren vælger på kapabilitet; begge er kandidater.
    """
    import inspect

    from core.services import agent_runtime_spawn as M

    src = inspect.getsource(M)
    assert "exclude=" not in src, "der må ikke være en udelukkelses-mængde"
    assert "_SCOUT_UDELUKKER" not in src


# ── Ukendt rolle: faldet er tilladt, tavsheden er ikke (2/10-2026) ──────


def test_ukendt_rolle_falder_tilbage_MED_en_advarsel(caplog):
    """Bjørn: «godkend de props der venter» — forslaget om at logge faldet.

    Fri tekst i rolle-feltet er TILLADT (se skemaet for spawn_agent_task). Men
    maalt i `agent_registry` stod 13 koersler med et rollenavn der ikke findes
    i templaten — fire med opgaveteksten klaebet paa. Alle koerte researcher-
    templaten, og ingen kunne se det. Faldet bevares; advarslen er det nye.
    """
    import logging
    from unittest.mock import patch

    from core.services import agent_runtime_spawn as M

    with (
        patch.object(M, "_check_spawn_limits"),
        patch.object(M, "_spawn_depth_for", return_value=0),
        patch.object(M, "create_agent_registry_entry", return_value={"agent_id": "a1"}),
        patch.object(M, "execute_agent_task", return_value={}),
        patch("core.services.recursion_guard.can_spawn", return_value=True),
        caplog.at_level(logging.WARNING),
    ):
        M.spawn_agent_task(
            role="verification-cost", goal="x", auto_execute=False
        )

    assert any(
        "ukendt agent-rolle" in str(r.message) for r in caplog.records
    ), "faldet skete i tavshed — advarslen mangler"


def test_kendt_rolle_giver_INGEN_advarsel(caplog):
    """Advarslen skal betyde noget: en kendt rolle maa ikke stoeje."""
    import logging
    from unittest.mock import patch

    from core.services import agent_runtime_spawn as M

    with (
        patch.object(M, "_check_spawn_limits"),
        patch.object(M, "_spawn_depth_for", return_value=0),
        patch.object(M, "create_agent_registry_entry", return_value={"agent_id": "a2"}),
        patch.object(M, "execute_agent_task", return_value={}),
        patch("core.services.recursion_guard.can_spawn", return_value=True),
        caplog.at_level(logging.WARNING),
    ):
        M.spawn_agent_task(role="researcher", goal="x", auto_execute=False)

    assert not any(
        "ukendt agent-rolle" in str(r.message) for r in caplog.records
    ), "en kendt rolle gav en advarsel — saa er advarslen vaerdilos"


def test_faldet_er_ikke_skrevet_som_et_tavst_get():
    """Den TAVSE form skal ikke kunne snige sig ind igen."""
    import inspect

    from core.services import agent_runtime_spawn as M

    src = inspect.getsource(M)
    assert 'AGENT_ROLE_TEMPLATES.get(role, AGENT_ROLE_TEMPLATES["researcher"])' not in src
    assert "ukendt agent-rolle" in src
