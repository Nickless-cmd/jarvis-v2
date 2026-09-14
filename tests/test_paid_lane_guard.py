"""Kun Bjørns egne ture må koste penge (2026-09-05).

Reglen stod i settings.py fra 16. juli, men lane-opslaget sker i
provider_router.json — og dér pegede `inner_enrichment` på api.deepseek.com i
omkring syv uger uden at nogen opdagede det. Vagten spørger det sted der
faktisk bestemmer.
"""
from __future__ import annotations

import pytest

from core.services import paid_lane_guard as PLG

_PAID = "https://api.deepseek.com/v1"
_FREE = "http://127.0.0.1:11434"


def _targets(mapping, monkeypatch):
    def _resolve(*, lane):
        if lane not in mapping:
            raise RuntimeError("ukendt lane")
        provider, model, url = mapping[lane]
        return {"provider": provider, "model": model, "base_url": url}
    monkeypatch.setattr(
        "core.runtime.provider_router.resolve_provider_router_target", _resolve)


def test_a_clean_setup_reports_nothing(monkeypatch):
    _targets({
        "visible": ("deepseek", "deepseek-v4-flash", _PAID),
        "inner_enrichment": ("ollama", "deepseek-v4-flash:cloud", _FREE),
        "local": ("ollama", "glm-5.2:cloud", _FREE),
        "cheap": ("aihubmix", "gpt-5.5-free", "https://aihubmix.com/v1"),
    }, monkeypatch)
    assert PLG.audit_paid_lanes() == []
    assert PLG.build_paid_lane_guard_surface()["ok"] is True


def test_the_actual_leak_is_caught(monkeypatch):
    """Praecis den tilstand der stod i syv uger."""
    _targets({
        "visible": ("deepseek", "deepseek-v4-flash", _PAID),
        "inner_enrichment": ("deepseek", "deepseek-v4-flash", _PAID),
    }, monkeypatch)
    leaks = PLG.audit_paid_lanes()
    assert len(leaks) == 1
    assert leaks[0]["lane"] == "inner_enrichment"
    assert leaks[0]["host"] == "api.deepseek.com"
    surface = PLG.build_paid_lane_guard_surface()
    assert surface["ok"] is False and "inner_enrichment" in surface["summary"]


def test_his_own_lanes_are_allowed_to_cost_money(monkeypatch):
    _targets({"visible": ("deepseek", "deepseek-v4-flash", _PAID)}, monkeypatch)
    assert PLG.audit_paid_lanes() == []
    assert "primary" in PLG._ALLOWED_PAID_LANES


@pytest.mark.parametrize("url,paid", [
    ("https://api.deepseek.com/v1", True),
    ("https://API.DeepSeek.com/v1/chat", True),
    ("http://127.0.0.1:11434", False),
    ("https://api.groq.com/openai/v1", False),
    ("", False),
    ("ikke en url", False),
])
def test_only_the_paid_host_counts(url, paid):
    assert PLG.is_paid(url) is paid


def test_an_unresolvable_lane_is_skipped_not_reported(monkeypatch):
    _targets({"visible": ("deepseek", "x", _PAID)}, monkeypatch)  # resten kaster
    assert PLG.audit_paid_lanes() == []


def test_the_guard_never_fixes_anything_itself(monkeypatch):
    """Et lane-valg er en driftsbeslutning. Vagten maa goere det synligt,
    ikke lave det om bag ryggen paa Bjoern."""
    import inspect
    src = inspect.getsource(PLG)
    for forbidden in ("configure_provider_router_entry", "write_text", "set_runtime_state_value"):
        assert forbidden not in src


def test_a_broken_resolver_never_raises(monkeypatch):
    def _boom(**_kw):
        raise RuntimeError("registret er vaek")
    monkeypatch.setattr(
        "core.runtime.provider_router.resolve_provider_router_target", _boom)
    assert PLG.audit_paid_lanes() == []
    assert PLG.check_paid_lanes()["leaks"] == []


# ─────────────────────────────────────────────────────────────────────────
# Vagten maalte det forkerte (14/9-2026)
#
# Bjoern: «Deepseek skal kun bruges i visible lane af mig... intet andet skal
# bruge den vej». Vagten svarede «kun hans egne ture koster penge» — MENS
# fire lanes brugte penge.
#
# To grunde, og den anden er den vigtige:
#
#   1. Den spurgte en HARDKODET liste paa seks lane-navne. `agent`, `vision`,
#      `compat_oneshot`, `agentic_round` og `primary_cache_warmer` stod ikke i
#      den. Lane-navne bliver ved med at komme til; listen kan ikke foelge med.
#
#   2. Den laeste KONFIGURATIONEN, ikke hovedbogen. En vej der gaar uden om
#      routeren — fx `execute_openai_compat_heartbeat_prompt`, der hardkoder
#      api.deepseek.com — er strukturelt usynlig for den. Konfigurationen er en
#      paastand om hvad der VIL ske; hovedbogen er hvad der SKETE.
#
# Reglen handler ikke om navne. Den handler om HVEM kaldet tilhoerer, og det
# kan hver eneste raekke svare paa: et betalt kald skal baere et `visible-`
# run-id. Den invariant kan ikke forældes af et nyt lane-navn.
# ─────────────────────────────────────────────────────────────────────────


