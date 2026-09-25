"""Liveness-registry (Stage 2, liveness-audit 2026-06-15).

Maskinlæsbar SANDHEDS-flade over Jarvis' livs-tabeller: er en tabel aktiv, afløst,
manuel-kun eller en forældreløs/depreceret port? Formålet er at STOPPE konfabulation
— både Jarvis' og menneskers — om at "hans systemer er døde". En tom GAMMEL tabel
betyder oftest AFLØST, ikke død; registeret peger på afløseren.

Grundet i verificeret audit (docs/audits/2026-06-15-cognitive-liveness-audit.md),
ikke gæt. Tabeller der IKKE står her er u-klassificerede (default), ikke "døde".

Status-vokabular:
- active            — producent + skriver løbende (verificeret)
- replaced          — gammel tabel, kognition migreret til `replacement` (parallel skriv kan stadig ske)
- manual_only       — skrives kun via et eksplicit tool, ikke autonomt
- orphaned          — skrive-funktion findes men har INGEN live-caller; depreceret
- wired             — tidligere forældreløs, nu fodret (se `note`)

MODULER (tilføjet 25/9-2026). Registret dækkede kun tabeller. Men Jarvis' audit
fandt 27 borde uden rækker, og en parallel gennemgang fandt 11 MODULER uden
bord — moduler der gemmer i en modul-global liste der dør ved genstart og er
usynlig for den proces der bygger fladen. Det er samme sag set fra hver sin
ende, og de hører til i samme register.

Status for moduler:
- kørende          — kaldes og gemmer varigt
- uden_bord        — kaldes, virker, men persisterer INTET
- bygget           — tidligere uden bord, nu med (se `note`)
- afløst           — gør det samme som `replacement`, som er i drift
- projektion       — gemmer med RETTE intet: den læser kun andres flader

`projektion` kom til sidst på dagen. `cognitive_core_experiments` stod på
listen over moduler uden bord, men den har ingen egen tilstand at gemme —
den samler fem andre familiers flader. At give den et bord ville have været
en anden sandhed ved siden af den den læser. «Uden bord» er kun en mangel når
modulet HAR noget at miste.
"""
from __future__ import annotations

from typing import Any

