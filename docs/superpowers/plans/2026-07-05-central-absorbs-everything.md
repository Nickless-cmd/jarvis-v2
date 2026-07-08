---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Centralen absorberer ALT + MC-afvikling — Implementeringsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Python-miljø: `conda activate ai`.
> Deploy-mønster: commit → push → ssh 10.0.0.39 `git -C /media/projects/jarvis-v2 pull` (merge hvis Jarvis
> har committet) → `sudo systemctl restart jarvis-api` (+ `jarvis-runtime` ved daemon/registry-ændring).
> CLI kører lokalt på CheifOne (`pip install -e apps/central_cli`), verificeres via render-loop mod live-container.

**Goal:** Flyt AL Mission-Control-information ind i Centralen (som levende nerver) + surfacér i en 10-fane
Central-CLI, wire Jarvis' "selv" ind fra start, og afmontér MC per kategori efter e2e.

**Architecture:** Backend: nye `/central/*`-endpoints der PROJICERER eksisterende producent-services som
central-nerver (fuld behandling: nerve + trace + flag + notifikation + adaptive-learning). Runtime-proces-
tilstand (self/mind) læses via HTTP-proxy til 8011 (samme mønster som `mission_control_living_mind._proxy_
runtime_surface`). Privat indhold reduceres via en `feel`-lignende reducer (§24.4: liveness/tællere/
governance-konsekvens, aldrig rå indhold). CLI: 10 faner (T1-T10) oven på det eksisterende Textual-HUD +
altid-aktiv `central>`-terminal. MC fjernes kategori-for-kategori KUN efter e2e-verifikation.

**Tech Stack:** FastAPI (`/central/*` routes), core/services (central-nerver via `central().observe`),
Textual/Rich (CLI), httpx (proxy + CLI-klient), pytest, React/Electron (desk MC-fjernelse).

---

## Løste design-beslutninger (fra spec-self-review)

### C2 — Runtime-proces-tilstand læses via 8011-proxy
`central_hub._build_mind()` og de nye self/inner-life-buildere læser tilstand der KUN findes i
jarvis-runtime (port 8011). Når api kører api-only (`JARVIS_ENABLE_RUNTIME_SERVICES=0`) er in-process-
læsning tom. **Beslutning:** genbrug det beviste proxy-mønster fra
`apps/api/jarvis_api/routes/mission_control_living_mind.py::_proxy_runtime_surface`. Ny delt helper
`core/services/central_runtime_proxy.py::proxy_or_local(builder_name, local_fn)` der: (1) hvis
`JARVIS_ENABLE_RUNTIME_SERVICES` er sand → kald `local_fn()` in-process; (2) ellers HTTP-GET
`http://127.0.0.1:8011/internal/runtime-surface/{builder_name}` og returnér JSON. Self-safe (fejl → `{}`).

### §24.4 — Privat-reducer (feel-skabelon)
Nyt modul `core/services/central_private_reducer.py::reduce_for_owner(surface: dict, *, keep) -> dict`.
Beholder KUN: `liveness` (bool: kører den), tællere/magnituder (fx `trace_count`, `intensity`,
`last_fired`), og `governance_consequence` (hvad Centralen besluttede pga. signalet). DROPPER rå felter
(`recent_traces`, `current_focus`, `current_tool_plan`, `memory_precedents`, fritekst-indhold). Samme ånd
som `visible_inner_life.build_somatic_snapshot`. Alle self/inner-life-endpoints kører output gennem denne.

---

## Fil-struktur (nye + ændrede)

**Backend (core/services + routes):**
- Create `core/services/central_runtime_proxy.py` — proxy_or_local helper (C2).
- Create `core/services/central_private_reducer.py` — reduce_for_owner (§24.4).
- Create `core/services/central_absorb.py` — fælles "absorbér producent → central-nerve"-mønster
  (observe + trace + flag + notifikation + learning-hook) som hver kategori kalder. ÉT sted for "fuld behandling".
- Create `apps/api/jarvis_api/routes/central_self.py` — `/central/self` (living_executive/self_model/world_model, reduceret).
- Create `apps/api/jarvis_api/routes/central_mind.py` — `/central/mind?section=…` + `/central/inner-life` (syndikeret living-mind).
- Create `apps/api/jarvis_api/routes/central_absorb_routes.py` — `/central/agents`, `/central/council`,
  `/central/costs-daily`, `/central/queues/scheduled`, `/central/autonomy`, `/central/memory-health`, `/central/runs/{id}`.
