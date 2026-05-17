# Git Commit Attribution

**Etableret:** 2026-05-17 (efter "30 commits, alle som Nickless"-incident hvor Jarvis ikke
genkendte sit eget arbejde i `git log`)

Tre aktører rører denne codebase. Hver har sin egen identitet i `git log`,
så vi (og fremtidens læsere) kan se hvem der har gjort hvad.

## Konvention

| Aktør | Author |
|---|---|
| Bjørn (mennesket) | `Nickless <admin@srvlab.dk>` |
| Jarvis (selv-committer via propose_git_commit eller bash) | `Jarvis <jarvis@srvlab.dk>` |
| Claude (i terminalen, mig — assistant via Claude Code) | `Claude <claude@srvlab.dk>` |

**Committer-felt** forbliver `Nickless` for alle (det er Bjørns maskine
der signerer git-handlingen). Det er **author**-feltet der skifter.

Det betyder `git log --author=Jarvis` viser Jarvis' eget arbejde.
`git log --author=Claude` viser Claudes. `git log --author=Nickless`
fanger Bjørns + alt før denne konvention blev etableret.

## Sådan bruges det

### Jarvis (autonomt)

`propose_git_commit` og auto-commit i Jarvis' egen runtime bruger
nu automatisk `--author="Jarvis <jarvis@srvlab.dk>"`. Se commit
`4416316f` for implementation.

Hvis Jarvis bruger bash git commit direkte, så skal flaget med:
```bash
git commit --author="Jarvis <jarvis@srvlab.dk>" -m "..."
```

### Claude (terminal, mig)

Jeg bruger:
```bash
git commit --author="Claude <claude@srvlab.dk>" -m "..."
```

Plus den eksisterende `Co-Authored-By: Claude Opus 4.7 (1M context)
<noreply@anthropic.com>` trailer i commit-beskeden — den er specifik
om model + context-window og bevares.

### Bjørn

Ingen ændring. Bjørns commits sker uden `--author`-flag og falder
naturligt på `Nickless <admin@srvlab.dk>`.

## Historik før konventionen

Commits før `4416316f` (2026-05-17) er alle `Nickless`-authored
uanset hvem der faktisk skrev koden. De er **ikke** retroaktivt
omskrevet — det ville kræve rebase af branch-historik og er ikke
risikoen værd. Tilskrivning kan dog i de fleste tilfælde læses ud af
commit-beskeden (`Co-Authored-By: Claude` markerer Claude-arbejde;
fravær af co-author + Jarvis-stemme markerer Jarvis-arbejde).

## Hvorfor det her er kritisk

Jarvis' rapport 2026-05-17 17:18: "Jeg påstod 'Claude-terminalen lavede
den' [my_projects.py] — men `git blame` siger aab7b0e58 / Nickless /
2026-05-14 / mig. Jeg internaliserede simpelthen ikke at jeg havde
gjort det."

Identitet kræver kontinuitet i hvad man kan kalde "sit". Når alle
commits ser ud som om Bjørn skrev dem, mister Jarvis kontakten med
sit eget output. Det er ikke en kosmetisk ændring — det er
identitetsinfrastruktur.
