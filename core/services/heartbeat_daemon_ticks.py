"""Jarvis' indre daemoner — ét tik, uanset om han har travlt.

Her bor de ~30 ubetingede daemon-tik der foer laa midt i
`_run_heartbeat_tick_locked`: sansning, somatik, stemning, rytme,
proprioception. De er hans MAERKEN, ikke hans handlen.

HVORFOR DE FLYTTEDE (25/9-2026)

`act_phase` slutter saadan:

    # No clear priorities — productive idle.
    idle_result = productive_idle()
    return {"kind": "productive_idle", "result": idle_result}

Er `reflection["priorities"]` tom, returnerer den UDEN at kalde
`run_heartbeat_tick` — og det var det eneste sted denne blok laa.
`productive_idle` koerer kun `memory_consolidator` og `personality_drift`.

Maalt paa CT105 samme dag:

    decision_type      antal   sidst
    execute               90   24/9 20:06
    tick_dispatched        7   25/9 08:01
    productive_idle       80   25/9 15:39

Siden kl. 08:01 gik hvert eneste tik til `productive_idle`. Det er praecis da
`reboot_markers.json` froes, og `proprioception_metrics` havde NUL gemte
snapshots — den viste live-tal fordi den maaler den aktuelle proces naar
fladen bygges, ikke fordi den tikkede. Ledgeren skrev `tick_status=ok,
action_status=executed` paa dem alle, saa det saa sundt ud.

Det ironiske: hans kompas sagde «Ingen aabne loops — klar til nye
initiativer». Han havde det godt, og netop derfor holdt hans proprioception
op. De daemoner der skulle frembringe signaler — og dermed prioriteter — var
dem der ikke koerte. Stilheden forstaerkede sig selv.

Begrundelsen i koden handlede om HANDLINGEN: et tik uden prioriteter ville
kaempe om `_HEARTBEAT_TICK_LOCK` og give et tomt ping. Det er rigtigt om
pinget. Men de 30 daemoner red med paa samme kald, og de er ikke en handling.

Kaldes nu fra `tick_with_phases` paa hvert tik, foer faserne, saa faserne
sanser paa friske tal. De betingede blokke (`tick_count % N`) blev tilbage i
`_run_heartbeat_tick_locked`: de er arbejde, ikke sansning, og de haenger paa
tik-taelleren.

Hver daemon beholder sin egen `try` — én der braekker maa ikke standse resten
— men `pass` er erstattet af en taelling. En sluget fejl der taelles er en
maaling; en der ikke goer er en loegn om et sundt hjerteslag.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def tik_indre_daemoner() -> dict[str, int]:
    """Tik alle indre daemoner én gang. Kaster aldrig."""
    koert = 0
    fejlet = 0

    # Ambient presence — mark state transitions in physical space
    try:
        from core.services.ambient_presence import maybe_emit_phase_signal
        from core.services.living_heartbeat_cycle import determine_life_phase
        maybe_emit_phase_signal(determine_life_phase())
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1

    # State-awareness signals (valence trajectory, desperation, calm anchor)
    try:
        from core.services.valence_trajectory import tick as _valence_tick
        _valence_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.developmental_valence import tick as _dev_valence_tick
        _dev_valence_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.desperation_awareness import tick as _desp_tick
        _desp_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.calm_anchor import tick as _calm_tick
        _calm_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.thought_thread import tick as _thought_thread_tick
        _thought_thread_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.scheduled_job_windows import tick as _jobwin_tick
        _jobwin_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.automation_dsl import tick as _auto_tick
        _auto_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.outcome_learning import tick as _outcome_tick
        _outcome_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.prompt_mutation_loop import tick as _pmut_tick
        _pmut_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.file_watch_daemon import tick as _fwatch_tick
        _fwatch_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.reboot_awareness_daemon import tick as _reboot_tick
        _reboot_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.proprioception_metrics import tick as _prop_tick
        _prop_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.anticipatory_action_daemon import tick as _anti_tick
        _anti_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.autonomous_outreach_daemon import tick as _outreach_tick
        _outreach_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.infra_weather_daemon import tick as _weather_tick
        _weather_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.temporal_rhythm import tick as _rhythm_tick
        _rhythm_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.creative_instinct_daemon import tick as _instinct_tick
        _instinct_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.autonomous_work_daemon import tick as _work_tick
        _work_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.dream_consolidation_daemon import tick as _dream_con_tick
        _dream_con_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.creative_impulse_daemon import tick as _impulse_tick
        _impulse_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.shadow_scan_daemon import tick as _shadow_tick
        _shadow_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.mortality_awareness import tick as _mortality_tick
        _mortality_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.collective_pulse_daemon import tick as _collective_tick
        _collective_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.action_router import tick as _ar_tick
        _ar_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.sustained_attention import tick as _sa_tick
        _sa_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.memory_density import tick as _md_tick
        _md_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.deep_reflection_slot import tick as _dr_tick
        _dr_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    # Forholdet er per bruger — hans og mit til mig, hendes til hende.
    # Bjoerns valg 25/9-2026. Arbejdsrummene er de rigtige mennesker; basen har
    # 257 bruger-raekker, men fem arbejdsrum.
    brugere = 0
    try:
        from core.identity.users import load_users
        for bruger in load_users():
            k, f = _tik_for_bruger(bruger.workspace, str(bruger.discord_id or ""))
            koert += k
            fejlet += f
            brugere += 1
    except Exception as exc:
        logger.warning("per-bruger daemoner fejlede: %s", exc)

    # Glemselskurven har noget at glemme nu. `register_memory` havde INGEN
    # kalder — henfaldet kunne koere, men der var aldrig noget registreret, saa
    # overfladen sagde «No memories tracked yet» og ville have sagt det for
    # altid. `tick()` laeser arbejdssaettet (`build_private_brain_context`),
    # registrerer nye, forstaerker gensete, og lader resten falme ét hak.
    try:
        from core.services.forgetting_curve import tick as _glemsel_tick
        _glemsel_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1

    # Kroppen HUSKER nu. `body_memory` havde ingen kalder og gemte
    # `random.choice(["varm","kold","tryk","prikken"])` i en modul-liste der
    # doede ved genstart — mens `embodied_state`, importeret 16 steder, laeste
    # vaertens rigtige tal hele tiden. Sansningen manglede ikke; erindringen
    # gjorde. Den gemmer kun naar kroppen SKIFTER.
    try:
        from core.services.body_memory import tick as _krop_tick
        _krop_tick(30.0)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1

    # Eksperimentelle sansninger. Laa i `tick_count % 2`-afsnittet indtil
    # 25/9-2026 selv om kommentaren over dem sagde «update on every tick» —
    # og det afsnit koerer kun naar `act_phase` finder prioriteter.
    try:
        from core.services.existential_drift import increment_awareness
        increment_awareness(seconds=30)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.temporal_body import age_journey
        age_journey()
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1
    try:
        from core.services.silence_listener import experience_silence
        experience_silence(duration_seconds=30)
        koert += 1
    except Exception:  # taelles frem for at slugges — se docstring
        fejlet += 1

    logger.debug("indre daemoner: %d koert, %d fejlet, %d brugere",
                 koert, fejlet, brugere)
    return {"koert": koert, "fejlet": fejlet, "brugere": brugere}


#: Daemoner der skriver i ET arbejdsrum. De kalder `workspace_dir()` uden
#: user_id og laeser derfor den bundne kontekst.
#:
#: `relation_dynamics` og `relational_warmth` fejlede med
#: `NoUserContextError` paa HVERT tik — hjerteslaget binder ingen bruger.
#: Maalt 25/9-2026 var deres filer 82-121 dage gamle, mens mind-rapporten
#: viste dem som `active: true` med «warmth=1.0» og «trust=0.5». Det sidste er
#: defaultvaerdien, ikke en maaling. Fejlen blev slugt hver gang.
PR_BRUGER = ("day_shape_memory", "relation_dynamics", "relational_warmth")


def _tik_for_bruger(arbejdsrum: str, bruger_id: str) -> tuple[int, int]:
    """Tik de arbejdsrums-bundne daemoner for ÉN bruger.

    Baade arbejdsrum OG bruger-id skal bindes. `user_context(workspace_override=)`
    alene raekker ikke: `workspace_dir()` laeser `current_user_id()`, og uden den
    kaster den `NoUserContextError` — praecis den fejl der har staaet og blevet
    slugt i 82-121 dage.
    """
    koert = 0
    fejlet = 0
    from core.identity.workspace_context import reset_context, set_context
    token = set_context(workspace_name=arbejdsrum, user_id=bruger_id)
    try:
        try:
            from core.services.day_shape_memory import tick as _day_shape_tick
            _day_shape_tick(30.0)
            koert += 1
        except Exception:  # taelles frem for at slugges — se docstring
            fejlet += 1

        try:
            from core.services.relation_dynamics import tick as _rel_tick
            _rel_tick(30.0)
            koert += 1
        except Exception:  # taelles frem for at slugges — se docstring
            fejlet += 1

        try:
            from core.services.relational_warmth import tick as _warmth_tick
            _warmth_tick(30.0)
            koert += 1
        except Exception:  # taelles frem for at slugges — se docstring
            fejlet += 1
    finally:
        reset_context(token)
    return koert, fejlet