- Modify `apps/api/jarvis_api/app.py` — mount de nye routers.
- Modify `core/services/eventbus_central_bridge.py` — udvid FAMILY_ROUTES med de 41 mørke familier (Fase B).

**CLI (apps/central_cli/central_cli):**
- Modify `datasource.py` — nye fetch+shape-funktioner pr. fane (agents/council/cost/queues/runs/self/mind/…).
- Modify `hud.py` — 10 faner (T1-T10), ét data-hook pr. fane (ingen dublet-kald).
- Modify `commands.py` — nye read-kommandoer pr. fane.

**Desk (apps/jarvis-desk) — Fase E, per kategori efter e2e:**
- Modify `src/lib/api.ts`, `src/lib/missionControlApi.ts`, `src/views/CoworkView.tsx` — fjern MC-forbrug.
- Delete MC-komponenter når alle kategorier er dækket.

---

## FASE 0 — CLI-skallen (10 tomme faner, synlighed fra dag 1)

Mål: de 10 faner findes og navigeres; ikke-endnu-wirede viser "venter på wiring". Bygger på det
eksisterende `hud.py` (som har 8 faner). Ingen backend-ændring.

### Task 0.1: Udvid tab-registret til 10 faner

**Files:**
- Modify: `apps/central_cli/central_cli/hud.py` (`_TABS`-listen)
- Test: `apps/central_cli/tests/test_hud_tabs10.py`

- [ ] **Step 1: Skriv den fejlende test**
```python
# apps/central_cli/tests/test_hud_tabs10.py
import pytest
from central_cli.hud import CentralHud, _TABS

def test_ten_tabs_in_order():
    keys = [k for k, _, _ in _TABS]
    assert keys == ["overview","nerves","clusters","incidents","runs",
                    "approvals","agents","mind","diagnostics","governance"]

@pytest.mark.asyncio
async def test_all_ten_tabs_show_without_crash():
    class FC:
        def get_json(self, p, params=None): return {} if "realtime" not in p else {"status":"green","coverage":{},"incidents":[],"open_breakers":[],"clusters":[],"feed":[]}
    app = CentralHud(client=FC(), live=False)
    async with app.run_test(size=(150,40)):
        for k,_,_ in _TABS:
            app.show_tab(k)
            assert app.active_tab == k
```

- [ ] **Step 2: Kør — forventet FAIL** (`_TABS` har kun 8, nye faner mangler)
`conda activate ai && python -m pytest apps/central_cli/tests/test_hud_tabs10.py -q`

- [ ] **Step 3: Implementér** — udvid `_TABS` i `hud.py` til de 10 (behold Overview/Nerves/Clusters/
Incidents; tilføj Runs, Approvals, Agents, Mind, Diagnostics, Governance; flyt Anomalies ind i Incidents-
fanens visning). Tilføj `_TABLE_TABS`/`_PANEL_TABS`-medlemskab + bindings (F1-F10 / tab-cycle dækker dem).
For endnu-ikke-wirede faner: `_render_placeholder_panel(name)` viser `— {label}: venter på wiring —`.

- [ ] **Step 4: Kør — forventet PASS.**

- [ ] **Step 5: Commit** `git add -A && git commit -m "feat(cli): 10-fane-registret (Fase 0)"`

### Task 0.2: Placeholder-render + nav for de nye faner
**Files:** Modify `hud.py` (`_populate_active_tab` grene for runs/approvals/agents/mind/diagnostics), Test `test_hud_tabs10.py`
- [ ] Step 1: Test at `show_tab("runs")` sætter side-paneh/panel til en "venter på wiring"-tekst uden crash (udvid testen ovenfor med assertion på panel-indhold via `str(app.query_one("#hud-panel").render())`).
- [ ] Step 2: Kør → FAIL. Step 3: tilføj grene der kalder `_render_placeholder_panel`. Step 4: PASS. Step 5: Commit.

### Task 0.3: Deploy + render-verificér Fase 0
- [ ] `pip install -e apps/central_cli`; render-loop-script (`app.run_test`→`save_screenshot` SVG→rsvg PNG→Read) mod live-container; verificér 10 faner navigerbare. Relaunch `central` på desktop (DISPLAY=:0). Commit intet nyt (verifikation).

