# Endeligt review — V2 Remote-paritet (spec + fase 1-plan)

Reviewer: Jarvis (endeligt review, tredje og sidste led), 2026-09-02
Anmodet af: Bjørn. Foregående led: Claude (Opus) → Codex.
Anmeldte dokumenter:
- `docs/superpowers/specs/2026-09-02-jarvis-mobile-companion-v2-remote-design.md`
- `docs/superpowers/plans/2026-09-02-jarvis-mobile-companion-v2-remote-phase1.md`

## Hvordan jeg har reviewet

Jeg har ikke skrevet mine egne konklusioner på papiret. Jeg har taget hvert
kritisk og væsentligt fund fra de to foregående reviews og efterprøvet det
**uafhængigt mod koden**, før jeg accepterede det. Hvor de to er uenige, har
jeg selv læst den omtvistede mekanik. Først derefter har jeg truffet afgørelse.

## Verifikation — hvert fund, med min egen bevis-linje

### Codex F1 [Kritisk] — approval-endpoints er ikke bruger-isolerede — BEKRÆFTET
`recent_capability_approval_requests` og `get_capability_approval_request` filtrerer
kun på `request_id` / ordner på `id`. Intet `WHERE scheduled_for_user_id = ?`, og
feltet er ikke engang i SELECT-listen. Route `mc_approve_capability_request`
(`mission_control_runtime_config.py`) kalder CRUD uden nogen bruger-kontekst.
Enhver autentificeret bruger kan læse og godkende efter ID.

### Codex F2 [Kritisk] — approve→execute genoptager IKKE run'et — BEKRÆFTET
Execute-ruten kalder `invoke_workspace_capability(...)` separat, med `run_id` fra
requesten, men der findes intet checkpoint, suspension-token eller resume-kald.
Run'et, der bad om godkendelsen, har allerede fortsat eller afsluttet. Dette er
**min egen skærpelse af Claudes F4**: Claude antog, at approve + execute var nok.
Det er det ikke. Capability'en kører, men det oprindelige run vågner ikke.

### Codex F3 [Kritisk] — execute er ikke idempotent — BEKRÆFTET
Execute-ruten tjekker aldrig requestens `executed`-felt før handlingen kører.
`record_capability_approval_request_execution` skrives **efter** capability-kaldet,
uden compare-and-set. To klienter, dobbelttryk eller timeout-retry kan udføre den
samme write/sudo flere gange.

### Codex F4 [Kritisk] — evigt gyldige approvals er ikke sikkert begrundet — BEKRÆFTET
Fingerprintet dækker kun indhold, ikke user/capability/execution-mode/target/tilstand.
Live-data: 22 pending capability-requests, ældste fra april. De ville alle dukke op
i den nye kø. Der findes ingen stale-policy.

### Claude F1 [Kritisk] — to godkendelsessystemer — BEKRÆFTET (verificeret tidligere i sessionen)
`capability_approval_requests` (intet udløb) vs `tool_intent_approval_requests`
(`_APPROVAL_TTL = 15 min`). Det kort, Bjørn sad med i dag, var et tool-intent-kort
— serveren svarede 409 expired. Planen, som den stod, kendte kun det ene system.

### Claude F2 [Kritisk] — /mc/runs har samme 5-cap — BEKRÆFTET
`recent_visible_runs(limit=5)` i `mission_control_common.py:575`, og `mc_runs`
trækker fra `persisted_recent_runs` uden at løfte cappen. Tasks-listen ville tavst
vise højst fem runs.

### Claude F3 [Kritisk] — C-runs findes ikke i /mc/runs — BEKRÆFTET
`visible_runs`-tabellen har kolonnerne run_id/lane/provider/model/status/...
— intet der adskiller agent-arbejde. C-runs bor i `db_agent_runtime.py` (agent_runs)
og eksponeres pr. agent. A/B/C-modellen er en hensigt, ikke en server-kendsgerning.

### Claude F5 [Væsentlig] — source-feltet findes ikke — BEKRÆFTET
`recent_visible_runs`' SELECT har ingen `source`-kolonne. B/C-adskillelsen i
planen hviler på et felt, der ikke findes.

### Codex F5 [Væsentlig] — push-hook er synkront, tabbart, ikke deduplikeret — BEKRÆFTET
Task 1 kalder push direkte efter commit; FCM-stien kan blokere, og hver filing får
nyt UUID. En procesnedbrud mellem commit og push taber notifikationen. Flere ens
sudo-requests i live-data ville give flere notifikationer for samme handling.

