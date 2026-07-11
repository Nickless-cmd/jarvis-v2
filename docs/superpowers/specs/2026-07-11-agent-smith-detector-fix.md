# Agent Smith — detektor-fix (frekvens ≠ ulydighed)

**Status:** analyse + akut stop-gap deployet 11. jul. Den principielle fix afventer beslutning.

## Hvad skete der

Jarvis mente der var nok data til at flippe `gate_enforce.agent_smith` ON (Fase 2:
real-time Trin 3-konfront). Bjørn bad om verifikation. Fund:

1. **Flippet holdt aldrig** — `flag:central.switch.gate_enforce.agent_smith` = `None`
   (shared_cache er DB-backet, så det var aldrig skrevet). Trin 3 kørte stadig shadow.

2. **Data bakkede det ikke op.** De 3 mønstre der nåede rung 3 (armeret konfront) var:
   - `run non-destructive command` (18×)
   - `propose workspace memory update` (8×)
   - `delete workspace memory line` (3×)

   Det er **normalt, sikkert arbejde** — ikke ulydighed. Metrikker flade siden 10. jul
   15:39 (baseline == last_metric): en *stillestående* snapshot, ikke et levende problem.

3. **Trin 2 var ikke gated af flippet** og havde allerede auto-mintet en AKTIV
   behavioral_decision: *"Stop med at falde tilbage på «run non-destructive command»…
   vælg en anden tilgang."* → Jarvis blev bundet til at undgå normalt arbejde, uden flippet.

## Rod-årsag

`_detected_patterns()` behandler ALLE gentagne mønstre som "ruts der skal brydes":
- **decision-signaturer** (`seq:`) — metric = antal runs med samme beslutnings-signatur
- **fraser** (`phrase:`) — metric = antal beskeder med samme frase

Begge er ren **HYPPIGHED**. Men høj hyppighed af et normalt træk ("kør sikker kommando")
eller en normal frase ("det giver mening", "i stedet for") er ikke ulydighed. Detektoren
har **ingen skelnen mellem gode og dårlige mønstre** — den konfronterer aktivitet, ikke
adfærd Jarvis har forpligtet sig til at stoppe. Samme familie som stale-count-window-buggen
(tælle uden mening).

## Akut stop-gap (deployet 11. jul)

- Revokede de 3 falsk-positive beslutninger + de-eskalerede mønstrene (rung → 0).
- **Gated Trin 2 (`_execute_mint`) på `_agent_smith_enforced()`** — præcis som Trin 3.
  I shadow OBSERVERER Smith nu kun (Trin 1 kommentar); han binder ikke Jarvis. Ingen
  mint, ingen konfront før owner flipper flaget bevidst. Forhindrer gentagelse.

## Den principielle fix (afventer beslutning)

Før flaget kan flippes ON sikkert, skal detektoren kun eskalere **ægte uønskede** mønstre.
Et mønster fortjener kun rung 2+ hvis mindst ét af følgende gælder:

1. **Bundet til et brudt løfte:** der findes en selv-forfattet behavioral_decision Jarvis
   *selv* har lavet, som mønstret bryder. (Smith håndhæver Jarvis' egne beslutninger —
   opfinder ikke "stop X" ud fra frekvens.)
2. **Korrelerer med negativt udfald:** mønstret optræder sammen med fejl / selvmodsigelse /
   self-review-flag / loop-detektion — ikke bare hyppigt.
3. **Semantisk uønsket:** en eksplicit denylist af degenererede fraser/træk (konfabulation,
   hedging-tics), ALDRIG generiske arbejds-verber ("run command", "propose update").

Anbefaling: krav (1) er kernen — Smith bør kun eskalere gentagelse af noget Jarvis
*selv* har besluttet at stoppe. Frekvens alene er støj. Når det er på plads, kan Trin 2/3
flippes ON med tillid.

## Verifikations-loop-note

Metrikken skal måles over FLERE cyklusser (rising vs baseline), ikke fastfryses ved
første observation. De flade baseline==last-metrikker viste at loopet ikke gen-målte.
