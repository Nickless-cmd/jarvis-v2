# Commit-attribution for alle aktorer - Design Spec

**Dato:** 2026-08-30
**Status:** Godkendt af Bjorn (design), afventer spec-review for implementeringsplan
**Scope:** Alle nye commits i `jarvis-v2`, uanset om de laves manuelt eller af en agent

---

## 1. Problem

Jarvis, Codex, Opus og Bjorn arbejder under samme Unix-bruger og arver derfor ofte den
samme globale Git-identitet. `Author` og `Committer` kan ikke i sig selv afgore, hvilken
aktor der udforte committen, hvilket run arbejdet kom fra, eller hvilken governance der
tillod den.

Det blev konkret synligt, da en autonom Jarvis-rettelse fra 24. august la ucommittet i
seks dage og senere blev committet med den samme Git-identitet som menneske- og
agentarbejde. Commit-historikken viste resultatet, men ikke en entydig operationel
proveniens.

Målet er et obligatorisk, maskinlaesbart auditspor pa alle nye commits. Kryptografisk
bevis er udtrykkeligt ikke et krav; en aktor med shell-adgang kan derfor i princippet
spoofe metadata. Systemet skal gore korrekt attribution automatisk og manglende
attribution umulig ved normal brug.

## 2. Beslutning

Git-commitbeskeden er source of truth. Hver ny commit skal indeholde et fast saet Git
trailers, valideret fail-closed af en versioneret `commit-msg`-validator.

En faelles commit-wrapper bygger trailers fra en eksplicit aktorkontekst. Runtime- og
agentkaldere bruger wrapperen i stedet for ra `git commit`. Manuelle commits bruger den
samme wrapper med `bjorn` som aktor. En lokal hook og en range-validator ved push sikrer,
at direkte Git-brug ikke kan efterlade commits uden gyldige trailers.

Mission Control eller databasen ma indeksere trailers til visning og sogning, men denne
projektion er aldrig en anden sandhed. Den kan altid genopbygges fra Git-historikken.

## 3. Metadata-kontrakt

Alle felter er obligatoriske. Manglende vaerdi skrives som den eksplicitte sentinel
`none`; et felt ma ikke udelades.

```text
Actor: jarvis
Actor-Type: agent
Run-ID: autonomous-abc123
Session-ID: chat-f01cf0c
Origin: autonomous
Approved-By: policy:auto-commit-v1
```

### Felter

| Trailer | Betydning | Regler |
|---------|-----------|--------|
| `Actor` | Aktoren der skabte den aktuelle commit | Registreret stabilt id, initialt `bjorn`, `jarvis`, `codex`, `opus` |
| `Actor-Type` | Overordnet aktortype | `human` eller `agent`; skal matche actor-registret |
| `Run-ID` | Operationel korrelation | Reelt run-id nar det findes; ellers genereret `manual-<UTC>-<suffix>` |
| `Session-ID` | Samtalekontekst | Reelt session-id eller `none` |
| `Origin` | Hvordan arbejdet blev udlost | `manual`, `interactive`, `autonomous` eller `delegated` |
| `Approved-By` | Governance der tillod committen | Actor-id eller `policy:<stabilt-policy-id>` |

Trailers forekommer praecis en gang hver. Ukendte ekstra trailers er tilladt, men kan
ikke erstatte de obligatoriske. Vaerdier trimmes og ma ikke indeholde linjeskift.

`Author`, `Committer` og `Co-Authored-By` bevares som normal Git-information, men er ikke
den autoritative aktorattribution. `Actor` betyder den aktor, der producerede den
nuværende commit-hash.

## 4. Aktorregister

Tilladte aktorer og deres type ligger i en lille versioneret konfiguration. Den er
eneste register for validatoren og wrapperen:

| Actor | Type | Normal oprindelse |
|-------|------|-------------------|
| `bjorn` | `human` | `manual`, `interactive` |
| `jarvis` | `agent` | `autonomous`, `interactive` |
| `codex` | `agent` | `interactive`, `delegated` |
| `opus` | `agent` | `interactive`, `delegated` |