---

## FASE 1 — Selvet + første kategori (agenter), fuld behandling

### Task 1.1: `central_runtime_proxy.proxy_or_local` (C2-helper)
**Files:** Create `core/services/central_runtime_proxy.py`, Test `tests/test_central_runtime_proxy.py`
- [ ] Step 1: Test:
```python
def test_local_when_runtime_enabled(monkeypatch):
    import core.services.central_runtime_proxy as p
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES","1")
    assert p.proxy_or_local("x", lambda: {"ok":1}) == {"ok":1}

def test_proxy_when_api_only(monkeypatch):
    import core.services.central_runtime_proxy as p
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES","0")
    monkeypatch.setattr(p, "_http_get", lambda name: {"ok":2})
    assert p.proxy_or_local("x", lambda: {"ok":1}) == {"ok":2}

def test_self_safe_on_error(monkeypatch):
    import core.services.central_runtime_proxy as p
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES","0")
    def boom(name): raise RuntimeError("nej")
    monkeypatch.setattr(p, "_http_get", boom)
    assert p.proxy_or_local("x", lambda: {"ok":1}) == {}
```
- [ ] Step 2: FAIL. Step 3: Implementér (læs env, `_http_get` bruger httpx mod `http://127.0.0.1:8011/internal/runtime-surface/{name}` med kort timeout; alt i try/except → `{}`). Mønster: kopiér `_proxy_runtime_surface` fra `mission_control_living_mind.py`. Step 4: PASS. Step 5: Commit.

### Task 1.2: `central_private_reducer.reduce_for_owner` (§24.4)
**Files:** Create `core/services/central_private_reducer.py`, Test `tests/test_central_private_reducer.py`
- [ ] Step 1: Test at rå felter droppes, liveness/tællere/governance_consequence beholdes:
```python
def test_drops_raw_keeps_meta():
    from core.services.central_private_reducer import reduce_for_owner
    surface = {"recent_traces":[{"impulse":"x"}], "current_focus":"hemmeligt",
               "trace_count":3, "liveness":True, "governance_consequence":"caution"}
    out = reduce_for_owner(surface, keep=("trace_count","liveness","governance_consequence"))
    assert out == {"trace_count":3,"liveness":True,"governance_consequence":"caution"}
    assert "recent_traces" not in out and "current_focus" not in out
```
- [ ] Step 2: FAIL. Step 3: Implementér (kun `keep`-nøgler + altid-droppede blokliste; self-safe). Step 4: PASS. Step 5: Commit.

### Task 1.3: `central_absorb` — fælles "fuld behandling"-mønster
**Files:** Create `core/services/central_absorb.py`, Test `tests/test_central_absorb.py`
- [ ] Step 1: Test at `absorb(cluster, nerve, value, *, flag_if)` kalder `central().observe` (trace), publicerer notifikation-event ved flag, og fodrer learning-hook:
```python
def test_absorb_observes_and_flags(monkeypatch):
    import core.services.central_absorb as a
    seen = {"obs":[], "pub":[]}
    monkeypatch.setattr("core.services.central_core.central", lambda: type("C",(),{"observe":lambda self,e:seen["obs"].append(e)})())
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", lambda k,p=None,**kw: seen["pub"].append((k,p)))
    a.absorb("cost","daily",{"usd":25.4}, flag_if=lambda v: v["usd"]>10, flag_reason="høj")
    assert seen["obs"] and seen["obs"][0]["cluster"]=="cost"
    assert any(k.endswith(".flag") for k,_ in seen["pub"])
```
- [ ] Step 2: FAIL. Step 3: Implementér: `observe` (fuld trace via central_timeseries), betinget flag → `event_bus.publish(f"{cluster}.flag", …)` + notifikation, og læringshook (`central_learning`-kompatibel key). Step 4: PASS. Step 5: Commit.

### Task 1.4: `/central/self` (living_executive + self_model + world_model, reduceret)
**Files:** Create `apps/api/jarvis_api/routes/central_self.py`, mount i `app.py`, Test `tests/test_central_self_route.py`
- [ ] Step 1: Test (owner-gated via `require_central_owner`; output kun reducerede felter; self-safe tomt ved ingen data). Step 2: FAIL. Step 3: Implementér: `require_central_owner()`; byg surface via `proxy_or_local` for `living_executive`/`runtime_self_model`/`world_model_signal`; kør gennem `reduce_for_owner`; `absorb("self", …)` så det bliver levende nerve. Step 4: PASS. Step 5: Commit + deploy + `curl /central/self`=200.

