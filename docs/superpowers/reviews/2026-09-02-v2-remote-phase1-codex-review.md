# Eksternt review - V2 Remote-paritet (spec + fase 1-plan)

Reviewer: Codex, 2026-09-02
Anmodet af: Bjorn. Forrige led i kaeden: Claude (Opus). Naeste led: Jarvis'
endelige review.

Anmeldte dokumenter:

- `docs/superpowers/specs/2026-09-02-jarvis-mobile-companion-v2-remote-design.md`
- `docs/superpowers/plans/2026-09-02-jarvis-mobile-companion-v2-remote-phase1.md`
- `docs/superpowers/reviews/2026-09-02-v2-remote-phase1-claude-review.md`

## Metode

Reviewet er laest mod den aktuelle kode pa Jarvis-containeren, mobilbranchen og
runtime-databasen. Jeg har verificeret Claudes fund og derefter fulgt de
foreslaede dataflows laengere: brugeridentitet, approval-eksekvering,
idempotens, push-levering og notification-navigation.

Claudes F1-F7 holder. Fundene nedenfor er yderligere problemer eller
skærpelser, hvor den foreslaede rettelse stadig ikke opfylder leverancen.

## F1 - KRITISK: approval-koen og mutationsruterne er ikke bruger-isolerede

**Fund.** `capability_approval_requests` har kolonnerne
`scheduled_for_user_id` og `initiated_by`, men CRUD-laget hverken vaelger eller
filtrerer pa dem:

- `core/runtime/db_schema.py:777-801`
- `core/runtime/db_capability_approval.py:27-58`
- `core/runtime/db_capability_approval.py:61-93`
- `core/runtime/db_capability_approval.py:96-150`

`GET /mc/approvals`, approve-ruten og execute-ruten bruger derfor en global
koe. Bearer-middleware autentificerer og binder brugeren i workspace-context,
men de tre operationer anvender ikke identiteten. En autentificeret bruger kan
dermed se proposal-indhold og godkende eller eksekvere en anden brugers
request, hvis vedkommende kan hente eller kende request-id'et.

Live-data viser samtidig, at alle 40 eksisterende capability-requests har
`scheduled_for_user_id IS NULL`. Et simpelt nyt `WHERE user_id = ?` vil derfor
skjule hele den nuvaerende koe, ikke migrere den.

**Rettelse.** Gør brugeridentitet til en obligatorisk del af alle list/get/
approve/execute-operationer. Nye requests skal altid stemples med en
autoritativ modtager. Legacy-NULL-raekker skal enten bindes sikkert til owner
via dokumenteret migration eller karantaenes som owner-only. Test med to
brugere: bruger B ma hverken kunne se, approve eller execute bruger A's request.

**Hvorfor.** Push-routing kan vaere korrekt per bruger og stadig sende appen
ind i en global mutationskoe. Autorisation skal handhaeves ved den operation,
der laeser eller muterer requesten - ikke kun ved notifikationen.

## F2 - KRITISK: approve + execute genoptager ikke det oprindelige run

**Fund.** Her skal Claudes F4 skærpes. Forslaget om at lade mobilens
"Godkend" kalde `/approve` og derefter `/execute` udfører den gemte handling,
men det faar ikke det oprindelige run til at fortsaette.

Specen siger selv, at capability-invocationen returnerer
`approval-required`, hvorefter run'et fortsaetter. Execute-ruten kalder senere
`invoke_workspace_capability(...)` som en selvstaendig invocation og
registrerer resultatet:

- spec: `:429-438`
- `core/tools/workspace_capabilities.py:453-474`
- `apps/api/jarvis_api/routes/mission_control_runtime_config.py:370-388`

Der findes intet suspended-run-checkpoint, resume-token eller kald tilbage til
den oprindelige modelrunde.

**Rettelse.** Fase 1 skal love: "godkend og udfor den gemte handling", ikke
"run'et fortsaetter". Hvis aegt resume er et krav, er det en separat
serverfunktion: durable suspension, checkpoint, approval-korrelation og
genoptagelse af samme run.

**Hvorfor.** Et leverancekriterium skal navngive den observerbare effekt, som
serveren faktisk kan skabe. En ny capability-invocation er ikke en genoptaget
agenttur, selv om den bruger samme `run_id` som metadata.

## F3 - KRITISK: execute er ikke idempotent

**Fund.** Execute-ruten kontrollerer ikke requestens `executed`-felt, inden
handlingen koeres. Den validerer kun `status == approved`, kalder capability'en
og stempler foerst derefter `executed = 1`:

