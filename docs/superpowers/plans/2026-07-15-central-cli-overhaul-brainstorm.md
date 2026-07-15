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
