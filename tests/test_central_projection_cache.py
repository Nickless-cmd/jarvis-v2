"""Poll-stormen: Centralens projektioner må ikke koste ét kald ét arbejde.

Målt 21. aug 2026 i TOMGANG (intet aktivt run): 1246 requests på 5 min, hvoraf
/central/costs-daily alene stod for 68,9s serverarbejde (359ms x 192) og
/central/realtime for 24,1s (78ms x 310). Samlet 32,7% af én kerne brugt
konstant på at besvare de samme spørgsmål.

Testene dækker de tre ting der kan gå galt med et plaster som dette: at det
ikke virker, at det cacher fejl, og at det lyver om friskheden.
"""
from __future__ import annotations

import time

import pytest

from core.services import central_projection_cache as cpc


@pytest.fixture(autouse=True)
def _clean():
    cpc.invalidate()
    yield
    cpc.invalidate()


class TestGrundlaeggende:
    def test_anden_kald_beregner_ikke_igen(self):
        calls = []
        prod = lambda: (calls.append(1), {"v": len(calls)})[1]
        a, age_a = cpc.cached("k", 60.0, prod)
        b, age_b = cpc.cached("k", 60.0, prod)
        assert len(calls) == 1, "produceren kørte to gange — cachen virker ikke"
        assert a == b
        assert age_a == 0.0 and age_b > 0.0

    def test_udloebet_ttl_beregner_igen(self):
        calls = []
        prod = lambda: (calls.append(1), len(calls))[1]
        cpc.cached("k", 0.01, prod)
        time.sleep(0.02)
        v, age = cpc.cached("k", 0.01, prod)
        assert len(calls) == 2 and v == 2 and age == 0.0

    def test_noegler_er_adskilte(self):
        cpc.cached("a", 60.0, lambda: "A")
        v, _ = cpc.cached("b", 60.0, lambda: "B")
        assert v == "B", "nøgler blandes sammen"

    def test_invalidate_prefix_rammer_kun_sit_eget(self):
        cpc.cached("central:x", 60.0, lambda: 1)
        cpc.cached("central:y", 60.0, lambda: 1)
        cpc.cached("andet:z", 60.0, lambda: 1)
        assert cpc.invalidate("central:") == 2
        assert cpc.stats()["keys"] == 1


class TestFejlHaandtering:
    def test_fejl_caches_ALDRIG(self):
        """Et enkelt uheld må ikke fryse et tomt svar fast i hele TTL'en —
        endpointet har sine egne self-safe fallbacks og skal have lov at
        prøve igen næste gang."""
        state = {"fail": True}

        def prod():
            if state["fail"]:
                raise RuntimeError("DB nede")
            return "godt svar"

        with pytest.raises(RuntimeError):
            cpc.cached("k", 60.0, prod)
        state["fail"] = False
        v, _ = cpc.cached("k", 60.0, prod)
        assert v == "godt svar", "fejlen blev cachet — svaret var frosset"

    def test_falsy_vaerdi_caches_stadig(self):
        """En tom liste er et gyldigt svar. Bruger implementeringen `if not
        value` som miss-signal, ville tomme dage koste fuld pris hver gang."""
        calls = []
        prod = lambda: (calls.append(1), [])[1]
        cpc.cached("k", 60.0, prod)
        cpc.cached("k", 60.0, prod)
        assert len(calls) == 1


class TestAerlighed:
    def test_alder_rapporteres_saa_HUD_kan_vise_den(self):
        cpc.cached("k", 60.0, lambda: "v")
        time.sleep(0.05)
        _, age = cpc.cached("k", 60.0, lambda: "v")
        assert 0.04 < age < 1.0, f"alderen var {age}s — HUD'en kan ikke vise sandheden"

    def test_stats_taeller_hits_og_misses(self):
        """Tællerne er globale for processen, så vi måler delta — ellers
        afhænger testen af hvad andre tests nåede først."""
        før = cpc.stats()
        cpc.cached("k", 60.0, lambda: 1)
        for _ in range(3):
            cpc.cached("k", 60.0, lambda: 1)
        efter = cpc.stats()
        assert efter["misses"] - før["misses"] == 1
        assert efter["hits"] - før["hits"] == 3
        assert 0.0 <= efter["hit_rate"] <= 1.0