def _hovedbog(monkeypatch, raekker):
    """Byt costs-opslaget ud. Raekker: (lane, provider, run_id, cost)."""
    class _Conn:
        def execute(self, q, p=()):
            class _C:
                def fetchall(_s): return raekker
            return _C()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    import core.runtime.db as db
    monkeypatch.setattr(db, "connect", lambda: _Conn())


def test_et_betalt_kald_UDEN_synligt_run_er_et_brud(monkeypatch):
    """Kernen. `vision` og `compat_oneshot` saa praecis saadan ud."""
    _hovedbog(monkeypatch, [("vision", "deepseek", "", 0.02)])
    brud = PLG.audit_paid_spend()
    assert len(brud) == 1
    assert brud[0]["lane"] == "vision"
    assert brud[0]["cost_usd"] == 0.02


def test_hans_egne_ture_er_IKKE_et_brud(monkeypatch):
    """`agentic_round` er runderne INDE i hans samtaler — 5.782 kald, alle paa
    `visible-`-koersler. Et lane-navn der ikke staar paa en liste goer dem ikke
    til et brud, og en vagt der raaber op om hans egne ture bliver ignoreret."""
    _hovedbog(monkeypatch, [
        ("agentic_round", "deepseek", "visible-abc", 15.09),
        ("visible", "deepseek", "visible-def", 6.57),
        ("primary", "deepseek", "visible-ghi", 2.68),
    ])
    assert PLG.audit_paid_spend() == []


def test_en_AUTONOM_koersel_er_et_brud(monkeypatch):
    """Det er den tydeligste form: han sad der ikke."""
    _hovedbog(monkeypatch, [("visible", "deepseek", "autonomous-xyz", 1.00)])
    brud = PLG.audit_paid_spend()
    assert len(brud) == 1 and brud[0]["run_id"] == "autonomous-xyz"


def test_et_NYT_lane_navn_fanges_UDEN_at_nogen_opdaterer_en_liste(monkeypatch):
    """Selve pointen med at skifte invariant. `compat_oneshot` fandtes ikke da
    vagten blev skrevet, og den gamle form kunne kun se seks navne."""
    _hovedbog(monkeypatch, [("en_lane_der_ikke_fandtes_endnu", "deepseek", "", 5.0)])
    assert len(PLG.audit_paid_spend()) == 1


def test_en_GRATIS_udbyder_er_aldrig_et_brud(monkeypatch):
    """Baggrundsarbejde paa ollama er praecis det reglen beder om."""
    _hovedbog(monkeypatch, [("inner_enrichment", "ollama", "", 0.0)])
    assert PLG.audit_paid_spend() == []


def test_cache_varmeren_taeller_MED(monkeypatch):
    """Den bogfoeres under sit EGET udbyder-navn, ikke «deepseek» — og rammer
    alligevel den betalte API 11.429 gange. Et udbyder-navn er en etiket, ikke
    et bevis."""
    _hovedbog(monkeypatch, [("primary", "primary_cache_warmer", "", 1.50)])
    brud = PLG.audit_paid_spend()
    assert len(brud) == 1, "cache-varmeren slap forbi paa sit udbyder-navn"


def test_brud_samles_pr_lane_med_BELOEB(monkeypatch):
    """«Der er et brud» er ikke handlingsbart. «vision har brugt $0,02 over ni
    dage» er — og forskellen afgoer om noget bliver rettet."""
    _hovedbog(monkeypatch, [
        ("vision", "deepseek", "", 0.01),
        ("vision", "deepseek", "", 0.01),
        ("compat_oneshot", "deepseek", "", 0.30),
    ])
    brud = {b["lane"]: b for b in PLG.audit_paid_spend()}
    assert abs(brud["vision"]["cost_usd"] - 0.02) < 1e-9
    assert brud["vision"]["antal"] == 2
    assert abs(brud["compat_oneshot"]["cost_usd"] - 0.30) < 1e-9


def test_fladen_BAERER_hovedbogens_dom(monkeypatch):
    """En vagt hvis dom ingen kan se, er den fejl vi lige har rettet.

    Den GAMLE flade sagde «kun hans egne ture koster penge» mens fire lanes
    brugte penge. Fladen skal baere begge svar: hvad konfigurationen LOVER, og
    hvad hovedbogen REGISTREREDE."""
    _targets({"visible": ("deepseek", "deepseek-v4-flash", _PAID)}, monkeypatch)
    _hovedbog(monkeypatch, [("vision", "deepseek", "", 0.02)])
    u = PLG.build_paid_lane_guard_surface()
    assert u["ok"] is False, "fladen sagde god for et maalt brud"
    assert u["spend_leaks"], "fladen baerer ikke hovedbogens dom"


