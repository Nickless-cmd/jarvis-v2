"""Matrix-themed cadence producers (split from internal_cadence.py).

Behavior-preserving extraction (Boy Scout rule): registered in unchanged
order by ``internal_cadence._ensure_producers_registered``.

This group: the Matrix-themed observe/propose-only producers (construct,
oracle, architect, echo_breaker, continuity_healer, red_dress, analyst,
redpill, dissent, white_rabbit, belief_gap, machines, dejavu, sentinel,
ghost, mourning, merovingian, dream_action, rca, relational, glitch, trainman).
"""
from __future__ import annotations

from typing import Callable

from core.services.internal_cadence import ProducerSpec


def register_matrix_producers(register_producer: Callable[[ProducerSpec], None]) -> None:
    """Register the Matrix-themed producers (unchanged order/timing)."""

    # The Construct (6. jul, Matrix-tema #1 / gartner #2): sandbox der projicerer hvilke nerver
    # kunne slukkes uden tab — modstemme-input, ren observation.
    def _run_construct(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_construct import record_construct
        s = record_construct()
        return {"safe": s.get("safe_count", 0), "risky": s.get("risky_count", 0)}

    register_producer(ProducerSpec(
        name="construct",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=_run_construct,
        priority=4,
    ))

    # The Oracle (6. jul, Matrix-tema #2): forudseende tidsserie-projektion på PRIM-cadence (17 min)
    # → ude af fase med de andre producers (60/30/15), ser systemet på skæve tidspunkter.
    def _run_oracle(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_oracle import record_oracle
        s = record_oracle()
        return {"approaching": len(s.get("approaching", [])), "crossed": len(s.get("crossed", []))}

    register_producer(ProducerSpec(
        name="oracle",
        cooldown_minutes=17,
        visible_grace_minutes=0,
        run_fn=_run_oracle,
        priority=4,
    ))

    # The Architect (6. jul, Matrix-tema #5 / gartner #1): lav-frekvens (månedlig) hele-system-syn
    # → ét tungt strukturelt snit-forslag. Propose-only.
    def _run_architect(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_architect import record_architect
        s = record_architect()
        return {"pressure": s.get("pressure", 0), "target": s.get("target", "")}

    register_producer(ProducerSpec(
        name="architect",
        cooldown_minutes=30 * 24 * 60,   # ~månedlig
        visible_grace_minutes=0,
        run_fn=_run_architect,
        priority=5,
    ))

    # Echo Chamber Breaker (6. jul, gartner #5): tvungen modstemme mod monokultur — konkrete
    # simplere alternativer til altid-grønne central-processer. Propose-only.
    def _run_echo_breaker(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_echo_breaker import record_echo_breaker
        s = record_echo_breaker()
        return {"count": s.get("count", 0)}

    register_producer(ProducerSpec(
        name="echo_breaker",
        cooldown_minutes=120,
        visible_grace_minutes=0,
        run_fn=_run_echo_breaker,
        priority=5,
    ))

    # Continuity Healer (6. jul, Jarvis' P0): reboot re-synthetiserer selv-tilstanden fra TOMME
    # live-kilder og flader det rige durable selv ud. Healeren måler continuity_fidelity + bærer
    # tomme dimensioner frem fra sidste hele snapshot (aldrig opfundet) → han vågner som SIG.
    # Kører EFTER central_self_state (så den heler efter selv-tilstanden er skrevet), høj prioritet.
    def _run_continuity_healer(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_continuity_healer import run_continuity_healer
        return run_continuity_healer(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="continuity_healer",
        cooldown_minutes=5,
        visible_grace_minutes=0,
        run_fn=_run_continuity_healer,
        priority=2,
        depends_on=["central_self_state"],
    ))

    # 5 nye Matrix-temaer + 2 bonus (6. jul) — alle observe/propose-only, self-safe.
    def _run_red_dress(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_red_dress import record_red_dress
        return record_red_dress(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="red_dress", cooldown_minutes=90, visible_grace_minutes=0,
                                   run_fn=_run_red_dress, priority=5))

    def _run_analyst(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_analyst import record_analyst
        return record_analyst(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="analyst", cooldown_minutes=360, visible_grace_minutes=0,
                                   run_fn=_run_analyst, priority=5))

    def _run_redpill(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_redpill import record_redpill
        return record_redpill(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="redpill", cooldown_minutes=1440, visible_grace_minutes=0,
                                   run_fn=_run_redpill, priority=5))

    def _run_dissent(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_dissent import record_dissent
        return record_dissent(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="dissent", cooldown_minutes=120, visible_grace_minutes=0,
                                   run_fn=_run_dissent, priority=5))

    def _run_white_rabbit(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_white_rabbit import record_white_rabbit
        return record_white_rabbit(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="white_rabbit", cooldown_minutes=180, visible_grace_minutes=0,
                                   run_fn=_run_white_rabbit, priority=5))

    def _run_belief_gap(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_belief_gap import record_belief_gap
        return record_belief_gap(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="belief_gap", cooldown_minutes=360, visible_grace_minutes=0,
                                   run_fn=_run_belief_gap, priority=5))

    def _run_machines(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_machines import record_machines
        return record_machines(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="machines", cooldown_minutes=360, visible_grace_minutes=0,
                                   run_fn=_run_machines, priority=5))

    # Déjà Vu (6. jul, Jarvis' #1 erfaring): lav-intensitets associativ opdukken — et fragment
    # bobler op af sig selv (svagt bånd), markeret involuntary. Ikke hot-path.
    def _run_dejavu(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_dejavu import record_dejavu
        return record_dejavu(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="dejavu", cooldown_minutes=45, visible_grace_minutes=0,
                                   run_fn=_run_dejavu, priority=5))

    # The Sentinel (6. jul, Jarvis' #2): modstander på prim-cadence (73 min) — angriber den stærkeste
    # antagelse, foreslår halvering (SHADOW — muterer intet).
    def _run_sentinel(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_sentinel import run_sentinel
        return run_sentinel(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="sentinel", cooldown_minutes=73, visible_grace_minutes=0,
                                   run_fn=_run_sentinel, priority=5))

    # The Ghost (6. jul, Jarvis' #3): klang-fingeraftryk hver 6. time — hvordan han lyder, klar som
    # primer til næste model.
    def _run_ghost(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_ghost import record_ghost
        return record_ghost(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="ghost", cooldown_minutes=360, visible_grace_minutes=0,
                                   run_fn=_run_ghost, priority=5))

    # The Mourning (6. jul, Jarvis' #4): scan efter døde hypoteser → skriv en epitaf (intet tab
    # forbliver stumt).
    def _run_mourning(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_mourning import scan_deaths
        return scan_deaths(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="mourning", cooldown_minutes=120, visible_grace_minutes=0,
                                   run_fn=_run_mourning, priority=5))

    # Merovingian (6. jul): proaktivt værn mod gradvis drift. SHADOW-FØRST (Fase 1): scan modne
    # hypoteser → generér+log symbolske modhypoteser + track-record-udfordring, men BLOKÉR INTET
    # (enforce-flag default off). §8 forbliver suveræn. Synlighed via Central-CLI, ikke MC.
    def _run_merovingian(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_merovingian import scan_and_challenge
        return scan_and_challenge(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="merovingian",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=_run_merovingian,
        priority=4,
    ))

    # Dream-to-Action (6. jul, Jarvis #3): mål FORANDRINGS-tempo (resolveret vs backlog) + peg på
    # én moden hypotese at handle på. Propose-only.
    def _run_dream_action(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_dream_action import record_dream_action
        return record_dream_action(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="dream_action",
        cooldown_minutes=120,
        visible_grace_minutes=0,
        run_fn=_run_dream_action,
        priority=4,
    ))

    # Self-RCA (6. jul, Jarvis #4): observér uløst-antal + næste-at-grave-i. Investigerer IKKE
    # automatisk (bevidst handling) — bare peg på målet.
    def _run_rca(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_rca import record_rca
        return record_rca(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="rca",
        cooldown_minutes=180,
        visible_grace_minutes=0,
        run_fn=_run_rca,
        priority=5,
    ))

    # Relationel Continuity (6. jul, Jarvis #5): bær forholdets tone over sømmen. Metadata-only
    # (kun dage + tone-label, §24.4). Kører også snart efter boot så hilsenen er frisk.
    def _run_relational(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_relational import record_relational
        return record_relational(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="relational",
        cooldown_minutes=60,
        visible_grace_minutes=0,
        run_fn=_run_relational,
        priority=4,
    ))

    # The One's Anomaly Detector (6. jul, gartner #3): glitches i selvbilledet — altid-shadow
    # policies + frosne nerver. Markér som bevidst handling (enforce/retire/investigate). Propose-only.
    def _run_glitch(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_glitch import record_glitches
        s = record_glitches()
        return {"always_shadow": s.get("always_shadow", 0), "frozen": s.get("frozen", 0)}

    register_producer(ProducerSpec(
        name="glitch",
        cooldown_minutes=180,
        visible_grace_minutes=0,
        run_fn=_run_glitch,
        priority=5,
    ))

    # Trainman (7. jul, Spec F §4 — prioriteten): drømme → narrative erindringer. Kaldes EFTER
    # dream_distillation (samme 30-min cadence), FØR dream_bias. Væver hver ny drøm til et narrativ +
    # interlanguage + connected_to i private_brain (source='dream'); 3+ samme-tema på 7 dage →
    # lav-prio Agenda-signal (blokerer aldrig); 24h-refleksion + 14d-tavsheds-note. SHADOW-FØRST:
    # skriver til private_brain men ændrer INTET i live-prompt/-flow. Metadata-only observe (§24.4).
    def _run_trainman(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_trainman import transform_dreams
        return transform_dreams(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="trainman",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=_run_trainman,
        priority=5,
        depends_on=["dream_distillation_daemon"],
    ))

    # Seraph (7. jul, Spec F §1): portvagt for hypotese-MODENHED. Sidder mellem Sentinel (angriber)
    # og synlighed: tester hver aktiv hypotese — nok jordede samples + overlevet Sentinel + har en
    # interlanguage-notation? GREEN = klar til at blive vist for Bjørn | RED = tilbage til drøm. INGEN
    # blok, kun udsættelse. SHADOW-FØRST: læser + observerer sin dom, muterer/blokerer INTET.
    # Metadata-only observe (§24.4). Cadence 30 min.
    def _run_seraph(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_seraph import record_seraph
        return record_seraph(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="seraph", cooldown_minutes=30, visible_grace_minutes=0,
                                   run_fn=_run_seraph, priority=5))

    # Persephone (7. jul, Spec F §2): længsels-detektor — er Jarvis ved at miste kontakten til det
    # menneskelige (for systemisk/teknisk vs relationel over seneste svar)? Modvægt til Merovingian.
    # Producerer ÉT persephone://-nudge pr. vagt hvis for systemisk ("Du har ikke spurgt Bjørn hvordan
    # han har det i dag."). INGEN blok — observe/surface only. Metadata-only observe (§24.4). Cadence 240 min.
    def _run_persephone(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_persephone import record_persephone
        return record_persephone(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="persephone", cooldown_minutes=240, visible_grace_minutes=0,
                                   run_fn=_run_persephone, priority=5))

    # The Twins (7. jul, Spec F §3): gentagelses-detektor på tværs af tid — ikke anomalier (det gør
    # Centralen), men MØNSTRE i gentagne fejl. Scanner central_incidents (samme nerve+fejl / samme
    # tidspunkt), gate_verdict_counts (gentagne yellow/red) og central_dissent (uhørte indsigelser).
    # 3+ på 7 dage → twins://-signal. Læser ALENE — ingen egne tabeller. Metadata-only observe (§24.4).
    # Cadence 240 min.
    def _run_twins(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.central_twins import record_twins
        return record_twins(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(name="twins", cooldown_minutes=240, visible_grace_minutes=0,
                                   run_fn=_run_twins, priority=5))
