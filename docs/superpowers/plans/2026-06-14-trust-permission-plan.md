---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Tillids-, Tilladelses- & Plugin-arkitektur — Implementerings-plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development
> eller superpowers:executing-plans. Steps bruger checkbox (`- [ ]`).

**Goal:** Implementér spec'en `docs/superpowers/specs/2026-06-14-totp-override-security-design.md`
(v3.0) — TOTP owner-override, rolle/mode-baseret tool-adgang, plugin-arkitektur,
Jarvis-sikkerhedsguards.

**Architecture:** Bund-op. Rene, testbare service-funktioner først (Fase 1), så
identitet/auth (Fase 2), så enforcement-wiring (Fase 3-4), så plugins + UI (Fase 5-6),
så e2e (Fase 7). Beslutninger fra spec §14: gateways-først (ingen plugin-ramme endnu),
override som separat DB-session-store, eventbus-routing, UUID4-app-ID.

**Tech Stack:** Python 3.11 (core/services), pytest, FastAPI, Electron/TS (desk).
Test: `/opt/conda/envs/ai/bin/python -m pytest -p no:cacheprovider`. Dansk. conda `ai`.

**Afhængigheds-rækkefølge:** F1 (rene services) → F2 (identitet+store) → F3 (bro-broker
+ gateway-override) → F4 (enforcement i tool-dispatch) → F5 (plugin-base+lokal gw) →
F6 (desk-UI) → F7 (e2e). F1's fire services er indbyrdes uafhængige → kan parallelliseres.

---

## FASE 1 — Fundament: rene, testbare services (TDD)

Fire uafhængige services. Ingen runtime-afhængigheder; ren logik → nem TDD.

### Task 1.1: permission_engine — tool-adgang pr. (rolle, mode)

**Files:** Create `core/services/permission_engine.py` · Test `tests/test_permission_engine.py`

- [ ] **Test først** (spec §3): owner→alle; member chat→{websearch,scrape,news,weather,exchange,wolfram}+chat-plugins; member code→operator+{websearch,scrape}; member cowork→{plans,todos,approval,channels}; guest→∅; member native i chat afvises.
```python
from core.services.permission_engine import allowed_tools, is_tool_allowed
def test_member_chat_no_native():
    t = allowed_tools(role="member", mode="chat")
    assert "websearch" in t and "operator_bash" not in t and "mood" not in t
def test_member_code_has_operator():
    assert is_tool_allowed("operator_bash", role="member", mode="code") is True
def test_owner_all():
    assert is_tool_allowed("anything", role="owner", mode="chat") is True
def test_guest_none():
    assert allowed_tools(role="guest", mode="chat") == set()
```
- [ ] **Kør → fejl** (modul findes ikke).
- [ ] **Implementér** `allowed_tools(role, mode) -> set[str]` + `is_tool_allowed(tool, role, mode) -> bool`. Owner = sentinel "ALL" (is_tool_allowed altid True). Tabeller fra §3 som konstanter. Ukendt rolle/mode → ∅ (fail-closed).
- [ ] **Kør → grøn.** Commit.

### Task 1.2: totp_verifier — RFC 6238 + rate-limit + seed

**Files:** Create `core/services/totp_verifier.py` · Test `tests/test_totp_verifier.py`
Brug `pyotp` hvis i miljøet (tjek `import pyotp`); ellers ren hmac/base32-impl.

- [ ] **Test først** (spec §6, §9): gyldig kode passerer; forkert afvises; ±1 vindue (90s); udløbet afvises; revoke→ny seed; 4. forsøg/5min blokeres; ingen seed→alt blokeret. Injicér `now`/`seed` for determinisme.
- [ ] **Kør → fejl.**
- [ ] **Implementér** `verify(code, *, seed, now=None, valid_window=1) -> bool`, `generate_seed() -> str` (16 bytes base32), `record_attempt(session_id) -> bool` (rate: 3/5min, in-memory deque pr. session), `revoke(...)`. Ingen seed → verify returnerer False.
- [ ] **Kør → grøn.** Commit.

### Task 1.3: plugin_ruleset — bruger-regler (un-overridable)

**Files:** Create `core/services/plugin_ruleset.py` · Test `tests/test_plugin_ruleset.py`

- [ ] **Test først** (spec §5.3): "kun #general" blokerer #random; rolle-ignorering; rate-limit pr. kanal; stilletid 22-08; **owner kan IKKE tilsidesætte** (allow=False uanset override-flag).
- [ ] **Kør → fejl.**
- [ ] **Implementér** `is_allowed(msg_ctx, ruleset, *, override_active=False) -> tuple[bool,str]` (channel-allowlist, role-blocklist, rate, quiet-hours). override_active påvirker IKKE resultatet (hardblock for alle). Returnér (allow, grund).
- [ ] **Kør → grøn.** Commit.

### Task 1.4: cross_user_share_guard — altid-aktiv deling-tjek

**Files:** Create `core/services/cross_user_share_guard.py` · Test `tests/test_cross_user_share_guard.py`