def test_en_UDLAESELIG_hovedbog_paastaar_ikke_at_alt_er_godt(monkeypatch):
    """Kan vi ikke laese hovedbogen, VED vi ikke at reglen holder.

    «Ingen brud fundet» og «jeg kunne ikke se efter» er to forskellige svar, og
    det var praecis sammenblandingen af dem der lod det her ligge. Samme regel
    som boot-reconcilerens ulaeselige in_flight-lager.
    """
    import core.runtime.db as db
    monkeypatch.setattr(db, "connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
    _targets({"visible": ("deepseek", "deepseek-v4-flash", _PAID)}, monkeypatch)
    u = PLG.build_paid_lane_guard_surface()
    assert u["spend_checked"] is False
    assert u["ok"] is None, "en ulaeselig hovedbog blev til et frikendende ja"


def test_vagten_maaler_HOVEDBOGEN_ikke_kun_konfigurationen():
    """Kilde-vagt paa at opslaget faktisk gaar i costs-tabellen. AST kan ikke
    se en SQL-streng, saa her ER teksten det rigtige at proeve — men paa
    funktionens egen kilde, ikke paa hele filen."""
    import inspect
    kilde = inspect.getsource(PLG.audit_paid_spend)
    assert "FROM costs" in kilde, "vagten laeser ikke hovedbogen"


def test_hjerteslaget_KALDER_hovedbogs_revisionen():
    """En vagt ingen kalder er den hyppigste fejl i huset — og en revision der
    kun findes som funktion ville gentage praecis det hul den er skrevet for at
    lukke. AST, ikke tekstsoegning: kaldet kunne staa i en kommentar, og det
    GOER det faktisk lige over kaldestedet.
    """
    import ast
    import pathlib
    kilde = pathlib.Path("core/services/heartbeat_runtime_influence.py").read_text()
    træ = ast.parse(kilde)
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(træ) if isinstance(k, ast.Call)}
    assert "check_paid_spend" in kaldt, "hovedbogs-revisionen bliver aldrig koert"
    assert "check_paid_lanes" in kaldt, "konfigurations-vagten forsvandt"


# ─────────────────────────────────────────────────────────────────────────
# Hjerteslaget stod paa den betalte API (14/9-2026)
#
# `heartbeat_model_provider = "deepseek"` i runtime.json. Hjerteslaget er det
# mest baggrundsagtige der findes i systemet, og det koerte paa Bjoerns betalte
# noegle. Rettet til ollama + `deepseek-v4-flash:cloud` — samme model, gratis,
# samme moenster som inner_enrichment-rettelsen 5/9.
#
# Vagten kunne ikke se det: hjerteslagets udbyder bor i runtime.json, ikke i
# provider_router.json som den kiggede i. Endnu et sted hvor sandheden om en
# lane ligger et STEDS ANDET end vagten spoerger.
# ─────────────────────────────────────────────────────────────────────────


def _indstillinger(monkeypatch, provider, model="m"):
    class _S:
        heartbeat_model_provider = provider
        heartbeat_model_name = model
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())


def test_hjerteslag_paa_BETALT_udbyder_er_et_brud(monkeypatch):
    """Den tilstand der faktisk stod i runtime.json."""
    _indstillinger(monkeypatch, "deepseek", "deepseek-v4-flash")
    brud = PLG.audit_heartbeat_provider()
    assert brud is not None
    assert brud["provider"] == "deepseek"


def test_hjerteslag_paa_ollama_er_rent(monkeypatch):
    _indstillinger(monkeypatch, "ollama", "deepseek-v4-flash:cloud")
    assert PLG.audit_heartbeat_provider() is None


def test_modelnavnet_alene_goer_det_ikke_betalt(monkeypatch):
    """`deepseek-v4-flash:cloud` PAA ollama er gratis. Doemte vi paa modellens
    navn, ville selve rettelsen se ud som bruddet — og en vagt der raaber op om
    sin egen loesning bliver slaaet fra."""
    _indstillinger(monkeypatch, "ollama", "deepseek-v4-flash:cloud")
    assert PLG.audit_heartbeat_provider() is None


def test_ULAESELIGE_indstillinger_frikender_ikke(monkeypatch):
    """Samme regel som den ulaeselige hovedbog: «jeg kunne ikke se efter» maa
    ikke blive til «alt er godt»."""
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    brud = PLG.audit_heartbeat_provider()
    assert brud is not None and brud.get("ukendt") is True


def test_fladen_baerer_hjerteslagets_udbyder(monkeypatch):
    _targets({"visible": ("deepseek", "deepseek-v4-flash", _PAID)}, monkeypatch)
    _hovedbog(monkeypatch, [])
    _indstillinger(monkeypatch, "deepseek", "deepseek-v4-flash")
    u = PLG.build_paid_lane_guard_surface()
    assert u["ok"] is False
    assert u["heartbeat_leak"], "hjerteslaget naar ikke ud paa fladen"