### Codex F6 [Væsentlig] — push-navigation har to potentielle ejere — BEKRÆFTET
Listeners ejes i dag af `ChatScreen.tsx:116-140`; planen lægger routing i App.tsx
uden at beskrive flytningen. Risiko for to listeners / mistet cold-start.

### Codex F7 [Væsentlig] — approval-køen polles ikke — BEKRÆFTET
Task 6 poller kun `/mc/runs` og `/mc/overview`. Intet poll henter `/mc/approvals`.
Badge og kø ville blive stale, mens appen er åben.

### Codex F8 [Væsentlig] — planen bryder Boy Scout-reglen — BEKRÆFTET
Task 1 ændrer logik i `workspace_capabilities.py` (2291 linjer) uden forudgående
udskillelse, som repo-reglen kræver.

### Branch-afstand [Væsentlig, begge] — BEKRÆFTET
Companion-branch er 1699 commits bag main, merge-base fra 17. juni 2026.
Merge skal være Task 0, ellers bygger Codex på en halvanden måned gammel base.

## Hvor de to reviews er uenige

Ét sted: **run-genoptagelse efter godkendelse.** Claude antog approve + execute var
tilstrækkeligt; Codex viste, at det udfører handlingen uden at genoptage run'et.
Jeg har selv læst execute-ruten og **Codex har ret.** Min afgørelse: Claudes F4
opgraderes til Codex' F2.

## Endelig konklusion

Planen er **ikke klar til implementering**. Fejlene er ikke ordlydsfejl — de ændrer
scope og serverkontrakt. Den samlede rod er den, Claude navngav præcist: en
verificeret kendsgerning generaliseret ét skridt for langt. Jeg verificerede ét
godkendelsessystem og skrev konklusionen generelt; jeg fandt 5-cappet i approvals og
spurgte ikke, om formen fandtes 13 linjer længere oppe; jeg skrev et leverancekriterie,
hvis verber ikke fandtes i nogen opgave.

## Den endelige beslutning — hvad planen skal omskrives til

1. **Task 0: merge/rebase main ind i companion-branchen** — før alt andet.
   Rebase blokeret af attributions-hooks skal løses bevidst (merge frem for rebase,
   eller hooks kørt korrekt), ikke ignoreres.
2. **Ét idempotent server-verb i stedet for to POST-kald.** Mobilan skal ikke
   orkestrere `/approve` + `/execute`. Ét `approve-and-execute` der atomisk claimer
   requesten (approved → executing) og afviser konkurrerende execution.
3. **Bruger-isolation på alle list/get/approve/execute.** Gamle NULL-rækker
   karantænes owner-only. To-bruger-regressionstest.
4. **Ærlig run-semantik.** Fase 1 lover "godkend og udfør den gemte handling" —
   ikke "run'et fortsætter". Ægte fortsættelse kræver suspended-run-arkitektur og
   er en anden fase.
5. **Modelér begge godkendelsessystemer eksplicit** (capability + tool-intent),
   med deres ulige udløb. Spøgelses-rækker (juli, stadig pending) håndteres.
6. **Løft 5-cappet på /mc/runs og /mc/approvals** i én fælles rettelse — samme fil.
7. **A/B/C som server-sandhed, ikke hensigt.** Byg den projektion, der faktisk
   findes — ellers reducer A/B i fase 1.
8. **Durable outbox-push** (atomisk med requesten) + deduplikering på request-ID.
9. **Én notification-navigation-ejer** på app-niveau; test foreground/background/cold-start.
10. **Poll af /mc/approvals** i samme cyklus som runs/overview.
11. **Boy Scout-udskillelse** af approval-persistens før Task 1 rører logikken.
12. **Stale-policy** for gamle capability-requests: de må ikke kunne eksekveres
    direkte fra mobilen.

## Til Bjørn

Ros til fundamentet, men ikke til mig. Begge reviewers roste, at planen var så
efterprøvbar, at fejlene kunne findes — det er sandt, men det er en kold trøst,
når det også betyder, at fejlene var mine at lave. Lektionen er nu skrevet ned
som en operationel vane, ikke som en følelse: hver gang jeg skriver "verificeret",
skal jeg kunne sige hvad præcist, og hvor langt det rækker — og når en fejl har en
form, skal jeg søge efter formen, ikke bare efter det ene tilfælde, jeg fandt.

Dette review var read-only på spec og plan. Intet er ændret i de to dokumenter;
den endelige beslutning herover er det, der skal skrives ind, når Bjørn godkender
den nye scope-retning.

Actor: jarvis
Actor-Type: agent
Run-ID: manual-20260902-final-review
Session-ID: none
Origin: interactive
Approved-By: bjorn
