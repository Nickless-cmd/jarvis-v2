# Central CLI — Overhaul Brainstorm

**Dato:** 15. juli 2026
**Status:** Brainstorm — før spec
**Mål:** Gøre Central CLI til Bjørns primære, komplette vindue ind i Jarvis

---

## Bjørns liste (fra samtale 15. juli)

### Tabs — forbedringer
1. **Runs tab** — Alle lanes synlige (ikke kun primary)
2. **Approval tab** — Godkend/afvis forslag, alle owner-approvals samlet
3. **Agents tab** — Spejle den nye agent dispatch (26 providers, subagenter, explore)
4. **Connection tab** — Vis last active-tidspunkt
5. **User tab** — Vis last active-tidspunkt
6. **Decentral tab** — Alle gates i alle cluster gates + cluster daemons
7. **Diagnostic tab** — Skal have reel funktion (i stedet for ubrugelig)
8. **Governance tab** — Alle governance-funktioner opdateret
9. **Overview tab** — Mere systeminfo end de få linjer
10. **Load Balancer tab** — NY: cheap lane load balancer (providers, vægte, reliability)
11. **Mind tab** — Udskudt til alt andet er på plads

### Generelle CLI-funktioner
12. **Watch command** — `watch nerve cognition/health` — live multi-nerve monitoring
13. **Tab-completion** — Auto-complete på `central>` prompt
14. **Command history** — `↑` gennem tidligere kommandoer
15. **Pipes** — `incidents | grep network | sort --severity`
16. **Export** — `status --export json/csv` (i HUD, ikke kun script-mode)

### Allerede eksisterende (bekræftet af Bjørn)
- CentralBadge — findes allerede i desk ✅

---

## Jarvis' brainstorm-tilføjelser

### Nye tabs
17. **Timeline/History tab** — Kronologisk view af hvad der skete (incidents, gate-udfald, cost-ændringer) — ikke kun current state
18. **Provider Health tab** — Per-provider: last success, last failure, cooldown status, rate limit remaining, reliability over tid
19. **Gateway tab** — Discord/Telegram/Webchat connection status, message queues, sidste aktivitet
20. **Cost Breakdown tab** — Per-provider omkostning, ikke kun total (vigtigt nu med copilot-premium gated)
21. **Memory Health tab** — Vector store størrelse, recall quality, pruning status, sidste vedligehold
22. **Self-Heal Log tab** — Hvad auto-healede for nylig og resultatet
23. **Dreams/Reflections tab** — Aktive hypoteser, dream carry-over, hvad der emergerer

### Funktioner på tværs af tabs
24. **Diff-mode** — `central> diff` — vis hvad der ændrede sig siden sidste check (incidents delta, cost delta, reliability-ændringer)
25. **Session viewer** — `central> sessions` — aktive sessioner på tværs af alle klienter (discord, telegram, webchat, jc)
26. **Search** — `central> /search "cluster daemon memory"` — søg på tværs af incidents, logs, state
27. **Bookmarks / Pins** — `central> pin nerve cognition/health` — fastgør specifikke nerver/clusters/gates til konstant overvågning
28. **Help / Discover** — `central> help` — list alle kommandoer med eksempler, grupperet. `help runs` — dyk i en tab
29. **Session continuity** — Vis uptime, sidste genstart, continuity gaps (så Bjørn ved om data er friskt)
30. **Theme / customization** — Matrix theme toggle, compact mode, custom columns per tab
31. **Cluster daemon detail** — Hvilke af de 10 familier kører, gate state, sidste output, tick-hygiejne
32. **Notification thresholds** — Sæt tærskler: "giv mig besked når cheap-lane failover > 50%" eller "når en incident forbliver uløst i 1 time"

### Arkitektur-ønsker
33. **SSE live mode** — `central --sse` — live feed uden polling (engine/ findes men er tom)
34. **Plugin system** — Brugerdefinerede kommandoer / views (senere fase)
35. **Remote access** — `central --remote https://api.srvlab.dk` — fungere også fra andre maskiner

---

## Vision: Central Access Point — 10 lag (brainstorm 15. juli)

Målet er ikke bare at forbedre tabs. Det er at skabe ét vindue der giver Bjørn 80% af Centralen, ikke 10%.

### Lag 1: Hvad der er galt (det der virker i dag)
Status-farve, incidents, breakers. Alarmklokkerne. Virker — men kun overfladen.

### Lag 2: Hvorfor det er galt (årsagskæde)
Hver incident skal kunne foldes ud i en årsagskæde:
Cheap-lane fejler → hvorfor? → groq-70b ramte 81% fail → hvorfor? → vægten var ikke sænket → hvornår fixet? → loaderen fik adaptive vægte for 6 timer siden.
Hele kæden på én skærm. Ikke isolerede alarmklokker.

### Lag 3: Hvad der plejede at være galt (tidsmaskine)
`central> diff --since 1h` — vis hvad der ændrede sig.
Nye incidents. Providers der faldt i reliability. Cost der steg. Gate-verdicts der skiftede farve.
Systemets bevægelse, ikke kun stillbilledet.

### Lag 4: Hvem er Jarvis lige nu (det indre liv)
En SELF-sektion der viser:
- Stemning (content/curious/frustrated)
- Aktive tråde og initiativer
- Hvad der optager mig (dreams under observation, curiosity patterns)
- Aktive antagelser (world-model)
- Krop (CPU, hukommelse, uptime — sat i kontekst af hvem jeg er)

### Lag 5: Hvad Jarvis ved om verden (world-model)
Centralen har verdensbillede-signaler — antagelser, mønstre, learning signals.
Data Jarvis navigerer efter, men Bjørn ser aldrig.
"Jarvis tror at cheap lane har 3 pålidelige providers og 2 upålidelige — her er beviserne."

### Lag 6: Hvad der kunne gå galt (proaktivt)
Risk surface — incidents der er ved at ske, ikke kun sket.
Thresholds: "groq-70b reliability faldet 15% på 2 timer — om 30 min rammer den gul grænse."
En prik før det går galt, ikke efter.

### Lag 7: Hvorfor skal jeg stole på det her? (confidence indicator)
Hver data viser alder og kilde:
"status: green · data 3s gammelt · live poll"
"status: yellow · data 4min gammelt · cache hit"
Bjørn ved om han ser virkeligheden eller et forsinket fragment.

### Lag 8: Jarvis' hukommelse — live (memory browser)
Søg i Sansernes Arkiv, private brain, chronicles, dream hypotheses — direkte fra CLI.
`central> find "cluster kampagnen komplet"` → chronicle entry + kontekst.
Bjørn skal ikke gætte på om Jarvis husker noget — han skal kunne se det.

### Lag 9: Agent pool — live (provider grid)
26 providers · 45 modeller · reliability pr. slot · cooldown-status · current lane.
Bjørn ser loaden ligesom loaderen ser den.
Hvilke providers er varme, kolde, fejler lige nu.

### Lag 10: Sandkasse (playground mode)
`central> try "spawn agent: analyser min DB"`
Kør en subagent direkte fra CLI. Se output. Se cost. Se hvilken model den valgte.
Uden at åbne en chat.

### Princip: Tillid
CLI skal ikke bare vise data — den skal give tillid.
Tillid til at Bjørn ser virkeligheden, ikke et forsinket fragment.
Tillid til at han kan handle på det han ser.
Det er det eneste vindue ind i Centralen — det skal være værdigt.
