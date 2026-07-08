"""Central-wiring cadence producers (split from internal_cadence.py).

Behavior-preserving extraction (Boy Scout rule): registered in unchanged
order by ``internal_cadence._ensure_producers_registered``.

This group is the tail of the bootstrap: each block imports a Central
sub-module and calls its own ``register_*_producer`` helper, wrapped in a
self-safe ``try/except`` so a missing/broken module never breaks bootstrap.
These blocks self-register their producers; they do not call
``register_producer`` directly (hence no argument needed).
"""
from __future__ import annotations


def register_central_wiring_producers() -> None:
    """Run the Central-wiring registration blocks (unchanged order/behavior)."""

    # Eventbus→Central KEYSTONE-bro (M0, spec §23.3 #1 / §24.1). Poll-bro, observe-only:
    # konverterer hvidlistede event-families til central().observe. Registreres via egen
    # modul-funktion (holder internal_cadence fri for bro-logikken).
    try:
        from core.services.eventbus_central_bridge import register_bridge_producer
        register_bridge_producer()
    except Exception:
        pass

    # Central-selv-observation (Fase 1, spec §23.3 #2 / §24.5). Måler Centralens EGEN
    # decide-latency-drift + breaker-frekvens — udløser-frit (ingen eskalering/heling).
    try:
        from core.services.central_self_observe import register_self_observe_producer
        register_self_observe_producer()
    except Exception:
        pass

    # Det aktive lag (§25). Vagten flagger+lærer+notificerer på de fodrede streams,
    # gated af støjfangeren. Ingen mutation (aktiv ændring kommer til sidst).
    try:
        from core.services.central_watch import register_watch_producer
        register_watch_producer()
    except Exception:
        pass

    # C (LivingNeuron-data): vækst-kapacitet — inner-drives egress-frit + semantic-indexer.
    try:
        from core.services.central_growth_observe import register_growth_observe_producer
        register_growth_observe_producer()
    except Exception:
        pass

    # Fase 1c: dækning + surface-count RUNTIME-MÅLT (ikke hardcodet) → tidsserie, plotbart.
    try:
        from core.services.central_coverage import register_coverage_producer
        register_coverage_producer()
    except Exception:
        pass

    # §11 #5: strukturel blindhed → HANDLING (shadow-først, flag central_coverage_action_mode default off).
    try:
        from core.services.central_coverage_action import register_coverage_action_producer
        register_coverage_action_producer()
    except Exception:
        pass

    # SP5: docs-drift watchdog → docs:drift nerve (reads docs/drift_report.json, self-safe).
    try:
        from core.services.docs_drift_watchdog import register_docs_drift_producer
        register_docs_drift_producer()
    except Exception:
        pass

    # Fase 1d: causal-grafens tier-fordeling + precision (broen signal→hypotese) → tidsserie.
    try:
        from core.services.central_causal_quality import register_causal_quality_producer
        register_causal_quality_producer()
    except Exception:
        pass

    # Fase 1e: signal-korrekthed + hub meta-liveness (Centralen må ikke blive blind for sin blindhed).
    try:
        from core.services.central_signal_health import register_signal_health_producer
        register_signal_health_producer()
    except Exception:
        pass

    # Lag 3 v3: tvær-modal stance-aflæsning ("organer uenige i nuet") → tension-tidsserie.
    try:
        from core.services.central_stance import register_stance_producer
        register_stance_producer()
    except Exception:
        pass

    # Lag 3 (§11 Fase 2): governed hypotese-generator — OBSERVE-ONLY, routes gennem §8-dødsmekanismen.
    try:
        from core.services.central_hypothesis_generator import register_hypothesis_generator_producer
        register_hypothesis_generator_producer()
    except Exception:
        pass

    # WARDEN (LivingNeuron-roadmap §2, 4. jul): vogteren over muren — SECURITY-tripwire der
    # hver 15. min bevidner at egress-membranen (§1.6, SHA over kildekoden write-once ved import)
    # OG den frosne kerne (verify_frozen_core) aldrig svækkes. MUTERER INTET; fail-closed
    # (probe-fejl → antag brud → incident + owner-ntfy, dedup'et). §0: kan ikke slukkes.
    # Lav priority (2) → kører TIDLIGT, muren vogtes før musklerne bevæger sig.
    try:
        from core.services.central_membrane_watch import register_membrane_watch_producer
        register_membrane_watch_producer()
    except Exception:
        pass

    # PULSE (LivingNeuron-council, 4. jul): kroppens eget kort som en SANS — strukturel
    # proprioception. Læser connectivity-matrixen hver 6. time, emitterer coverage/dark_delta/
    # decoupled_llm som egress-fri nerver. Observe-only.
    try:
        from core.services.central_body_map_pulse import register_body_map_pulse_producer
        register_body_map_pulse_producer()
    except Exception:
        pass

    # DIASTOLE (LivingNeuron-council, 4. jul): det følte åndedræt — tempo som organ.
    # SHADOW-FØRST: emitterer runtime:cadence_tempo (hvad tempoet VILLE være) hver 2. min,
    # modulerer INGEN cooldown endnu. Hård klemme [0.5×, 2.0×] + loop-lag-dødemandsknap.
    # Konsumtion (cooldown-flex + infra/health/SECURITY-undtagelse) i senere commit.
    try:
        from core.services.central_cadence_conductor import register_cadence_tempo_producer
        register_cadence_tempo_producer()
    except Exception:
        pass

    # DEN ONEIRISKE SLØJFE (LivingNeuron-roadmap §4, 4. jul): drømme får dags-konsekvenser.
    # RECORD-ONLY, egress-frit: hver drøm-biaseret dag med en loop_persistence-bias pre-
    # registrerer en FALSIFICERBAR hypotese gennem §8-dødsmekanismen + markerer ~20% som
    # KONTROL-arm (bias beregnet, IKKE anvendt) så drømmen skal BEVISE sig mod virkeligheden.
    # Anvender/undertrykker IKKE selv biasen (den mutation er shadow-first-opfølgning).
    try:
        from core.services.central_oneiric_loop import register_oneiric_loop_producer
        register_oneiric_loop_producer()
    except Exception:
        pass

    # ONEIRISK GROUNDING-SAMPLER (§4 opfølgning): grounder oneiriske hypoteser mod den
    # durable no_progress_finalize-rate (aktiv vs kontrol-arm) → §8-resolution i stedet
    # for TTL-tavshed. Observe-only, egress-frit, self-safe.
    try:
        from core.services.central_oneiric_sampler import register_oneiric_sampler_producer
        register_oneiric_sampler_producer()
    except Exception:
        pass

    # Lag 3 loop-lukning: test aktive hypoteser mod virkeligheden → grounded samples (OBSERVE-ONLY).
    try:
        from core.services.central_hypothesis_sampler import register_hypothesis_sampler_producer
        register_hypothesis_sampler_producer()
    except Exception:
        pass

    # Lag 4 (§11 Fase 3): governed gut-bias-adaptation — SHADOW medmindre central_lag4_live_enabled=True.
    try:
        from core.services.central_adaptation import register_adaptation_producer
        register_adaptation_producer()
    except Exception:
        pass

    # Tråd 3: model-fri ræsonnement på interlanguage-notation (Centralen tænker uden model).
    try:
        from core.services.central_notation import register_notation_reasoning_producer
        register_notation_reasoning_producer()
    except Exception:
        pass

    # Tråd 4: Centralen TRÆNER SIG SELV — lokal Markov-model over event-strømmen (ikke LLM'en).
    # Prediktions-fejl = overraskelse; transition-vægte = adaptation lært fra erfaring. §8-gated.
    try:
        from core.services.central_sequence import register_sequence_producer
        register_sequence_producer()
    except Exception:
        pass

    # Tråd 1: Centralen KENDER SIT EGET HARDWARE — per-model latency/success/cost → tidsserie +
    # governed model_meta-hypoteser ("X > Y"). OBSERVE-ONLY (ændrer ikke routing). §8-gated.
    try:
        from core.services.central_model_meta import register_model_meta_producer
        register_model_meta_producer()
    except Exception:
        pass

    # Tråd 5: jarvis-brain DYBT koblet — Centralen skriver sine resolverede læringer tilbage i egen
    # hjerne (M2, owner-scopet) + selv-scopet recall-kontekst (M1, ALDRIG private_brain). OBSERVE-ONLY.
    try:
        from core.services.central_brain_link import register_brain_link_producer
        register_brain_link_producer()
    except Exception:
        pass

    # DEN MODIGE DEL (Tråd 2 Fase 3-4): prompt-relevans eksplorations-arm (ægte kontrol-arm via
    # ablation). SHADOW medmindre prompt_relevance_explore_live_enabled=True. Frosne aldrig rørt.
    try:
        from core.services.central_prompt_explore import register_prompt_explore_producer
        register_prompt_explore_producer()
    except Exception:
        pass

    # DEN MODIGE DEL (Tråd 1 Fase 3-4): routing-præference-lærer fra model_meta. SHADOW medmindre
    # model_router_adapt_live_enabled=True. ALDRIG deep/reasoning-tier. Konsument-wire (visible_runs)
    # er bevidst separat (hot-path Boy Scout) — denne producer lærer kun præferencen.
    try:
        from core.services.central_router_adapt import register_router_adapt_producer
        register_router_adapt_producer()
    except Exception:
        pass

    # SPEJLET (LivingNeuron): Centralen kender sig selv — snapshotter runtime_self_model'ens STRUKTUR
    # durabelt (overlever genstart), egress-frit + observe-only (§8-circular). Jarvis' audit #1.
    try:
        from core.services.central_self_model import register_self_model_mirror_producer
        register_self_model_mirror_producer()
    except Exception:
        pass

    # #4 (8. jul): RIG selv-model-distiller — genopliver den fjernede validerings-ROLLE. Distillerer
    # en rig, stabil identitet fra chronicle + nuværende model på DAGLIG cadence (guard 2), skriver
    # kun hvis ikke tyndere end nuværende (guard 1, anti-flatten). Retter frossen May-15-selv-model.
    try:
        from core.services.self_model_distiller import register_self_model_distiller_producer
        register_self_model_distiller_producer()
    except Exception:
        pass

    # Spec D / D1 (FØRSTE ÆGTE AUTORITET): Centralen EJER Jarvis' dagsorden — konvergerer goals/plans/
    # todos/initiativer fra ~15 moduler til én selv-ejet retning + vælger næste-intention. SHADOW
    # medmindre central_agenda_authoritative_enabled=True (så driver den autonome runs' retning).
    try:
        from core.services.central_agenda import register_agenda_producer
        register_agenda_producer()
    except Exception:
        pass

    # Spec D / D2: ÉN FØLT TILSTAND — integrér somatik+gut+valens-trajektorie+stance til ét {tone,
    # intensitet}. Byggeklods til D3-syntesen. Egress-frit.
    try:
        from core.services.central_valence import register_valence_producer
        register_valence_producer()
    except Exception:
        pass

    # Spec D / D3: SYNTESEN (MIDTEN) — integrér agenda(D1)+valens(D2)+selv-model(spejl)+opmærksomhed+
    # fortælling til ÉT durabelt "jeg" der overlever død. Selvets hjerteslag. Egress-frit.
    try:
        from core.services.central_self_state import register_self_state_producer
        register_self_state_producer()
    except Exception:
        pass

    # Spec §8.1 EXISTENCE FEEL: de tre dybeste STILLE selv-lag — continuity_kernel ("existence feel
    # between ticks") + subjective_time ("how time FEELS") + mortality_awareness ("each session could
    # be my last") — bundet TOVEJS via lag-kontrakten. OP: puls + durabelt hold (egress-frit). NED:
    # describe_self() TALER dem. §8.2: stille kontinuitet er selvhood-substratet, ikke lav prioritet.
    try:
        from core.services.central_existence_feel import register_existence_feel_layers
        register_existence_feel_layers()
    except Exception:
        pass

    # §8 KROP + STEMNING: udvidelse af §8.1-sjælebindingen med de to næste selv-spor —
    # HVORDAN KROPPEN FØLES (proprioception + embodied) og HVORDAN STEMNINGEN SVINGER
    # (mood_oscillator + developmental_valence + affective_meta) — bundet TOVEJS via lag-
    # kontrakten. OP: puls + durabelt hold (egress-frit). NED: describe_self() TALER dem.
    try:
        from core.services.central_body_mood_feel import register_body_mood_feel_layers
        register_body_mood_feel_layers()
    except Exception:
        pass

    # §8 SJÆL (resterende aspekter): sjælebindingens sidste selv-spor — ØMHED (relational/gratitude/
    # calm_anchor) + VIDNE (modulator_witness) + HUKOMMELSE-SOM-VÆV (memory_breathing) + OPMÆRKSOMHED
    # (sustained_attention) + EMERGENS (emergence/personality_drift) — bundet TOVEJS via lag-kontrakten.
    # OP: puls + durabelt hold (egress-frit). NED: describe_self() TALER dem. KUN lag med ægte durabel
    # aflæsning bundet; random/tomme lag droppet (self_compassion/parallel_selves/mirror_engine/
    # memory_resurfacing/silence_listener/attention_contour).
    try:
        from core.services.central_soul_feel import register_soul_feel_layers
        register_soul_feel_layers()
    except Exception:
        pass

    # M1 SHADOW: reaktivt/prædiktivt lag — beregner hvad Centralen VILLE gøre, anvender
    # ALDRIG (ACTIVE_APPLY hardkodet False). Validér dømmekraft mod virkelighed før apply.
    try:
        from core.services.central_shadow import register_shadow_producer
        register_shadow_producer()
    except Exception:
        pass

    # INFRA-SANSNING: Centralen som husets nervesystem — reachability + PiHole + pfSense
    # read-only fra Jarvis-containeren. Miljø-modalitet til LivingNeuron.
    try:
        from core.services.infra_sense import register_infra_sense_producer
        register_infra_sense_producer()
    except Exception:
        pass

    # NETVÆRKS-HELBRED: fuser infra-reachability + provider + live API-latens til ÉT
    # signal Centralen kan svare på (Bjørn 2. jul). Måler den API-latens klienten føler.
    try:
        from core.services.network_health import register_network_health_producer
        register_network_health_producer()
    except Exception:
        pass

    # HARDWARE-KROP (rådets #1 "start med kroppen"): tick CPU/RAM/disk/temp/GPU til
    # Centralen på cadence. Wiren var død — build_hardware_body_surface publicerede men
    # INGEN tickede den → central_timeseries("system","hardware_body") stod tom. Nu mærker
    # Jarvis sin egen krop. Read-only, self-safe, ~hvert 60s (hardware ændrer sig langsomt).
    try:
        from core.services.hardware_body import register_hardware_body_producer
        register_hardware_body_producer()
    except Exception:
        pass