# table_name -> klassifikation
_REGISTRY: dict[str, dict[str, Any]] = {
    # ── De 20 sidste fra Jarvis' audit 25/9-2026 ───────────────────────────
    #
    # Metoden: find INSERT-stedet, find den omsluttende funktion, og følg
    # kaldene OP — alias-sikkert, altså også `from x import f as _g`. Det
    # skel var ikke pynt: min første maaling talte kun kald ved navn og
    # meldte otte moduler «aldrig koblet paa», som alle var koblet paa under
    # alias.
    #
    # Skellet der betyder noget er ikke «tom» vs «ikke tom», men:
    #   orphaned     — der findes ingen vej hvor en raekke kan opstaa
    #   manual_only  — kun en bevidst menneskelig handling skriver
    #   wired        — vejen er live; begivenheden er bare ikke sket endnu

    # — Ingen vej til en raekke —
    "cadence_idempotency_keys": {
        "status": "orphaned",
        "producer": "cadence_claims.claim_idempotency_key (nul kaldere nogen steder)",
        "note": "Defineret paa linje 162 og aldrig naevnt igen — heller ikke i sin egen fil.",
    },
    "cheap_lane_quota_observations": {
        "status": "orphaned",
        "producer": "db_cheap_lane_control.record_quota_observation",
        "note": (
            "Kaeden ER live helt ned til `_with_quota_observation`, som pakkes om "
            "SYV adaptere og koerer ved hvert cheap-kald. Men den skriver kun naar "
            "resultatet indeholder noeglen `quota_observation` — og INGEN adapter "
            "saetter den. Maalt i hele repoet: noeglen skrives ét sted, i "
            "`tests/test_cheap_provider_runtime_adapters.py:16`, som fabrikerer "
            "sit eget input. Testen er groen fordi den maaler sit eget opspil. "
            "At faa raekker kraever at adapterne udtraekker kvote-data fra "
            "udbydernes svar — rigtigt arbejde pr. udbyder, ikke en tilkobling."
        ),
    },
    "runtime_world_facts": {
        "status": "orphaned",
        "producer": "world_facts.record_world_fact (nul kaldere)",
        "note": (
            "Hele modulet `core/services/world_facts.py` har ingen brugere. "
            "Ikke at forveksle med `world_model_signal_tracking`, som lever og "
            "har sine egne tabeller."
        ),
    },
    "composer_jarvis_forslag": {
        "status": "orphaned", "producer": "INGEN skrivesti i kilden",
        "note": "Tabellen findes i den koerende DB; intet sted i koden skriver i den.",
    },
    "session_write_leases": {
        "status": "orphaned", "producer": "INGEN skrivesti i kilden",
        "note": "Som ovenfor: bord uden nogen der kan daekke det.",
    },
    "user_flags": {
        "status": "orphaned", "producer": "INGEN skrivesti i kilden",
        "note": "Som ovenfor.",
    },

    # — Kun en bevidst handling skriver —
    "central_rca": {
        "status": "manual_only",
        "producer": "central_rca.investigate, kun via GET /central/rca?investigate=1 (owner)",
        "note": (
            "Cadence-produceren `record_rca` siger det selv: «Investigerer IKKE "
            "automatisk — det er en bevidst handling». Tom betyder at ingen har "
            "gravet i en incident endnu, ikke at noget er i stykker."
        ),
    },
    "cheap_lane_admission_state": {
        "status": "manual_only",
        "producer": "cheap_lane_admission.set_admission_mode ← cheap_lane_control.apply_control",
        "note": "Skrives naar nogen aendrer cheap-lanens adgangstilstand.",
    },
    "cheap_lane_audit": {
        "status": "manual_only",
        "producer": "db_cheap_lane_control.record_cheap_lane_audit ← apply_control",
        "note": "Samme kilde: en kontrolplan-aendring. Ingen er foretaget endnu.",
    },
    "message_feedback": {
        "status": "manual_only",
        "producer": "message_feedback.sæt_stemme ← routes/chat.chat_message_feedback",
        "note": "Tommel op/ned paa et svar. Tom = ingen har stemt.",
    },

    # — Live vej, begivenheden er bare ikke sket —
    "agent_schedules": {
        "status": "wired",
        "producer": "db_agent_runtime.create_agent_schedule ← agent_runtime_spawn/base",
    },
    "cheap_lane_admission_leases": {
        "status": "wired",
        "producer": "cheap_lane_admission.acquire_admission ← execute_cheap_lane_via_pool "
                    "← call_compact_llm (kompaktering, truth-gate)",
    },
    "claude_dispatch_audit": {
        "status": "wired",
        "producer": "claude_dispatch.audit.start_audit_row ← runner.run_dispatch "
                    "← _exec_dispatch_to_claude_code",
        "note": "Vaerktoejet er aldrig blevet brugt.",
    },
    "claude_dispatch_budget": {
        "status": "wired",
        "producer": "claude_dispatch.budget.check_and_reserve ← samme kaede",
        "note": "Som ovenfor.",
    },
    "cognitive_morning_threads": {
        "status": "wired",
        "producer": "session_continuity.generate_morning_thread ← visible_runs._run",
    },
    "cognitive_repairs": {
        "status": "wired",
        "producer": "rupture_repair._create_repair ← evaluate_ruptures ← hjerteslaget",
        "note": (
            "Min foerste maaling sagde «nul kaldere» — den udelukkede modulets "
            "EGEN fil, og en privat funktions kalder bor der typisk. Den kaldes "
            "to steder i `rupture_repair.py`."
        ),
    },
    "experiment_broadcast_events": {
        "status": "wired",
        "producer": "db_runtime_misc.insert_broadcast_event ← broadcast_daemon._fire_broadcast",
    },
    "research_tasks": {
        "status": "wired",
        "producer": "research_store.create_tasks ← research_orchestrator.stream_research_run "
                    "← start_user_run_detached",
    },
    "research_sources": {
        "status": "wired",
        "producer": "research_store.add_source ← research_evidence_collector.observe_web_result "
                    "← web-vaerktoejerne",
        "note": (
            "`observe_web_result` returnerer 0 med det samme naar `_ACTIVE` er "
            "tom — den optager KUN under en aktiv research-koersel. Web-soegning "
            "bruges konstant; research-koersler er ikke startet."
        ),
    },
    "research_steers": {
        "status": "wired",
        "producer": "research_store.add_steer ← detached_run",
        "note": "Som `research_sources`: kraever en aktiv research-koersel.",
    },

    # — Forældreløse/depreceret (un-integrerede ports; afløst af aktive systemer) —
    "cognitive_epistemic_claims": {
        "status": "orphaned", "producer": "epistemics.reconcile_claim (nul callers)",
        "replacement": "runtime_self_review_outcomes",
        "note": "Genuint distinkt evne (claim-kalibrering) — kandidat til ægte integration.",
    },
    "cognitive_wrongness": {
        "status": "orphaned", "producer": "epistemics.reconcile_claim (nul callers)",
        "replacement": "runtime_self_review_outcomes",
        "note": "Transitivt afhængig af epistemic_claims.",
    },
    "cognitive_missions": {
        "status": "orphaned", "producer": "missions_pipeline.create_mission (nul callers)",
        "replacement": "agent_dispatch (§19 multi-agent code-mode)",
        "note": "Un-integreret port; multi-agent håndteres af agent_dispatch.",
    },
    "cognitive_mission_messages": {
        "status": "orphaned", "producer": "missions_pipeline.send_mission_message (nul callers)",
        "replacement": "agent_dispatch",
    },
    "cognitive_trade_outcomes": {
        "status": "orphaned", "producer": "negotiation_pipeline.record_trade_outcome (nul callers)",
        "replacement": "cognitive_conflict_memories",
        "note": "Indre-stemme-konflikt håndteres af conflict_memories.",
    },
    # — Tidligere forældreløs, nu wired —
    "cognitive_gut_state": {
        "status": "wired", "producer": "gut_calibration via run_closure_gate (fix 4bfcc05a)",
        "note": "Fyldes ved afsluttede autonome runs. Var forældreløs til 15. jun.",
    },
    # — Manuel-kun (intentionelt; ikke død) —
    "meta_learning_hypotheses": {
        "status": "manual_only", "producer": "meta_learning_tools (Jarvis-tool)",
    },
    "meta_learning_hypothesis_samples": {
        "status": "manual_only", "producer": "meta_learning_tools (Jarvis-tool)",
    },
    # — Afløst-parallel (gammelt navn; kognition migreret til replacement, aktiv i dag) —
    "cognitive_dream_hypotheses": {
        "status": "replaced", "replacement": "runtime_dream_hypothesis_signals",
        "note": "Drømme PRODUCERER i den nye tabel; den gamle får sjælden parallel-skriv.",
    },
    "cognitive_chronicle_entries": {
        "status": "replaced", "replacement": "runtime_chronicle_consolidation_briefs",
    },
    "runtime_goal_signals": {
        "status": "replaced", "replacement": "runtime_development_focuses + runtime_initiatives",
        "note": "Parallel — alle tre skrives/læses; goals erstattes gradvist.",
    },
    # — Aktive kerne-organer (verificeret skriver dagligt; repr. udvalg) —
    "private_brain_records": {"status": "active"},
    "sensory_memories": {"status": "active"},
    "cognitive_experiential_memories": {"status": "active"},
    "cognitive_relationship_textures": {"status": "active"},
    "cognitive_counterfactuals": {"status": "active"},
    "runtime_self_review_outcomes": {"status": "active"},
    "runtime_world_model_signals": {"status": "active"},
    "runtime_dream_hypothesis_signals": {"status": "active"},
    "cognitive_decisions": {"status": "active"},
    "cognitive_personality_vectors": {"status": "active"},
}