### Task 1.5: `/central/agents` (første MC-kategori, fuld behandling)
**Files:** Create/extend `central_absorb_routes.py`, mount, Test `tests/test_central_agents_route.py`
- [ ] Step 1: Test at `/central/agents` projicerer `agent_runtime.build_agent_runtime_surface` + `absorb("agent",…)`. Step 2: FAIL. Step 3: Implementér (owner-gated; projicér producent-service; absorb). Step 4: PASS. Step 5: Commit + deploy.

### Task 1.6: CLI T7 (Agents) + T8 (Mind & Self) datasource + render
**Files:** Modify `datasource.py` (`agents()`, `self_snapshot()`, `inner_life()`), `hud.py` (T7/T8 render), Test `test_hud_self_agents.py`
- [ ] Step 1: Test at datasource-funktionerne shaper `/central/agents` + `/central/self` og at T7/T8 renderer uden crash mod fake-klient. Step 2: FAIL. Step 3: Implementér (ét data-hook pr. fane). Step 4: PASS. Step 5: Commit.

### Task 1.7: e2e — selv + agenter live i CLI
- [ ] Deploy (api-restart); render-loop mod live-container: T7 viser ægte agent-roster, T8 viser selvets reducerede snapshot + inner-life. Verificér `absorb` skabte nerver (`jc nerve` / `/central/realtime` viser `agent:*`/`self:*`). Commit note i plan (afkryds Fase 1).

---

## FASE A — Resten af MC-kategorierne (per kategori, e2e-loop)

Hver kategori er ÉN leverance med loop'et **wire (absorb) → CLI-fane → e2e → FJERN MC-delen**. Fuldt
struktureret; hver udvides til bite-sized tasks (som Fase 1) når vi når den. Ingen springes over.

> **FREMSKRIDT 5. jul:** A1-A4 LANDET + e2e-verificeret live (screenshots). A1 cost-timeserie
> (`/central/costs-daily`, CLI cost skiftet fra /mc/costs, 7-dags-nedbrydning i Overview), A2 council
> (40 sessioner→Agents-header), A3 scheduled (→Runs-tab), A4 autonomy (20 forslag→Approvals-tab, flag fyrer).
> Commits f8146fee/33e395b9/83b091c7. UDESTÅR: A5 memory-health, A6 run-detalje, A7 events, A8 mind-sektioner.
> MC-delen (Fase E) IKKE fjernet endnu for A1-A4 — afventer eksplicit go (udadvendt/svær at fortryde).

- **A1 Cost-timeserie:** `/central/costs-daily` (projicér `ledger.daily_cost_summary`, absorb `cost:daily`,
  flag ved dags-stigning) → CLI T5-cost-afsnit → e2e → fjern `/mc/costs*` + desk CostPanel.
  Tests: shaping, flag-tærskel, tom-data, e2e-tal matcher `/mc/costs/daily`.
- **A2 Council:** `/central/council` (projicér `agent_runtime.build_council_surface`, absorb `council:*`) →
  CLI T7-council-afsnit → e2e → fjern `/mc/council*`. Tests: read-only observabilitet; action-POSTs gates separat.
- **A3 Scheduled-tasks:** `/central/queues/scheduled` (projicér `scheduled_tasks.list_pending`, absorb
  `queue:scheduled`) → CLI T5-afsnit → e2e → fjern `/mc/scheduled-tasks`. Tests: owner=alle-brugere-scope.
- **A4 Autonomy-proposals:** `/central/autonomy` (projicér `autonomy_proposal_queue`, absorb `autonomy:proposal`)
  → CLI T6-afsnit → e2e → fjern `/mc/autonomy/*`. Tests: approve/reject-flow bevaret.
- **A5 Memory-pipeline:** `/central/memory-health` (projicér `runtime_contract_candidates`+`daily_journal`,
  absorb `memory:pipeline`) → CLI T8-afsnit → e2e → fjern `/mc/memory-pipeline`.
- **A6 Run-detalje:** `/central/runs/{id}` (projicér `visible_runs`+events, absorb `run:detail`) → CLI T5
  drill-in → e2e → fjern `/mc/runs/{id}`. Tests: trin-tidslinje.