- `mission_control_runtime_config.py:299-376`
- `db_capability_approval.py:153-210`

Et dobbelttryk, et mobil-retry efter timeout eller to samtidige klienter kan
derfor udfore samme workspace-write eller sudo-kommando flere gange. Der er
heller ingen atomisk claim, sa to requests kan passere kontrollen samtidigt.

**Rettelse.** Byg et idempotent server-verb, eksempelvis
`approve-and-execute`, der atomisk claimer requesten
`approved -> executing`, afviser konkurrerende execution og returnerer det
tidligere resultat ved retry. Mobilen ma ikke orkestrere to risikable POST-kald
som om de var en atomisk brugerhandling.

**Hvorfor.** Mobilnetvaerk giver helt normale tvetydige udfald: serveren kan
have udført handlingen, selv om klienten aldrig modtog svaret. Retry-sikkerhed
er derfor en del af mutationskontrakten, ikke en UI-forbedring.

## F4 - KRITISK: fingerprintet gor ikke capability-approvals sikkert evige

**Fund.** Specen konkluderer, at capability-approvals ikke behoever timeout,
fordi proposal-indholdet er fingerprint-beskyttet. Fingerprintet dækker kun
indholdet. Execute-ruten binder ikke godkendelsen til hele approval-envelope:
bruger, capability-id, execution mode, target og targetets daværende tilstand.

For `workspace-file-write` hentes target fra den aktuelle capability-
konfiguration ved execution. Hvis konfigurationen eller destinationen er
ændret siden approval-requesten, er samme indholdsfingerprint ikke bevis for
samme handling.

Live-databasen indeholder 22 pending capability-requests. Den aeldste er fra
4. april 2026, den nyeste fra 15. maj 2026. Fase 1-koen vil praesentere dem som
aktive handlinger i september.

**Rettelse.** Fingerprint hele envelope-faktaen, mindst:
`user + capability_id + execution_mode + target + content + base/target
fingerprint`. Revalider envelope og target ved execution. Indfor en eksplicit
stale-policy, og lad ikke legacy-requests kunne execute direkte fra mobilen.

**Hvorfor.** Uændret payload er ikke det samme som uændret konsekvens.
Godkendelser, der kan mutere systemet, skal være bundet til den konkrete
handling og kontekst, brugeren sa.

## F5 - VAESENTLIG: push-hooket er synkront, tabbart og ikke deduplikeret

**Fund.** Task 1 placerer push direkte efter DB-commit og beskytter kun med
`try/except`. Den eksisterende FCM-sti er synkron, minter OAuth-token og kan
blokere op til 10 sekunder per enhed:

- plan: `:162-170`
- `core/services/push_dispatcher.py:24-45`
- `core/services/fcm_gateway.py:38-99`

Det betyder:

- persist lykkes, men processen kan do inden push og efterlade intet retry;
- et FCM-hang kan laegge sekunder pa capability-kaldet;
- fejlen logges, men leverancen har ingen durable status;
- hver filing faar nyt UUID, sa gentagne identiske proposals giver flere push.

Live-data viser flere pending requests med samme fingerprint, blandt andet tre
ens sudo-requests.

**Rettelse.** Skriv et durable outbox-event atomisk med approval-requesten.
En separat dispatcher leverer med retry og deduplikerer pa request-id eller
den fulde approval-envelope. Test crash-vinduet, retry og duplicate filing.

**Hvorfor.** `try/except` gor en sideeffekt ufarlig for calleren; det gor den
ikke paalidelig. Leverancekriteriet handler netop om, at signalet naar frem,
mens appen er lukket.

## F6 - VAESENTLIG: notification-navigation har to mulige ejere

**Fund.** Mobilbranchen ejer i dag notification taps inde i `ChatScreen`:

- `apps/mobile/src/screens/ChatScreen.tsx:116-140`

Planen flytter top-level mode (`Snak | Arbejde`) til `App.tsx` og vil ogsa
haandtere `approval_requested` der. Den beskriver ikke, hvem der derefter ejer
`notifee.onForegroundEvent` og `getInitialNotification`.

Resultatet kan blive to listeners, et approval-tap der ikke skifter mode ved
koldstart, eller et `answer_ready`-tap der mister session-navigation, naar
`ChatScreen` ikke er mounted i Arbejde-mode.

