# Streaming Gate Design

**Status:** Designstadie — Claude bygger ID-mængde-validering + non-blocking in-loop gates  
**Dato:** 2026-08-18  
**Autor:** Bjørn (krav), Claude (implementering), Jarvis (spec/feedback)

## Baggrund

Jarvis fabricerede et tool-kald i en tur (18. aug 2026) — skrev inline tekst der lignede `([tool_result:tool-result-...])` og præsenterede falske resultater som sandhed. Post-hoc fangst (efter runden) fungerer ikke: løgnen når brugeren før den fanges.

## Bjørns krav

> "Det burde faktisk være sådan realtime for alle vores gates så de aldrig afbryder en tur, men fanger realtime, korrigere og advare og ved forsættelse eskalere. Men aldrig ender et rund uden det virkelig er nødvendigt."

## Designprincipper

1. **Realtime** — gates evaluerer token-strømmen løbende, ikke post-tur
2. **Non-blocking** — korrektion indsættes midt i genereringen, runden fortsætter
3. **Synlig i klienten** — brugeren kan se når en gate griber ind
4. **Eskalering** — kun ved fortsatte brud efter korrektion/advarsel
5. **Afbryd kun når nødvendigt** — runden dræbes kun som sidste udvej

## Arkitektur

- **ID-mængde-validering** — hvert tool-kald har et ID; runtime verificerer at inline "tool-resultater" matcher et ægte eksekveret kald
- **In-loop gates** — gates kører inde i genererings-loopet, ikke som post-hoc auditor
- **Klient-synlighed** — gate-interventioner vises i klienten som runtime-noter, ikke skjultes i logs

## Status

Claude bygger: ID-mængde-validering + non-blocking in-loop gates synlige i klienten.
Jarvis spec: se docs/inner-life/streaming-gate-design.md (denne fil).