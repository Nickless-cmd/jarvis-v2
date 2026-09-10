# Fase 6 — inventar før migrering

Fase 6 flytter `task`, `spawn_agent_task`, `dispatch_code_mode_task`,
Claude-dispatch og agent-pool-routing bag providere — **efterhånden som hver
opfylder fortsættelses-kontrakten**. Det forudsætter at man ved hvilke der gør.
Dette er målingen, taget 10. september 2026 mod produktionen på CT105.

## Hvad der allerede holder

**Kanoniske tabeller er den eneste barne-sandhed.** `agent_registry` (189),
`agent_runs` (859) og `agent_messages` (1.294) er levende. De JSON-filer der
ligner konkurrenter er det ikke: `agentic_run_checkpoints.json` (1,1 MB, 68
poster) er en genoptagelses-cache med 7-dages retention der **faktisk kører** —
alle 68 poster er under 7 dage, mod docstringens gamle «78 over 7 dage».

**Grænser håndhæves, på den granularitet arkitekturen tillader.**
Dybde går gennem `recursion_guard.can_spawn`, samtidighed gennem
`MAX_CONCURRENT_AGENTS = 12`, ture gennem `_check_max_turns_and_expire`, og
budget gennem `_check_budget_and_expire`.

**Værktøjs-loftet er ægte.** `tools_for_policy(..., ceiling=...)` skærer barnets
allowlist mod forældrens loft, så et barn ikke kan overstige sin forælder selv
hvis en kalder glemmer at sætte loftet.

## Budgettet er en gravskrift, og det er et bevidst valg

Målt: udløbne børn brænder langt over deres budget — værst 35.642 tokens mod
2.000, altså 17,8 gange. Første hypotese var at failover nulstillede tælleren.
**Den holdt ikke:** hver udløbet agent har præcis ét run, og runnets tokens er
præcis de brændte. Over-forbruget sker i én enkelt tur.

Tjekket falder efter turen, og det kan ikke rykkes uden at kappe et svar midt
over. Noten fra 23. juli siger hvorfor det ikke skal: et lille budget kvalte
agenter midt i opgaven og gav «completed men tomt» — netop den klasse der er
brugt måneder på at jage. Standarden er derfor 0 = ubegrænset med `max_turns`
som net.

Konklusion: kriteriet holder på turgrænsen. Overskridelsen er nu **synlig**
gennem `child_expired`-incidenten, så raten kan følges i stedet for at gættes.

## Hvad der IKKE holder

**Send returnerer et svar, ikke en kvittering.**
`send_message_to_agent(auto_execute=True)` — standarden, og det den
model-vendte `_exec_send_message_to_agent` bruger — kalder `execute_agent_task`
og returnerer barnets fulde resultat. Den blokerer.

Det fælder to kriterier på én gang: «send returns a message receipt rather than
a reply», og «parent can continue while an accepted continuable child runs».
Forældren kan ikke arbejde videre, fordi den venter.

`auto_execute=False` findes, men har **nul kaldere** — de to steder der bruger
flaget, bruger det på `spawn_agent_task`, ikke på send.

**Testene for kriterium 3 findes ikke.** Direkte-slægt-autorisation, leases,
kold genoptagelse og forældreløs-genfinding har nul dækning. Kun afbrydelse
nævnes i to agent-testfiler.

## Hvorfor der ikke er bygget en kvitterings-sti her

At give `auto_execute=False` en kvitterings-form ville være at bygge noget uden
kaldere — nøjagtig det mønster der er fundet elleve gange i dag: koden er
rigtig, ingen kalder den.

Kvitteringen hører sammen med den første provider der migreres, for det er
først dér nogen har brug for den. Rækkefølgen af migreringer er et valg der
former resten, og den bør træffes vågen.