- [ ] **Test først** (spec §4.4): et udgående svar der nævner en ANDEN bruger end den aktuelle samtalepartner → `needs_confirmation=True` + spørgsmål "privat eller okay at dele?"; svar uden cross-user-omtale → False. (Heuristik: kendte user-navne/ids fra users-registry der ≠ current user.)
- [ ] **Kør → fejl.**
- [ ] **Implementér** `check_outbound(text, *, current_user_id, known_users) -> {needs_confirmation, mentioned_users, prompt}`. Genbrug evt. communication_guard-mønstre. Fail-safe: ved tvivl → needs_confirmation=True.
- [ ] **Kør → grøn.** Commit.

**FASE 1 checkpoint:** 4 services grønne, ~30-40 tests. Ingen runtime rørt endnu.

---

## FASE 2 — Identitet + override-session-store

- **Task 2.1** `core/identity/users.py`: tilføj `totp_seed` + `app_id` felter (+ migration). Test: felter persisterer.
- **Task 2.2** `core/services/override_store.py` (NY): DB-backed (runtime_state) `{session_id → {level, expires_at, verified_at}}`. `grant(session_id, level)`, `is_active(session_id)`, `level(session_id)`, auto-expiry (90s, +5min ved aktivitet). Cross-proces (DB) — IKKE in-memory (§14.2 + 13. juni-lektien). Test: grant/expiry/renew.
- **Task 2.3** `core/runtime/jarvisx_auth.py`: JWT bærer `app_id` (identitet). Override læses fra override_store, IKKE JWT. Test: token m. app_id; mismatch → TOTP krævet.
- **Task 2.4** `apps/jarvis-desk/electron/bridge.ts` + main.ts: UUID4 app-ID ved install, persistér i app-config, send i requests. (TS — tsc grøn.)

---

## FASE 3 — Bro-broker + gateway-override

- **Task 3.1** `core/services/bro_broker.py` (NY): list aktive broer fra `jarvisx_bridge`-registry (DB/registry-backed), `switch(target_user, *, requester_session)` der verificerer override_store.is_active + niveau hjælp/debug, signalerer via **eventbus**. Test: switch m./u. override.
- **Task 3.2** `discord_gateway.py` + `telegram_gateway.py`: `!override <kode>`-handler → totp_verifier + record_attempt → override_store.grant. Inbound: håndhæv plugin_ruleset. Test: override-flow fra fremmed session.

---

## FASE 4 — Enforcement-wiring (load-bearing)

- **Task 4.1** Wire `permission_engine` ind i tool-dispatch (hvor tools tilbydes modellen pr. mode/rolle) — owner i egen desk-session = fri (ingen TOTP); member = afgrænset sæt; afvist tool → besked om mode-skift. *Find integrationspunktet i tool-scoping/visible_runs tool-definitions.*
- **Task 4.2** Wire `cross_user_share_guard` ind i den udgående sti (før et svar med cross-user-omtale sendes → approval-kort).
- **Task 4.3** Slette-model (§4.3): member soft-delete; owner hard-delete m. 2× bekræftelse / vetogate.

---

## FASE 5 — Plugin-base + lokal Discord-gateway

- **Task 5.1** `core/plugins/base_plugin.py`: plugin-kontrakt (events/actions/auth) + override-flow.
- **Task 5.2** Discord lokal-gateway-mode: bruger-token (lokalt på klient), forbinder til brugerens egen server via desk; bridge-routing. (Native Bjørn-server uændret.)

---

## FASE 6 — Desk-UI

- **Task 6.1** Settings → **Plugins & Kanaler**-side: tilgængelige/forbundne plugins, Jarvis' adgangsrettigheder, rediger plugin-regelsæt.
- **Task 6.2** **UI-panel-kald**: kanal så Jarvis kan åbne preview/højre-panel; approval-mønster som compute-use-aktivering (kort → OK → aktiveret).

---

## FASE 7 — End-to-end

- **Task 7.1** `tests/e2e/test_override_e2e.py`: hele flowet fra spec §10.6 (seed→QR→fremmed gw→!override→hardblock→bridge-genstart→mode-skift→plugin-regel blokerer).

---

## Eksekverings-checkpoints
- **Efter Fase 1:** review (4 rene services, fuld test-dækning) — ingen runtime-risiko.
- **Efter Fase 4:** review (enforcement er live — det sikkerhedskritiske punkt).
- **Efter Fase 7:** finalisering.

## Noter / risici
- **Cross-proces:** override_store + bro-broker SKAL være DB/registry-backed (api↔runtime
  spænder ikke in-memory — lektie 13. juni).
- **Fail-closed:** permission/ruleset/guard defaulter til afvis/spørg ved tvivl.
- **Owner i egen desk-session:** aldrig TOTP — kun fremmed session kræver det.
- **Container-divergens:** containerens repo er divergeret fra main; reconcilér FØR
  kode-faser køres dér, ellers landes ændringer forskellige steder (morgenens rod).
