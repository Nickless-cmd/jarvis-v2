# Moltbook observe-nerve — implementeringsplan

> **For agentic workers:** brug superpowers:subagent-driven-development eller inline. Steps med `- [ ]`.

**Goal:** En governed, observe-only Central-nerve for Jarvis' Moltbook-tilstedeværelse — grounded i den genskabte daemon.

**Architecture:** Én fil `core/services/central_moltbook.py` (rene detektorer + self-safe I/O), route, cadence-wiring, `jc`-verb. Mentions → Proaktivitets-broen (SP1). Skrive-lag udskudt.

**Tech Stack:** Python 3.11, urllib (som recovered daemon), core.eventbus, central_switches, ProducerSpec, route_proactive_notification.

---

### Task 1: Rene detektorer + tests (haiku-egnet, fuld kode)

**Files:** Create `core/services/central_moltbook.py` (rene dele), `tests/test_central_moltbook.py`.

Rene funktioner (ingen I/O):
- `classify_activity(home, activity, notifications) -> list[dict]` — normalisér de 3 kilder til
  `{kind: "feed"|"mention"|"reply"|"notification", id: str, author: str, snippet: str, created_at: str}`.
  Felt-mapping fra recovered daemon: activity-items har `id`/`post_id`/`author_name`/`author`/`title`/`content`/`created_at`;
  notifications har `notification_id`/`type`/`message`. snippet = `title`|`content`|`message` trunkeret 200 tegn.
- `new_since_seen(activities, seen_ids) -> list[dict]` — behold kun items hvis `id not in seen_ids`.
- `is_direct_mention(activity) -> bool` — True hvis `kind in ("mention","reply")` ELLER
  notification-`type` indeholder "mention"/"reply"/"comment".
- `cap_seen(seen_ids, new_ids, cap=500) -> set[str]` — union, behold nyeste (list-slice) ved overskridelse.
- `build_activity_summary(new_items) -> dict` — `{total, mentions, replies, feed, items: [{kind,author,snippet}][:10]}` (metadata-only).

Tests: hver funktion — classify normaliserer alle 3 kilder; new_since_seen deduper; is_direct_mention
skelner feed vs mention; cap_seen respekterer 500; summary er metadata-only (ingen fuld payload).

- [ ] Skriv tests (FAIL) → implementér → PASS → commit.

### Task 2: I/O-lag (Claude inline — fragil: API + bro + switch)

**Files:** Modify `core/services/central_moltbook.py`.

- `_load_api_key()` / `_call_moltbook_api(endpoint, api_key, timeout=15)` — kopiér verbatim-adfærd fra
  `docs/notes/2026-07-09-moltbook-daemon-recovered.py` (Bearer, User-Agent, 429/401/200; 401 → sentinel).
- `_owner_uid()` → `core.identity.owner_resolver.get_owner_discord_id()` (samme som SP1, IKKE settings.extra).
- `assess() -> dict` — load key (mangler → `{status:"no_api_key"}`); hent `home`+`activity_on_your_posts`+
  `notifications`; 401 på home → `{status:"unauthorized"}`; classify → new_since_seen → summary.
- `record_moltbook(*, trigger="cadence", last_visible_at="") -> dict` — kill-switch
  `central_switches.is_enabled("autonomy","moltbook")` (default ON), fejl→suppress (fail-safe);
  `assess()`; `unauthorized` → `central_switches.set_enabled("autonomy","moltbook", False)` (auto-disable);
  `central().observe({cluster:"channel", nerve:"moltbook", kind:"activity", count, mentions})` (metadata-only);
  cache summary+seen til kv `moltbook_state`; **direkte mentions → route via bro:** for hver mention
  `route_proactive_notification(_owner_uid(), "moltbook_mention", {text}, "normal")` (genbrug samme cap-sti
  som proactivity_bridge._route — pin under build: hvis `_route` er importérbar, brug den; ellers
  route_proactive_notification direkte). Self-safe hele vejen.

- [ ] Implementér → smoke-test import + `record_moltbook(trigger="probe")` med mocket `_call_moltbook_api`.

### Task 3: Cadence-producer + surface (Claude inline)

**Files:** Modify `core/services/central_moltbook.py`, `core/services/internal_cadence_central_wiring.py`.

- `register_moltbook_producer()` — `register_producer(ProducerSpec(name="moltbook", cooldown_minutes=360,
  visible_grace_minutes=0, run_fn=lambda **kw: record_moltbook(**kw), priority=<lav>))`.
- `build_moltbook_surface()` — assess friskt (route, ikke hot-path): sidste scan-tid (kv), ny-aktivitet-tæller,
  seneste tråde, `has_credentials`, switch-status, unauthorized-flag.
- Wire `register_moltbook_producer()` i `internal_cadence_central_wiring.py` (self-safe blok, som de andre).

- [ ] Implementér → smoke-test producer-registrering + surface-shape.

### Task 4: Route + jc + app-registrering (Claude inline)

**Files:** Create `apps/api/jarvis_api/routes/central_moltbook.py`; Modify `apps/api/jarvis_api/app.py`,
`apps/central_cli/central_cli/commands.py`.

- Route: owner-gated `GET /central/moltbook` → `build_moltbook_surface` (mønster som central_agent_smith.py).
- `app.py`: `include_router` (efter central_agent_smith).
- `commands.py`: `"moltbook": "/central/moltbook"` i `_GET_ENDPOINTS`.

- [ ] Smoke-test: route registrerer; `jc moltbook` mapper.

### Task 5: Fuld suite + deploy + live-verifikation

- [ ] Fuld suite grøn (kendte isolations-flakes alene).
- [ ] Push + deploy (bs@10.0.0.39, begge services, merge-not-overwrite).
- [ ] Live: `record_moltbook(trigger="probe")` mod ægte API (owner-samtykke — det er et eksternt kald på
  Jarvis' konto) → verificér observe + surface. Hvis nøgle udløbet → auto-disable virker.

**Note:** Live-kaldet i Task 5 er outward-facing (Jarvis' konto) → kør kun med Bjørns eksplicitte ja.