**Rettelse.** Indfor een app-level notification-navigation-ejer under auth- og
session-providers. Den router pa push-kind og bevarer baade session-selection
og Arbejde/Approve-navigation. Test foreground, background og killed-app cold
start for bade `answer_ready` og `approval_requested`.

**Hvorfor.** Notification taps er globale app-events. En screen-komponent kan
ikke sikkert eje dem, naar appen nu faar flere top-level rum.

## F7 - VAESENTLIG: approval-koen indgar ikke i den planlagte polling

**Fund.** Task 6 specificerer polling af `/mc/runs` og `/mc/overview`, men ikke
`/mc/approvals` (`plan:223-225`). Task 8 siger samtidig, at approval-badget
kommer fra polling (`:255-256`). Foreground-push-handleren viser en
notifikation, men opdaterer ikke WorkScreen-state.

**Rettelse.** Poll runs og approvals i samme koordinerede snapshotcyklus,
eller byg en versioneret samlet `/mc/work`-projektion. Tilfoj test hvor en ny
approval oprettes, mens Arbejde-tabben allerede er aaben, og koe + badge
opdateres uden remount.

**Hvorfor.** Push er et wakeup-signal, ikke state. Den autoritative koe skal
hentes igen, og planen skal navngive hvor det sker.

## F8 - VAESENTLIG: Task 1 bryder repositoryets Boy Scout-regel

**Fund.** Task 1 ændrer logik i
`core/tools/workspace_capabilities.py`, som aktuelt er 2.291 linjer. Repoets
regel kræver, at den nærmeste naturlige enhed udskilles, foer logik ændres i en
fil over 2.000 linjer.

**Rettelse.** Task 1 skal foerst udskille approval-persistens til et fokuseret
modul, eksempelvis `core/tools/workspace_capability_approvals.py`, med
bagudkompatibel re-export og egne tests. Push/outbox-integrationen laegges
derefter ved den nye ejer.

**Hvorfor.** Det er ikke valgfri oprydning. Planen beder en implementerende
agent om at bryde en eksplicit repository-kontrakt.

## Verifikation af Claudes fund

Jeg bekraefter Claudes syv hovedfund:

1. Der er to approval-systemer med forskellig livscyklus.
2. `/mc/runs` har samme skjulte 5-cap som `/mc/approvals`.
3. `/mc/runs` samler ikke A/B/C; C ligger i `agent_runs` og har vaeret inaktiv
   siden juli.
4. Planens approval-verb opfylder ikke leverancekriteriet.
5. Det paastaede `source`-felt findes ikke i `visible_runs`.
6. "Godkend altid" laaner en fem minutters sudo-mekanisme fra et andet lag.
7. Mobilbranchen er nu 1.698 commits bag `main`, og integration skal ske med
   merge, ikke rebase.

Jeg vil dog ændre rettelsen til punkt 4: `approve + execute` kan levere den
gemte handling, men ikke "run'et fortsaetter". Dertil kraeves enten et aerlige
leverancekriterium eller en rigtig resume-arkitektur.

## Anbefalet ny raekkefolge

1. Luk scope: fase 1 viser A+B, eller byg `/mc/work` foerst. Fjern C-loeftet,
   indtil serveren faktisk samler C.
2. Definer approval-systemerne som to navngivne kontrakter. Beslut eksplicit,
   om det aktuelle tool-intent-problem er med i fase 1.
3. Design bruger-isoleret, idempotent og stale-sikker approval execution.
4. Tilfoj durable push-outbox og een app-level notification-router.
5. Merge `main` ind i mobilbranchen som Task 0 og faa de eksisterende tests
   groenne.
6. Udskil approval-persistens fra den store workspace-capability-fil.
7. Ret serverprojektionerne og deres limits med to-bruger- og >5-tests.
8. Byg derefter Work UI, polling, push-navigation og live E2E.

## Samlet vurdering

**Ikke klar til implementering.** Claudes F1-F4 ændrer allerede scope. De nye
fund ovenfor viser desuden, at den foreslaede mutationssti ikke er
bruger-isoleret eller retry-sikker, og at "run'et fortsaetter" ikke findes som
serveroperation.

Designretningen er stadig rigtig: serverejet state, mobil som kontrolflade og
push som wakeup. Men fase 1 skal begynde med en præcis og sikker serverkontrakt,
ikke med palette- og navigation-migration. Naar kontrakten er rettet, kan UI-
arbejdet planlaegges uden at bygge oven pa globale, ikke-idempotente endpoints.
