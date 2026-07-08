---
status: forældet
audited: 2026-07-08
ground_truth: "1) Verified multi_signal_recall WAS wired (bd1b1667 June 9, appeared in prompt_contract.py at d9ddbde7 time); doc claims "aldrig wired" = INACCURATE. 2) Auth fail-opens (tool_scoping/abuse_monitor) correctly identified and fixed same day in 75077711 (16:19); exceptions now log wa"
superseded_by: core/services/central_catalog.py (authoritative nerve registry); core/services/gate_privacy.py; core/services/gate_auth.py; core/services/gate_memory.py (implementations of findings)
---
# Fit-pass: Memory, Privacy🔒, Auth🔒 (2026-06-22)

Sidste tre clusters → central_catalog. Hermed er alle 8 navngivne clusters kortlagt
(47 nerver). Privacy + Auth migreres SIDST med fail-closed paritet.

## Memory (observabilitet, GateClass.COGNITIVE)
INGEN request-path-gates — pointen er TRACE, ikke enforcement (clusteren findes fordi
memory fejler stille). Recall/promotion = instrument, skrivning = leave.
Nerver: memory_write/embed (jarvis_brain), memory_search, memory_unified_recall
(memory_recall_engine), memory_candidate_promotion (candidate_workflow), memory_distill
(session_distillation), memory_associative_recall.
- **Stille fejl (kernen):** recall-kilder returnerer tomme lister ved fejl → **prompten
  bygges UDEN memory og bruger/Jarvis mærker intet** (memory_recall_engine ~261/332/341,
  prompt_sections/memory_recall.py 58/81/120, jarvis_brain build-section 26-27).
  Promotion: candidate-backlog vokser stille hvis auto-apply fejler.
- **Bonus-fund:** `multi_signal_recall` er bygget+testet men ALDRIG wired ind i
  prompt_contract (kode-note ~1318). Kandidat til at aktivere (egen opgave).

## Privacy🔒 (SIKKERHED, fail-CLOSED, GateClass.SECURITY)
Fit-pass-resultat: **ALLE nerver fejler closed (deny)** — strukturelt sundt. 3 request-
path-gates = merge (kun med fail-closed paritet): cross_user_share, visibility_ceiling,
brain_recall_gate. Crypto/scoping/kø = leave: share_guard_store, workspace_encryption
(AES-256-GCM, KEK/DEK), private_brain_scoping.
- **ÉT stille fejl-hul:** `visible_runs.py:~3817` record_pending `except: pass` — hvis
  pending-share-beslutningen ikke registreres, kan session fortsætte med delt data uden
  spor. Trace-kontrakten skal attache her (WARN, ikke silent).

## Auth🔒 (SIKKERHED, fail-CLOSED, GateClass.SECURITY)
Kerne-gates fejler CLOSED: tool_scoping (203-243), permission_engine (kanonisk matrix,
ukendt rolle→tom sæt), override_command (TOTP). Bevidst fail-OPEN (sikkerhed ≠ selvmål-
DoS, dokumenteret): identity_guard, abuse_monitor, security_guard (lock-checks).
- **`simple_tools.py:3925` except:pass = BEVIDST defense-in-depth-backstop** (primær gate
  = model-tool-filteret FØR execute_tool). Bekræftet — ikke et hul. Konsistent med tidligere
  manuel læsning.
- **2 UTILSIGTEDE fail-opens noteret (verificér/luk i Auth-migrationen):**
  1. `tool_scoping.py:216-229` `_apply_computer_use_policy` except:pass → operator-tools
     filtreres ikke ved DB-fejl (backstop: permission_engine member-liste).
  2. `abuse_monitor.py:106-131` injection-scan exception → besked passerer uden scan.

## Status
Alle 8 navngivne clusters kortlagt i central_catalog (loop/truth/commit/review/
proactivity/memory/privacy/auth = 47 nerver). Restkategorien (Led-4, ucluster-bart)
er pr. definition ikke en katalog-sektion. Migrations-rækkefølge: kognitive først,
sikkerhed (Privacy/Auth) SIDST med fail-closed paritet på fuldt sikkerheds-fixtureset.