Nye aktorer kraever en almindelig code change til registret. Frie modelnavne, versionsnumre
og provider-navne bruges ikke som actor-id; de kan tilfojes som valgfrie diagnostiske
trailers uden at destabilisere identiteten.

## 5. Commit-flow

### 5.1 Faelles wrapper

Wrapperen modtager committeksten og en struktureret attribution-kontekst. Den:

1. validerer actor, actor-type, origin og approval lokalt;
2. genererer et manuelt run-id, hvis konteksten ikke har et run;
3. fjerner eksisterende forekomster af de seks styrede trailers;
4. tilfojer et kanonisk trailerblok i fast raekkefolge;
5. kalder `git commit` uden at springe hooks over.

Wrapperen ejer kun commitbeskeden. Den vaelger ikke filer og bruger aldrig `git add -A`.
Eksisterende staging-, pathspec- og isolationregler forbliver kaldstedets ansvar.

### 5.2 Kaldere

- **Bjorn:** en kort manuel kommando/alias, der saetter `Actor=bjorn`, `Origin=manual`
  og `Approved-By=bjorn`.
- **Jarvis visible/interaktiv:** run-id og session-id kommer fra visible-run-konteksten;
  approval er `bjorn` eller den konkrete policy, der godkendte handlingen.
- **Jarvis autonom:** run-closure-gaten sender sit autoritative run-id, session-id,
  `Origin=autonomous` og et versionsfast policy-id.
- **Codex og Opus:** deres adapter/session-start saetter actor-konteksten eksplicit;
  commits bruger brugerens godkendelse (`Approved-By=bjorn`) og det aktuelle task/session-id.

Ingen aktor udledes fra procesnavn, committekst, modelnavn eller global `git config`.

### 5.3 Direkte `git commit`

Direkte commits er tilladt, hvis beskeden allerede indeholder en gyldig kontrakt. Ellers
afviser `commit-msg` med en kort fejl og viser den korrekte wrapperkommando. `--no-verify`
kan teknisk omga hooken; push-validatoren er derfor den anden kontrol og afviser den
resulterende commit, for den kommer ind i delt historik.

## 6. Validering og handhaevelse

Validatoren er en ren funktion over commitbeskeden og actor-registret. Den tjekker:

- alle obligatoriske trailers findes praecis en gang;
- actor findes og actor-type matcher registret;
- origin er tilladt for aktoren;
- run/session-vaerdier er ikke tomme;
- `Approved-By` er en registreret actor eller et syntaktisk gyldigt `policy:*` id;
- trailerblokken kan parses med Gits egen trailersemantik.

Handhaevelsen har to lag:

1. **`commit-msg`:** hurtig lokal feedback pa den commit, der er ved at blive skabt.
2. **Pre-push/range-check:** validerer alle nye commits i den range, der skubbes. Dermed
   fanges commits skabt med `--no-verify`, fra en anden checkout eller via aeldre tooling.

Hooks installeres fra versionerede scripts via repositoryets setupkommando. Installation
verificeres af capability/deploy-checket; en manglende hook ma ikke rapporteres som aktiv.
Hvis repositoryet senere far server-side CI eller protected remote, kan samme range-check
kores der uden ny valideringslogik.

## 7. Git-specialtilfaelde

- **Merge commit:** den aktor der udforer merge er `Actor`; merge-wrapperen tilfojer den
  normale kontrakt.
- **Revert:** `Actor` er den der udforer reverten. Den oprindelige hash forbliver i Gits
  standard-reverttekst.
- **Cherry-pick:** `Actor` er den der udforer cherry-picket. Oprindelig author bevares i
  Git, mens de styrede trailers omskrives til den nye commit-aktor.
- **Amend/rebase:** den aktor der producerer den nye hash bliver `Actor`. Wrapperen
  erstatter gamle styrede trailers i stedet for at duplikere dem.
