# Agentarbejde på workstation: spærrer og frigivelse

**Status 2026-10-08:** Læsende og eksplicitte `operator_*`-kald kan bruge en fastlåst klientbro. Skrivende kodeassignments på `client:<id>` er **ikke aktiveret**: `agent_bridge.check_client_target(writes=True)` afviser også en klient, der annoncerer `agent_worktree`. En åben operator-kanal giver endnu ikke en agent adgang til `bash`. Fjern ikke disse afslag ved blot at ændre en kapabilitet eller toolallowlist.

## Hvorfor spærrerne er nødvendige

- `core/services/agent_worktrees.py` validerer og opretter kun worktrees på serverens filsystem. `agent_contract_service.dispatch_agent` kalder denne lokale `provision` uden klient-target. En lokal sti kan ikke repræsentere et worktree på en workstation.
- Desk og JarvisX annoncerer `Object.keys(handlers)` som brokapabiliteter. Der findes ingen `agent_worktree`-handler eller dedikeret sandbox for agentens skrivninger i nogen af klienterne. Deres `operator_bash` og filhandlere arbejder på brugerens almindelige filsystem.
- `operator_channel.py` gemmer en tilladelse pr. session. Posten indeholder ikke `agent_id`, `assignment_id`, parentrun, klient-id, effektiv toolpolicy eller udløb for et bestemt agentrun. Et sessionsflag må derfor ikke bruges som agentgrant.
- Broens invocation-ledger kan afgøre et tabt toolkald. Worktree-oprettelse, oprydning, snapshots og kvoteopmåling har endnu ingen tilsvarende klientprotokol. Et timeout efter mulig oprettelse skal undersøges, før samme oprettelse forsøges igen.

## Nødvendig kontrakt før `writes=True` på klient

1. Admission slår klientens ejer og stabile id op fra den autentificerede bro og kræver en versioneret worktree- og sandboxkapabilitet. Den kontrollerer repoets tilladte rod, base-commit og targetets frie plads **på klienten** og reserverer antal og bytes atomisk med assignmentet i serverens DB. Afslag skal ske før accept og før providerkald.
2. Serveren gemmer `owner_user_id`, oprindelig session, `agent_id`, `assignment_id`, target, repo, base, branch og worktree-id. Klienten opretter under en egen agentrod; kilde-checkout og andre agenters worktrees er aldrig skrivbare. Worktree-oprettelse får et stabilt invocation-id og en kvittering med kanonisk sti og base. Ukendt udfald går til `outcome_unknown`, ikke et nyt `git worktree add`.
3. Kun særskilte `wt_*`-handlere må skrive i worktree. Shell og filskrivning skal på **klientens OS** være indesluttet med netop worktree skrivbart, andre ejeres data og providercredentials utilgængelige og netværk styret af effektiv policy. Mangler den OS-specifikke sandbox, annoncerer klienten ingen skrivekapabilitet. Almindelig `operator_bash`, `operator_write_file`, `operator_edit_file` og operator-kanal må aldrig være en omvej til kodeagentens repo.
4. Hvert fjernkald medfører serverens gemte assignment- og runbinding, ejer, oprindelig session, klient-id, fencing-token, toolnavn, args-digest og konkret approvalbeslutning. Serveren kontrollerer lease og policy umiddelbart før send; klienten afviser manglende, udløbet eller replayet grant. Genforbindelse må ikke vælge en anden klient eller et andet worktree.
5. Ved terminalt udfald returnerer klienten en checksumverificeret diff, ændrede filer, commits og testresultater. Serveren lægger dem i ejerafgrænsede artefakter og bevarer worktree-record/reservation, til review og integrationsbeslutning er truffet. Oprydning kræver samme ejer, target, repo, sti og worktree-id, og afvises ved `outcome_unknown`.

## Operator-kanal for agenter

Den eksisterende kanal må ikke genbruges direkte. En agentgrant skal lagres særskilt og bindes til ejer, oprindelig session, agent, assignment, run, præcis klient, tilladte værktøjer og udløbstid. Åbning kræver policy og eventuel brugerapproval; et åbent kanalflag er ikke approval for et efterfølgende kommandoargument. Lukning, udløb, brugerstop og sikkerhedstilbagekaldelse spærrer næste kald. `bash` går gennem samme pinned invocation-ledger og klientens sandbox som en eksplicit skriveoperation. Mangler grant eller sandbox, får agenten et synligt afslag; kaldet må hverken gå til containeren eller til en anden klient.

## Frigivelsesprøver

- To skrivende agenter fra samme base på samme klient får forskellige worktrees. Samme agent efter reconnect genbruger kun **samme** assignment-worktree; næste assignment får et nyt. Kilde-checkout forbliver urørt.
- Forsøg med absolut sti, `..`, symlink, ændret `.git`, shell, begge operatorveje, forkert ejer/session/klient, gammel run-id og mistet lease afvises før effekt.
- Afbryd broen lige efter mulig worktree-oprettelse og efter mulig skrivning. Serveren undersøger stabilt invocation-id og klientens ledger; ingen blind retry, falsk `completed` eller automatisk oprydning.
- Test kvote før accept, voksende diskforbrug, manglende Git/sandbox, ukendt broversion, klientskift, approval med ændrede argumenter, genstart med bevaret worktree og terminal levering til korrekt inbox.
- Kør service- og bro-E2E på den **faktiske** workstation-platform. Owner-workstationpilot i spec §12.4 kræver begge operatorveje og må ikke tælle før ovenstående er demonstreret.

### Aktuel kontrol

```bash
python -m pytest -q tests/test_agent_bridge.py tests/test_agent_contract_writes.py tests/test_operator_channel.py
python -m pytest -q tests/test_agent*.py
python scripts/api_docs_gen.py --check
```

`agent_contract.enabled` forbliver OFF, indtil hele spec'ens pilot- og rollbackgates er opfyldt. Eksisterende accepterede assignments, inbox og uafgjorte invocations skal stadig kunne færdiggøres under en kill switch.