class TestEndpoints:
    def test_ttl_er_sat_paa_begge_tunge_endpoints(self):
        from apps.api.jarvis_api.routes.central import _REALTIME_TTL_S
        from apps.api.jarvis_api.routes.central_absorb_routes import _COSTS_DAILY_TTL_S
        assert 0 < _REALTIME_TTL_S <= 5, "realtime skal stadig føles live"
        assert _COSTS_DAILY_TTL_S >= 10, (
            "costs-daily var 70% af belastningen — for kort TTL løser intet")

    def test_costs_daily_blokerer_ikke_event_loopet(self):
        """Den var `async def` men kaldte ledger blokerende: 343ms x 192 kald
        = ~66s frosset event-loop pr. 5 min. Det bidrog til loop-lag."""
        import inspect
        from apps.api.jarvis_api.routes import central_absorb_routes as car
        src = inspect.getsource(car.get_costs_daily)
        assert "asyncio.to_thread" in src, "blokerende DB-arbejde i event-loopet"

    def test_absorb_sker_kun_ved_miss(self):
        """absorb() SKRIVER til den WAL-DB runtime også bruger. Ligger den uden
        for produceren, skriver hvert eneste GET stadig."""
        import inspect
        from apps.api.jarvis_api.routes import central_absorb_routes as car
        src = inspect.getsource(car.get_costs_daily)
        build = src[src.index("def _build()"):]
        assert "absorb(" in build, "absorb ligger uden for cachen — GET skriver stadig"

    def test_cache_age_er_med_i_svaret(self):
        import inspect
        from apps.api.jarvis_api.routes import central_absorb_routes as car
        from apps.api.jarvis_api.routes import central as c
        assert "cache_age_ms" in inspect.getsource(car.get_costs_daily)
        assert "cache_age_ms" in inspect.getsource(c.central_realtime)


class TestSkema:
    def test_index_paa_created_at_findes(self):
        import inspect
        from core.runtime import db_schema
        src = inspect.getsource(db_schema)
        assert "idx_costs_created_at ON costs (created_at)" in src
        assert "IF NOT EXISTS" in src.split("idx_costs_created_at")[0][-60:]


class TestBlokerendeHandlers:
    """75 route-handlers var `async def` uden at awaite noget.

    FastAPI kører en `async def` handler DIREKTE i event-loopet; en almindelig
    `def` handler kører i dens threadpool. Alle 75 var altså synkront DB-arbejde
    der frøs loopet mens det kørte — /central/users alene 111ms x 100 kald pr.
    kvarter. Det er samme mekanisme som bidrog til loop-lag ved cutoffs.

    Testen scanner AST'en, så den fanger både en genindført `async` og en ny
    handler skrevet efter det gamle mønster.
    """

    def _blokerende(self):
        import ast
        import pathlib
        fundet = []
        root = pathlib.Path(__file__).resolve().parents[1]
        filer = sorted((root / "apps/api/jarvis_api/routes").glob("central*.py"))
        filer.append(root / "apps/api/jarvis_api/routes/chat.py")
        for p in filer:
            for node in ast.walk(ast.parse(p.read_text())):
                if not isinstance(node, ast.AsyncFunctionDef):
                    continue
                if not any(
                    isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and d.func.attr in ("get", "post", "put", "delete")
                    for d in node.decorator_list
                ):
                    continue
                body = ast.unparse(node)
                if "to_thread" in body:
                    continue
                if any(isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith))
                       for n in ast.walk(node)):
                    continue
                # Streaming-handlers SKAL blive async — de lever i loopet og
                # driver en generator; at gøre dem til `def` ville bryde SSE.
                if "StreamingResponse" in body or "yield" in body:
                    continue
                fundet.append(f"{p.name}:{node.name}")
        return fundet

    def test_ingen_async_handler_blokerer_event_loopet(self):
        blok = self._blokerende()
        assert not blok, (
            f"{len(blok)} handler(e) er `async def` uden await og uden to_thread — "
            f"de kører synkront DB-arbejde i event-loopet: {blok[:5]}")

    def test_users_er_cachet(self):
        import inspect
        from apps.api.jarvis_api.routes import central_users as cu
        src = inspect.getsource(cu.get_user_activity)
        assert "cached(" in src, "/central/users var 67% af belastningen efter costs-daily"
        assert "cache_age_ms" in src

    def test_users_ts_bygges_inde_i_cachen(self):
        """Et 9s gammelt snapshot må ikke bære et friskt tidsstempel."""
        import inspect
        from apps.api.jarvis_api.routes import central_users as cu
        src = inspect.getsource(cu.get_user_activity)
        build = src[src.index("def _build()"):src.index("surf, age_s = cached")]
        assert 'surf["ts"]' in build, "ts sættes uden for cachen — det lyver om friskheden"