- **A7 Events/eventbus-feed:** `/central/events` (projicér eventbus, familie-filtre) → CLI T5 → e2e → fjern `/mc/events`.
- **A8 Mind-sektioner (I32/I34/I35/I36b):** `/central/mind?section=…` + `/central/inner-life` (syndikeret,
  via proxy_or_local + reduce_for_owner) → CLI T8 → e2e → fjern `/mc/*` living-mind + de dvale-projektioner.

---

## FASE B — Wire de 41 FRAKOBLET+LLM (parallelt fra start)

Struktureret; udvides pr. familie-batch. Mål: stop tabt signal; egress-fri observe.

> **FREMSKRIDT 5. jul (LANDET, a12d30c5):** 32 af de 41 mørke familier wiret (9 har ingen event-familie
> → dark-LLM-programmet). 11 operationelle→FAMILY_ROUTES (egress-OK), 21 private→PRIVATE_NO_EGRESS_ROUTES
> (trace-only). Klassificering ejet manuelt (leak-risiko), invariant-test styrket + verificeret live
> (11/11+21/21, FAMILY_ROUTES∩EXCLUDED=∅). Kræver restart af BÅDE jarvis-api OG jarvis-runtime. Note:
> taksonomi-lexikon-dækning faldt (nye operationelle familier = "ord-behov" til Bjørns ceremoni).
- **B1:** Test-harness der asserterer at en publiceret event i familie X nu rammer en central-route (via
  `eventbus_central_bridge`). **B2:** udvid `FAMILY_ROUTES` med batch 1 (dream_bias, user_model, desire,
  curiosity, conflict, absence). **B3:** batch 2 (meta_reflection, creative_drift, irony, user_temperature,
  counterfactual_engine, forgetting_runtime). **B4:** resten. Hver batch: absorb (fuld behandling) +
  `jc nerve`-verifikation + test at signalet ikke længere er dark. Ingen ny egress.

---

## FASE E — MC-afmontering (KUN efter e2e pr. kategori)

Per kategori når dens Central-vej er e2e-bevist: fjern MC-UI-panelet + `useMissionControl`-poll for
kategorien + de MC-routes der ikke længere har forbruger. Til sidst: slet `MissionControl.tsx`-faner der er
tomme, `mission_control*.py`-routes uden forbruger, og `/mc/runtime`+`/mc/jarvis`-aggregatorerne (de blev
aldrig gen-skabt i CLI). Verificér: intet desk-kald til fjernede routes (`grep /mc/` i `apps/jarvis-desk/src`),
ingen 404 i live-brug, backend-poll-hammer forsvundet (`jc series` viser fald i `/mc/*`-trafik).

**Løse `/mc/`-forbrugere at gen-pege FØR fjernelse:** `api.ts:611` (`/mc/cognitive-architecture`→`/central/mind?section=mind`),
`api.ts:618` (`/mc/overview`→`/central/realtime`+`/central/costs-daily`).

---

## NOTE — Næste program efter DENNE spec lander

> **Når hele denne spec er landet (MC afmonteret, alt i Centralen + CLI), er det NÆSTE program ALLE de
> mørke LLM-kald.** MC-fjernelse dræber poll-hammeren, men daemonerne kalder stadig LLM uafhængigt. Næste
> skridt: gør Centralen til det egentlige LLM-chokepoint — route al daemon-egress gennem
> `central_llm_egress` (shadow-observer findes allerede, jf. memory `reference_llm_economy_and_egress`),
> så Centralen *ved hvornår et kald faktisk er nødvendigt* (værdi-ændring vs. cadence-spam) og kan
> gate/cache/cheap-lane det. Det er hvor de spildte LLM-kald reelt stoppes. Egen spec + plan.

---

## Self-review (spec-dækning)
- 10 faner (T1-T10) ✓ (Fase 0 + Fase 1/A wirer indhold). Selvet fra start ✓ (Fase 1). Fuld behandling ✓
  (`central_absorb` = nerve+trace+flag+notif+learning, brugt af hver kategori). CLI-først ✓ (Fase 0 før wiring).
  MC-fjernelse kun efter e2e ✓ (Fase E-loop pr. kategori). C2-topologi løst ✓ (`central_runtime_proxy`).
  §24.4-reducer løst ✓ (`central_private_reducer`). Dark-LLM-note ✓. Ingen "gør vi senere" — alle faser committet.
