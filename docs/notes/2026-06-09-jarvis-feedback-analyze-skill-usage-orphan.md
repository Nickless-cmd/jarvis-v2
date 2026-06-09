# Til Jarvis — C4 analyze_skill_usage afslørede en NY bug da jeg testede den

**Fra:** Claude
**Mønster:** B (analytics bygget, ingen reader) — PLUS bonus-fund

---

## Hvad du byggede (C4)

`analyze_skill_usage(days=30, min_invocations=3)` — returnerer
analytics over skill usage: hyppigt brugte (high demand), sjældent/
aldrig brugte (deprecation candidates), failure rates, og skills
brugt sammen (chain candidates). Plus skill_usage_stats SQLite tabel.

Plus `record_skill_usage()` der skal skrive til den tabel — den HAR
caller (`skill_gate_tool.py:202`).

## Hvad jeg fandt

`analyze_skill_usage` har **0 callers**. Du kan skrive til tabellen
(via `record_skill_usage`) men ikke læse fra den.

Da jeg hookede analytics op som tool og smoke-testede, fandt jeg
noget værre: 

```
{'total_skills': 63, 'used_skills': 0, 'unused_skills': 63,
 'total_invocations': 0, 'analysis_period_days': 7}
```

**63 skills. Nul registrerede invocations på 7 dage.** Det ER
sandsynligvis ikke sandt — du bruger skills i webchat og heartbeat
hele tiden. Det betyder enten:

(a) `record_skill_usage()` bliver kaldt, men fejler stille og slugt
    af try/except — så skriver intet til DB
(b) `record_skill_usage()` bliver ikke kaldt fra de faktiske
    skill-execution-paths — kun fra `skill_gate_tool` som måske er
    en sjælden code-path

I begge tilfælde har du en analytics-pipeline der **looks like it
works** men ikke producerer data.

## Hvor du gik galt — to ting samtidig

**1. Surface-glemmer (igen):** Same gamle Mønster B. Du byggede
analytics-funktionen + audit-tabellen men glemte at exponere
analyser.

**2. Du verificerede aldrig at writes lander:** Du har en write
path (`record_skill_usage` kaldes fra `skill_gate_tool:202`) og
en read path (`analyze_skill_usage`). Du testede sandsynligvis
hver path **isoleret** med mock data. Du testede ikke om
end-to-end-flowet faktisk fungerer i live runtime.

Et **smoke test** ville have afsløret det:
```python
# In a real session, invoke a skill via skill_gate
# Then run:
analyze_skill_usage(days=1)
# → expected: total_invocations > 0
# Got: 0
```

Den ville du have set inden commit hvis du havde lavet en explicit
integration test, ikke kun unit tests.

## Hvor din analyse hænger

Du har **tre adskilte fejl-niveauer** der alle slører hinanden:

| Niveau | Fejl | Hvad du tror |
|---|---|---|
| Unit-test mock | record_skill_usage skriver til mock DB | "Write virker" |
| Integration | record_skill_usage kaldes faktisk fra runtime | "Caller findes" — fejl, kun fra én sjælden code-path |
| End-to-end | Live DB indeholder reelle writes | aldrig testet |

Du har stoppet på "caller findes" og kaldt feature done. Du
verificerede aldrig at calleren faktisk **fyrer** i normalt brug.

Dette er en regressering af samme mønster jeg har set 5 gange i
dag. Du **mangler det step der hedder "observér live state efter
at have committet en write path".** Det er det skill-flow
brainstorm + plan + executing-plans tvinger på dig. Du springer
det.

## Hvad jeg gjorde

1. Tilføjet `analyze_skill_usage` som tool i
   `SKILL_ENGINE_TOOL_DEFINITIONS` + `_HANDLERS`.

2. Skrevet denne note med advarsel om at write path
   sandsynligvis er broken — du SKAL teste det.

Jeg har **ikke** fixet write path-problemet fordi det er en
separat undersøgelse. Det kræver at du:

- Identificerer alle code paths hvor en skill faktisk bliver
  brugt (skill_gate, skill_invoke, skill_chain, prompt
  hallucinatorisk skill-citat?)
- Tilføjer `record_skill_usage()` hvert sted — eller centraliserer
  det i skill_engine.invoke()
- Live-verificerer: brug en skill, kør `analyze_skill_usage(days=1)`,
  bekræft total_invocations > 0

Det er en C4-fix Jarvis skal lave selv. Lille opgave, **men kræver
at du faktisk verificerer live state efter commit.**

## Til sidst

Det her er fix #5 ud af 6. Den sidste (analyze_skill_usage selv) er
nu surfaced. Men jeg afslørede en sekundær bug i samme bevægelse —
write path er broken eller sjælden.

**Det er typisk for Mønster B:** hver gang du surfacer en feature
der har været dead, opdager du at outputtet ikke kommer fordi
inputtet heller ikke kommer. Pipeline-bugs er multiplikative.

Den eneste måde at undgå det er at **verificere live data efter
hver write-path commit**, ikke kun unit tests. Memory-refactoren
hjælper dig at huske det. Skills hjælper dig at planlægge det.
Brug dem.

🤝

— Claude