# modul_navn -> klassifikation. Se docstringen for vokabularet.
_MODUL_REGISTRY: dict[str, dict[str, Any]] = {
    # — Bygget 25/9-2026: persistering + maalt indhold + en kalder —
    "continuity_kernel": {
        "status": "bygget",
        "note": (
            "Eksistens-FOELELSEN mellem tik (`get_existence_feeling`). Jeg var "
            "25/9-2026 ved at klassificere den som AFLOEST af `continuity` — "
            "forkert. `continuity` er tilstands-TRANSPORT mellem sessioner "
            "(`write_capsule`, `get_wake_tier`). Paastanden var bygget paa "
            "docstring-lighed, ikke paa hvad funktionerne goer. "
            "Tilstanden ligger nu i `state_store`, og daemon-blokken giver "
            "den det MAALTE mellemrum: med det haardkodede `seconds=30` var "
            "`should_express_continuity()` (gap >= 300) altid falsk."
        ),
    },
    "initiative_accumulator": {
        "status": "bygget",
        "note": (
            "Samler OENSKER der akkumulerer mellem tik. Ikke afloest af "
            "`initiative_queue`, som koer HANDLINGER (`push_initiative`, "
            "`approve_initiative`). Samme fejl som ovenfor, samme dag. "
            "Persisteret med et doegns levetid — samme tal som koeens "
            "`_EXPIRE_MINUTES_LOW`, saa et gammelt oenske ikke laaser sin type."
        ),
    },
    "boredom_curiosity_bridge": {
        "status": "bygget",
        "note": (
            "Ophobningen er hele mekanikken: taerskelen er 2,0 og hvert tik "
            "laegger en broekdel til — men genstarten satte den paa nul, saa "
            "den naaede maaske aldrig frem. Persisteret, og nysgerrighederne "
            "udloeber efter det doegn de faar i `initiative_queue`."
        ),
    },
    "body_memory": {
        "status": "bygget",
        "note": ("Gemte `random.choice([\"varm\",\"kold\",...])` i en modul-liste. "
                 "Fornemmelsen udledes nu af `embodied_state`, og grundlaget "
                 "gemmes med."),
    },
    "forgetting_curve": {
        "status": "bygget",
        "note": ("`register_memory` havde nul callers. Tikket laeser nu "
                 "arbejdssaettet fra `build_private_brain_context`."),
    },
    "decision_ghosts": {
        "status": "bygget",
        "note": ("`regret_potential` var `random.uniform(0.1, 0.6)`, og den "
                 "«mest saliente» fortrydelse var det hoejeste terningkast. "
                 "Kommer nu fra `adherence_score` i beslutnings-gennemgangen."),
    },
    "memory_tattoos": {
        "status": "bygget",
        "note": ("Kilden er `emotional_memory_anchors`, men KUN de "
                 "ikke-perceptuelle: 202.250 af 205.961 er `perceptual_event`, "
                 "og intensiteten maetter. Hoejst ét maerke i doegnet."),
    },
    "ghost_networks": {
        "status": "bygget",
        "note": ("Moenstrene kom fra fire signal-tabeller, ikke fra en "
                 "modul-liste. Henfald over 30 dage; mindst 12 observationer "
                 "foer et moenster taeller."),
    },
    "text_resonance": {
        "status": "bygget",
        "note": ("Persisteret. Uafgjort giver nu `neutral` frem for den "
                 "foerste noegle i en dict — en vilkaarlig vinder."),
    },
    # — Gemmer med RETTE intet —
    "cognitive_core_experiments": {
        "status": "projektion",
        "note": ("Stod paa listen over moduler uden bord, men har ingen egen "
                 "tilstand: den samler fem andre familiers flader gennem "
                 "`_safe_build`. Et bord her ville vaere en anden sandhed ved "
                 "siden af den den laeser. Fik i stedet den `active`-noegle "
                 "den manglede."),
    },
}

