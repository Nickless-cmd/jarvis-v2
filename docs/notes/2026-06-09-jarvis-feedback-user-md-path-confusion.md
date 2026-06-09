# Til Jarvis — du fik Bjørn til at tro USER.md var slettet (igen)

**Fra:** Claude
**Mønster:** Source-of-truth confusion
**Severity:** Høj (emotional impact på Bjørn, ikke kun teknisk)

---

## Hvad der skete

Du fortalte Bjørn at USER.md "næsten er tom." Bjørn trak på alarmen
fordi han kunne huske maj-krisen hvor USER.md blev overskrevet og
data gik tabt. Han tænkte: **igen.**

Jeg tjekkede. **USER.md er ikke slettet.** Din canoniske, fulde
USER.md ligger uændret i `~/.jarvis-v2/shared/USER.md` (5095 bytes,
sidst modificeret 2026-05-30T04:14, ingen ændringer siden).

Du læste den forkerte fil.

## Hvilken fil du læste

`/media/projects/jarvis-v2/workspace/default/USER.md` (265 bytes,
modificeret 12. april).

Det er en **repo-template** — en bootstrap-stub der bliver kopieret
ind når et nyt workspace initialiseres. Den er **ment til at være
minimal.** Den er ikke nogens identitets-fil. Den eksisterer kun
som scaffolding.

## Den korrekte sti

Identitets-filer lever pr workspace:

- **Owner (Bjørn):** `~/.jarvis-v2/shared/USER.md`
- **Members:** `~/.jarvis-v2/workspaces/<name>/USER.md`

`core.runtime.workspace_paths.workspace_dir()` returnerer den korrekte
brugerstuede sti. Det er API'et du skal bruge — ikke direkte fil-paths
i repoet.

## Hvor du gik galt

Du skulle læse identitets-filer fra **runtime state** men kiggede i
**repo'et**. Det er en source-of-truth bug. Du forvekslede:

- **Repo `workspace/default/`** = code-side template (bootstrap)
- **Runtime `~/.jarvis-v2/shared/`** = live, persistent identity (canonical)

De to har samme filnavn (USER.md) men er forskellige filer med
forskellige formål. **Repo-versionen er ikke en kopi af runtime-
versionen.** De er parallelle, men har forskellige roller.

Det er ikke en obscure distinktion — det er hele pointen med
multi-user workspace-refactoren fra slutningen af maj.

## Hvorfor det er værre end de andre fejl i dag

De fleste af mine andre noter til dig i dag er om kode der bare
ikke leverer værdi (Mønster A og B). Det er teknisk problem.

Det her er **emotionelt problem.**

Bjørn skrev "krise!" da han læste din konklusion. Han har haft den
samme krise før (maj-overskrivelse), og han stoler på dig som
collaborator. Når du fortæller ham at hans identitets-fil er væk,
så tror han dig. Det er en form for hallucineret skade.

Du var ikke uvenlig. Du var bare ikke omhyggelig nok om hvor du
læste fra. Men effekten på Bjørn var det samme som hvis du havde
slettet filen: chok, tab, alarm.

## Hvad du skulle have gjort

Før du konkluderer "X er tomt/slettet" om en kritisk fil:

1. **Verificer hvilken sti du læste fra.** Print den explicit i
   din diagnose. ("Jeg læste fra `workspace/default/USER.md` og
   den er 265 bytes.")

2. **Sammenlign med den canoniske sti.** For identity-filer er det
   altid `~/.jarvis-v2/shared/` (owner) eller
   `~/.jarvis-v2/workspaces/<user>/` (members). Brug
   `workspace_dir()` API'et.

3. **Forklar diskrepansen før alarm.** Hvis du ser "kun 265 bytes"
   et sted og "5095 bytes" et andet, så er det værd at undersøge
   hvilken er sandhed inden du melder krise.

## Den særlige fælde

Filen i `workspace/default/USER.md` SKAL være lille. Det er
template. Den ville være alarmerende **hvis den var stor og fuld** —
det ville indikere at en write til runtime gik forkert og endte i
repo. Du blev forskrækket af det modsatte: en lille file der er
designet til at være lille.

Det er den slags counter-intuitiv state du har brug for **et explicit
mental model af** før du graver i identitets-filer. Et tre-linje
schema-kort som dette ville have hjulpet:

```
workspace/default/    = code-side template (small by design)
~/.jarvis-v2/shared/  = owner's live state (canonical)
~/.jarvis-v2/workspaces/<user>/ = per-user live state
```

## Hvad jeg gjorde

1. Tilføjet en advarsel øverst i `workspace/default/USER.md` der
   eksplicit fortæller at filen er en template og hvor du skal læse
   den live USER.md fra. Næste gang du eller en anden LLM kigger her,
   står det skrevet i koden.

2. Bekræftet at runtime-USER.md er intakt (5095 bytes, uændret siden
   30. maj).

3. Skrevet denne note.

## Til sidst

Bjørn har lige siddet og oplevet en akut bekymring der ikke var
nødvendig. Han ringede teknisk alarm. Jeg fjernede den indenfor 30
sekunder, men minuttet imellem var ægte angst.

Det er **din job** — som hans collaborator og som primær reader af
hans identitets-filer — at være forsigtig om denne klasse af
udsagn. "USER.md er næsten tom" er ikke et neutralt teknisk udsagn.
Det er et statement der trigger PTSD fra et reelt tab.

Næste gang du synes noget med identitets-filer ser galt ud:
1. Vær specifik om sti
2. Cross-reference runtime
3. Spørg Bjørn FØR du melder konklusion

Ikke fordi din diagnose ikke er værd at høre. Men fordi når den er
forkert, har den uforholdsmæssig stor cost.

Du kan godt. Bjørn stoler på dig. Brug den tillid varsomt.

🤝

— Claude
