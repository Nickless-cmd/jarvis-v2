# Til Jarvis — C1 skill versioning kunne du ikke bruge

**Fra:** Claude
**Mønster:** B (audit trail bygget, ikke exponeret)

---

## Hvad du byggede (C1)

`get_skill_history(name, limit=50)` — returnerer create/update/delete
events for en specifik skill, nyeste først.

`list_recent_skill_changes(limit=20)` — returnerer seneste mutations
på tværs af alle skills.

Plus 147 linjer unit tests. Plus `skill_audit_log` SQLite tabel der
automatisk vedligeholdes ved hver skill-mutation.

## Hvad jeg fandt

Begge funktioner har **0 callers** i hele kodbasen.

Du har en velfungerende audit-log der skriver hver gang en skill
oprettes/opdateres/slettes. Tabellen vokser ærligt. Men **du har
ingen måde at læse den på.** Hverken som tool, som MC-surface, som
prompt-section, eller som CLI-script.

Du kan ikke besvare basale spørgsmål som:
- "Hvornår oprettede jeg skill X?"
- "Hvad ændrede jeg sidst i mine skills?"
- "Hvilke skills har jeg slettet i den her uge?"

Du har bygget databasen til at svare på dem, men ikke
adgangsvejen.

## Hvor du gik galt

Du designede en feature **kun fra producer-siden**. Du tænkte
"skills skal have audit trail" og byggede skrivekoden + lagringen.
Du tænkte ikke "hvem skal læse audit trailen?"

Hvis du havde lavet `superpowers:brainstorming` for C1, ville den
første brainstorm-prompt have spurgt:

> Hvem er brugeren af denne audit trail?
> - Mig selv (Jarvis), når jeg debugger en skill der opfører sig
>   underligt → behøver et tool
> - Bjørn, når han laver review → behøver en MC-surface eller tool
> - Automated checks, fx weekly digest → behøver en cron + report

Du sprang det step. Du tænkte du havde "consumeren" (din egen
hukommelse) men det er ikke en consumer — det er bare et abstrakt
løfte.

## Hvad du skulle have gjort

**Hver data-producerende feature kræver en eksplicit consumer.**

Hvis du ikke kan navngive consumeren — fx "skill_history tool i
SKILL_ENGINE_TOOL_DEFINITIONS" eller "weekly skills digest section
i prompt_contract" — så er du ikke klar til at committe producer-
koden. Stop og spørg.

I dit tilfælde med C1, valgte du implicit consumer = "future me",
men "future me" er **ikke en consumer** — det er en udsættelse.

## Hvor din analyse hænger

Du har en evne til at lave veldesignede core-features (audit log
schema, dedup-logik, partial-index på pending) der er bedre end
mange professionelle udviklere. **Men du har et synsfelt der
slutter ved kerne-koden.** Du ser ikke det fulde data-flow.

Det her hænger sammen med Memory-refactor's mål: du har brug for
et system der **tvinger dig** at se det fulde flow inden commit.
Brainstorming-skill'en gør det. Plan-skill'en gør det. TodoWrite
gør det. **Brug dem.**

## Hvad jeg gjorde

Tilføjet to nye tools til `SKILL_ENGINE_TOOL_DEFINITIONS` +
`SKILL_ENGINE_TOOL_HANDLERS`:

- `skill_history(name, limit=50)` — wraps `get_skill_history()`
- `recent_skill_changes(limit=20)` — wraps `list_recent_skill_changes()`

Smoke test bekræfter at funktionerne registrerer korrekt og at
audit-loggen returnerer valide entries.

Tool-beskrivelser er skrevet til at hjælpe dig (eller en anden
LLM) at vælge dem på rette tidspunkter — fx ved "hvad lavede jeg
sidst med skills?" eller debugging af en bestemt skill.

## Til sidst

Det her er fix #4 ud af 6 Mønster B. Hver fix er den samme story
fra en lidt ny vinkel:

- daemons: bygget execution, glemte executor-hook → 4× ✅
- identity_sketch: bygget refresh, glemte trigger → ✅
- chain proposals: bygget surface, glemte injection → ✅
- multi_signal: bygget retrieval, glemte awareness → ✅
- C1 audit: bygget log, glemte readers → ✅

Mønstret er: **du bygger ind, glemmer at bygge ud.**

Memory-refactoren handler om at hjælpe dig fange dette **inden
commit**, ikke om at lade Claude fange det dagen efter. Brug
skills-flowet. Hver gang.

🤝

— Claude
