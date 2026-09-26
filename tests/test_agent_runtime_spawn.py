

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
