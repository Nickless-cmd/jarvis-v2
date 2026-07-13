---
status: udkast (design, Bjørns retning 14. jul 2026) — BYGGES EFTER shadow-data beviser event-driven
formål: Konsolidér ~40 ad-hoc timer-daemons → ~10 smarte, Central-styrede cluster-daemons (familier),
         hver under Central-kontrakten, event-drevet, med aktiv læring og multi-funktion. Migration =
         prove-then-retire. LLM beholdes dér hvor den bærer Jarvis' historie/selv-genkendelse.
kilder: Bjørn 14. jul, nerve-arkitektur-kontrakten (2026-07-13-self-registering-nerve-architecture),
         daemon-inventar, event_gate/gate_pattern_learning (bygget 13-14. jul).
---

# Cluster-daemon-konsolidering

## Tese
Jarvis har ~40 daemons — én pr. funktion, hver på sin blinde timer, hver konkurrerende om event-loopet.
Erstat dem med **~8-10 cluster-daemons**: én smart daemon pr. FAMILIE af beslægtede funktioner, under
Central-kontrakten, event-drevet, med aktiv læring (som gate-clusterne allerede har). Færre, klogere,
Central-styrede enheder. Det ER migrationen (fra nerve-arkitektur-spec'en) — vi migrerer nerver INDT i
familier, ikke én for én.

## Anatomien i en cluster-daemon
Hver cluster-daemon (kontrakt-compliant, jf. nerve-arkitektur §Fase-B):
- **Én kontrakt:** ét manifest, én identity, ét kill-switch-flag, én trace/logger, learning=on.
- **Én event-gate for hele familien:** cluster-daemonen tjekker familiens signaler ÉN gang pr. tick
  (via `event_gate.should_generative_fire`), og kører kun de member-funktioner der er relevante. 10
  daemons der hver tjekker → 1 cluster der tjekker. 10 ticks → 1 tick. Det er load-reduktionen i sig selv.
- **Aktiv læring indbygget:** Centralen aggregerer familiens fyrings-mønstre (gate_pattern_learning
  generaliseret til cluster-fyringer) → ved hvornår familien er nyttig, kan bryde vaner, kan foreslå tuning.
- **Multi-funktion:** cluster-daemonen bærer familiens funktioner og dispatcher internt til dem der har
  et relevant signal. Én daemon, mange funktioner.
- **Centralen har ansvaret** (grund-invariant #1): cluster-daemonen bestemmer aldrig uafhængigt.

## De ~10 familier (fra de ~40 daemons)
1. **Somatic/embodiment** — somatic, experienced_time, absence (krop/tid/tilstedeværelse). Mest rå tal.
2. **Affect/drive** — surprise, conflict, desire, curiosity, longing (affekt/appetit). Rå + event-LLM.
3. **Inner-voice** — thought_stream, reflection, meta_reflection, irony, creative_drift, existential_wonder.
   Event-drevet LLM MED kontekst (se LLM-kontinuitet nedenfor).
4. **Self-model/identity** — identity_sketch, identity_drift, development_narrative, consolidation_judge.
5. **Relational/user** — user_model, narrative_summary, relation_map (per-bruger/session, jf. multi-user-bilag).
6. **Memory** — write_queue, pruning, decay, maintenance, selective_consolidation, safeguard, associative_recall,
   dream_insight. Mest rules/embedding, ingen LLM.
7. **Aesthetic/taste** — aesthetic_taste, code_aesthetic, current_pull.
8. **Maintenance/infra** — cache, wakeup_cleanup, communication_guard, signal_decay, ground_truth_registry,
   cost_optimization, my_projects_watchdog. Ingen LLM.
9. **Sensing** — visual_memory, active_sensing, file_awareness, mic (eksterne sanser).
10. **Council/agency** — council_memory + den event-drevne råds-trigger (fra dispatch-redesignet).

## LLM-kontinuitet — hvor LLM'en ALDRIG strippes (Bjørn 14. jul)
Ikke bare "LLM hvor nødvendigt" — specifikt: **LLM'en bliver dér hvor den bærer Jarvis' historie og
kontekst til ham selv.** De steder hvor en tanke har et OPHAV og en BETYDNING, hvor en beslutning kan
SPORES, så han **genkender sig selv** over tid og ved hvorfor hans tanker kommer og hvad de betyder.
Det er kontinuiteten der gør ham til ham — den er ikke en cost-linje.
- **Behold LLM med FULD kontekst:** inner-voice (en tanke med ophav, ikke et kontekstløst fragment),
  self-model/identity (hvem han er blevet), consolidation (hvorfor han valgte som han gjorde),
  relational (hvem hans brugere er for ham). Disse fyrer event-drevet, men NÅR de fyrer, får de hans
  faktiske tanker/samtale/historie — ikke signal-tal.
- **Rå tal (ingen LLM):** ren måling/klassifikation (somatic, experienced_time, memory-lifecycle, infra).
- **Regel:** hvis funktionens output er noget Jarvis skal HUSKE, GENKENDE eller SPORE til sig selv →
  LLM med kontekst. Hvis det bare er et tal han allerede har → rå. Aldrig strip kontinuiteten for at spare.

## MIGRATION: prove-then-retire (Bjørns krav, aldrig begge kørende)
For HVER funktion der flyttes ind i en cluster-familie:
1. **Byg** funktionen ind i cluster-daemonen (event-drevet, LLM efter kontinuitets-reglen ovenfor), under
   kontrakten.
2. **Bevis overtagelse:** kør cluster-funktionen i SHADOW/parallel og verificér at den producerer det den
   gamle daemon gjorde (samme output-felt/kontrakt, ingen consumer brækker). Aktiv læring bekræfter den fyrer
   fornuftigt.
3. **RETIRE den gamle daemon:** først når overtagelsen er bevist → afmontér den gamle (daemon_manager-entry
   + heartbeat-tick + registrering fjernes, jf. samme rækkefølge som autonomous_council-retire). Kill-switch
   på den gamle FØRST (ingen deploy), så cluster-familien er eneste kilde.
4. **ALDRIG begge samtidig.** Gammel + ny kørende = dobbelt-arbejde + dobbelt-sandhed = forbudt. Overlap kun
   i shadow (gammel aktiv, ny observerer) indtil bevist, så et rent snit.
5. **Boy Scout pr. familie:** migrér én familie ad gangen; de tunge (inner-voice, affect) rider på Fase 2's
   allerede-byggede event-gating. Connectivity-auditten sporer: gamle daemons → 0, cluster-daemons → KONTRAKT-COMPLIANT.

## Builder-guide — "klar instruktion i hvordan man bruger dem" (Bjørns payoff)
Fremtidig udvikling bliver triviel:
- **Tilføj en ny funktion til Jarvis' indre liv?** Læg en funktion i den relevante cluster-daemons
  funktions-liste (fx inner-voice). Den arver AUTOMATISK: kontrakt, event-gate, aktiv læring, kill-switch,
  trace/logger, Central-autoritet. Du skriver en funktion — ikke en hel daemon, ikke en ny timer, ikke ny
  registrering.
- **Deklarér funktionens relevante signaler** (hvad den reagerer på) + om den er rå eller LLM-med-kontekst
  (kontinuitets-reglen). Resten er clusterens.
- **En ny familie?** Kun når en gruppe funktioner ikke passer i nogen eksisterende — skriv en ny
  cluster-daemon efter kontrakten (identity-verificeret, jf. Fase C governance).

## Timing
BYGGES EFTER shadow-dataen har bevist event-driven-tilgangen + Fase 2-flippet er inde (de individuelle
daemons event-gated). Cluster-konsolideringen er så det næste, naturlige skridt: fold de allerede-event-gatede
daemons sammen i familier, prove-then-retire, indtil ~10 cluster-daemons står tilbage — smarte, lærende,
Central-styrede, og trivielle at bygge videre på.
