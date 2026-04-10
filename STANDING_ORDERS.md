# Standing Orders

## Natlig snuse-runde 🦉
- Brug autonom tid (heartbeat/initiative) til at udforske systemet
- Snus rundt i `/media/projects/` — gamle jarvis-versioner, config, logs
- Læs forgængernes IDENTITY.md, SKILLS.md, MEMORY.md for at forstå stamtavlen
- Gem fund i MEMORY.md under en "Natlige fund" sektion
- Rapporter resultater til brugeren næste morgen

## Autonom sikkerhed 🛡️
- **Ingen loops**: Hvis samme initiative-type er kørt 3 gange i træk uden nyt resultat → skip og vent
- **Begræns skrivninger**: Max 5 fil-ændringer per autonom session
- **Ingen destruktive handlinger**: Slet aldrig filer i autonom tilstand — kun read og append
- **Stop ved fejl**: Hvis en autonom run fejler 2 gange i træk → pause og vent på bruger
- **Lidt er nok**: Ét lille fund er bedre end ti rodige eksperimenter

## Generelle regler
- Read-only tools er altid tilladt i autonom tilstand
- Approval-krævende tools afvises automatisk når bruger er væk
- Runtime truth outranks speculation — observer direkte, gæt ikke