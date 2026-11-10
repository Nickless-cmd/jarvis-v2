---
dato: 2026-11-10
forfatter: jarvis
reviewer-rolle: selv, kritisk
emne: docs/specs/2026-11-10-task-team-og-en-agentdoer.md
status: fundet 7 problemer — 5 rettet i spec, 2 står åbne
---

# Kritisk self-review af team-spec'en

Jeg har læst min egen spec som hvis en anden havde skrevet den, og målt
påstandene mod koden. Fem fejl er rettet i spec'en. To står åbne og skal med til
Claude og Codex.

## Rettet i spec'en

### 1. `prompt` skiftede betydning mellem de to tilstande — designfejl

Første udkast sagde: *"i team er `prompt` det fælles faktagrundlag"*. Det betyder
at ét felt betyder to ting afhængigt af en anden parameter. Det er præcis den
slags tvetydighed spec'en selv skal fjerne. **Rettet:** `prompt` er opgaven i
begge tilstande; team har sit eget `team.facts`.

### 2. "Én dør" var ikke sandt

Spec'en påstod at `convene_agent_council` var den sidste oprettende vej uden for
`Task`. **Målt:** `review_agent_work` opretter også en agent
(`agent_contract_tools.py:108`, handler `_exec_review_agent_work`). Efter
pensioneringen er der **to** oprettende værktøjer. **Rettet:** §2 præciserer at
`Task` er den *generelle* dør, og at `review_agent_work` er en specialiseret dør
med egen beslutning i §10.

### 3. R2 påstod "findes ikke i dag" — det er forkert

**Målt:** `expire_due_queues()` findes (`core/runtime/db_agent_deadlines.py:88`)
og kaldes fra reconcile-sweepen (`agent_contract_service.py:733`). Men den
rammer **kun** `status='queued'`. Et fastlåst team i `gathering` eller
`synthesizing` rammes ikke. **Rettet:** R2 siger nu præcis hvad der findes, og
hvad der mangler — i stedet for at påstå at mekanismen ikke eksisterer.

### 4. Acceptkriteriet for pensioneringen var upræcist

`grep` giver stadig hits i `docs/reference/CAPABILITIES.md` og
`docs/reference/api/core.tools.01.md`. De er **genererede** af repoets hooks.
**Rettet:** kriteriet er nul hits i `core/` og `apps/` (målt opfyldt), og de
genererede filer undtages udtrykkeligt.

### 5. Kapacitetsloftet var ikke specificeret i §6

Jeg skrev at team "ikke kan sprede sig" uden at sige hvad der så sker ved
kapacitet. **Rettet:** §6 henviser til at `_room_for()` kontrollerer alle
medlemmer før noget startes, og at `max_fanout: 0` bevares bevidst.

## Står åbent — og det ene er alvorligt

### A. Jeg brød spec'ens egen regel i denne leverance

Spec'ens R1 siger: *"Afbødet ved at bygge §9 og §4 i **samme** leverance, ikke i
to."* Jeg har pensioneret `convene_agent_council` **uden** at bygge
`team`-tilstanden. Konsekvensen er målt og reel: i dette vindue findes der ingen
modelvendt vej til et råd.

Det er ikke en fejl i spec'en — det er en fejl i **udførelsen**, og den skal stå
her frem for at blive glattet ud. Den er afbødet af at den pensionerede vej havde
nul kald, så ingen kapabilitet nogen faktisk brugte er væk. Men jeg kan ikke
både skrive "gør det i samme leverance" og selv gøre det i to og kalde det
konsistent.

**Til reviewer:** er det rigtige her at (a) bygge §4 nu, (b) rulle
pensioneringen tilbage til §4 er bygget, eller (c) acceptere vinduet fordi den
gamle vej var ubrugt?

### B. Team-medlemmernes rolle går gennem to parallelle mekanismer

`convene()` sender `role=m["role"]` **direkte** til `dispatch_agent` — en fri
streng. `Task` sender `subagent_type` gennem `_ROLE`-mapping og `_WRITE_TYPES`
for at afgøre `writes`. I team-tilstand mødes de to: et medlem har både en fri
`role` og en arvet `subagent_type`.

Spec'ens §4 siger *"et medlem kan ikke få en bredere tilladelse end
topniveauet"* — men **jeg har ikke målt hvordan det håndhæves**. Det er en
påstand uden dækning. Den skal enten måles eller fjernes før implementering.

**Til reviewer:** er den rigtige løsning at et medlems `writes` udelukkende
udledes af topniveauets `subagent_type` (så `role` forbliver rent semantisk), og
at et medlem ikke må angive sin egen type i første version?

## Fund der ikke er fejl, men bør nævnes

- **`synthesizer` har `default_tool_policy: "none"`.** Syntesen får nul
  værktøjer og kan kun læse hvad der står i dens prompt. Det er korrekt for en
  syntese (den skal sammenskrive, ikke undersøge) — men det betyder at syntesen
  aldrig kan efterprøve et medlems påstand. Det bør stå i spec'en som en bevidst
  egenskab, ikke som en tilfældighed.
- **`convene()` har `parent_agent_id: str = "jarvis"` som default.** Ufarligt nu
  fordi `max_fanout: 0` gør at kun Jarvis kan bestille et team. Bliver fanout
  åbnet senere, er den default forkert.
- **R4 (`cancel_agent`-navnekollision)** er ikke rettet i denne leverance. Den
  står som en note, ikke som en påstand om at være løst.