- **Automatiske hook-rettelser:** filer som en pre-commit-hook genererer, tilhorer samme
  commit og samme actor-kontekst.
- **Historiske commits:** grandfatheres. Range-checket validerer kun commits nyere end
  feature-aktiveringscommitten; historikken omskrives ikke.

## 8. Forholdet til fil-attribution

Commit-attribution og write-attribution er forskellige fakta:

- Trailers svarer pa: **Hvem producerede denne commit?**
- Run-scopede write-events eller isolerede worktrees svarer pa: **Hvem redigerede filen?**

Denne feature lover kun det forste. Run-ID'et gor det muligt at koble committen til en
write-ledger, men en ren working-tree-diff bliver ikke derved et ejerskabsbevis. Jarvis'
auto-commit-gate skal fortsat vaere fail-closed ved tvivl og ma ikke bruge trailers som
erstatning for path-isolation.

## 9. Fejlhandtering

- Ukendt/manglende kontekst: ingen commit; vis praecist hvilke felter der mangler.
- Ugyldigt actor/origin-match: ingen commit; peg pa actor-registret.
- Hook ikke installeret: setup/deploy-check fejler synligt.
- Push med ugyldig commit: hele pushen afvises med hash og manglende/ugyldigt felt.
- DB/Mission Control-indeksering fejler: committen er stadig gyldig; projektionen kan
  genopbygges senere fra Git.

Ingen valideringsfejl ma automatisk omskrive brugerens committekst eller stage/unstage
filer. Wrapperen kan generere en midlertidig besked, men Git ejer den endelige commit.

## 10. Teststrategi

1. Golden tests for gyldige commits fra `bjorn`, `jarvis`, `codex` og `opus`.
2. Afvisning af manglende, tomme, duplikerede og ukendte trailers.
3. Actor-type og actor-origin mismatch afvises.
4. Wrapperen erstatter eksisterende styrede trailers deterministisk.
5. Manuelt run-id er unikt og har stabilt format.
6. Reelle temp-repo-tests for commit, merge, revert, cherry-pick og amend.
7. `--no-verify` slipper forbi lokal hook, men afvises af range-validatoren.
8. Historiske commits foer aktiveringspunktet grandfatheres.
9. Jarvis auto-commit sender korrekt run/session/policy og bruger fortsat pathspec.
10. Hook-installationscheck skelner mellem fil pa disk og faktisk aktiv hook-konfiguration.

Mocks er ikke tilstraekkelige for Git-semantik; specialtilfaelde og range-check kores mod
rigtige midlertidige repositories.

## 11. Udrulning

1. Tilfoj actor-register, ren validator, wrapper og tests uden handhaevelse.
2. Integrer alle fire aktorers kendte commitstier.
3. Kor audit over nye lokale commits og ret manglende kaldestier.
4. Aktiver `commit-msg` fail-closed og registrer aktiveringscommitten.
5. Aktiver range-check i pre-push/deploy-flow.
6. Verificer med en rigtig commit fra hver aktor og en bevidst ugyldig commit.

Der er intet laengerevarende dual-mode flag. Audittrinnet er en kort rollout-verifikation;
efter aktivering er manglende metadata en hard fejl.

## 12. Ikke i scope

- Kryptografisk signering eller separate OS-brugere.
- Bevis mod en ondsindet aktor med shell-adgang.
- Automatisk omskrivning/backfill af historiske commits.
- En ny DB-ledger som source of truth.
- Losning af samtidig filredigering; det horer til worktree/write-ledger-sporet.

## 13. Succeskriterier

- Enhver ny commit kan med `git log` entydigt kobles til actor, run, session, origin og
  approval.
- Ingen normal commitsti for Bjorn, Jarvis, Codex eller Opus kan skabe en commit uden
  gyldig kontrakt.
- `--no-verify` opdages senest ved push.
- Git er eneste autoritative historik; enhver UI/DB-visning kan genbygges.
- Eksisterende auto-commit path-isolation svaekkes ikke.