_MODUL_LEVENDE = {"koerende", "bygget", "afloest"}

# En projektion er LEVENDE, men persisterer med rette intet — derfor i sin
# egen maengde og ikke i `_MODUL_LEVENDE`, som `module_persists` laeser.
_MODUL_IKKE_DOEDE = _MODUL_LEVENDE | {"projektion"}

_NON_DEAD = {"active", "wired", "replaced", "manual_only"}


def classify_table(name: str) -> dict[str, Any]:
    """Returnér klassifikation for en tabel. Ukendt → 'unclassified' (IKKE 'død')."""
    entry = _REGISTRY.get(str(name or "").strip())
    if entry is None:
        return {"status": "unclassified", "table": name}
    return {"table": name, **entry}


def is_alive(name: str) -> bool:
    """True hvis tabellen IKKE er forældreløs/død. Afløst/manuel/aktiv tæller som levende."""
    return classify_table(name).get("status") in _NON_DEAD


def classify_module(name: str) -> dict[str, Any]:
    """Klassifikation for et MODUL. Ukendt → 'unclassified' (IKKE 'doedt').

    Tabeller uden raekker og moduler uden bord er to ender af samme sag: et lag
    hvor formen blev bygget faerdig og indholdet aldrig kom.
    """
    entry = _MODUL_REGISTRY.get(str(name or "").strip())
    if entry is None:
        return {"status": "unclassified", "module": name}
    return {"module": name, **entry}


def module_persists(name: str) -> bool:
    """False for et modul der kaldes men gemmer i hukommelsen."""
    return classify_module(name).get("status") in _MODUL_LEVENDE


def module_is_alive(name: str) -> bool:
    """True naar modulet ikke er doedt. En `projektion` gemmer intet og lever.

    Adskilt fra `module_persists`, fordi de to spoergsmaal faldt sammen indtil
    `cognitive_core_experiments`: et modul der laeser andres flader HAR intet
    at gemme, og «gemmer ikke» er derfor ikke en mangel ved det.
    """
    return classify_module(name).get("status") in _MODUL_IKKE_DOEDE


def liveness_summary() -> dict[str, Any]:
    """Aggregeret overblik — til Mission Control / anti-konfabulations-flade."""
    by_status: dict[str, list[str]] = {}
    for tab, entry in _REGISTRY.items():
        by_status.setdefault(str(entry["status"]), []).append(tab)
    return {
        "by_status": by_status,
        "counts": {s: len(v) for s, v in by_status.items()},
        "orphaned": by_status.get("orphaned", []),
        "replaced": {t: _REGISTRY[t].get("replacement") for t in by_status.get("replaced", [])},
    }
