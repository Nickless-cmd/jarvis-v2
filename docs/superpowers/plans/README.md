# Plan-dokumenter — hvordan de skal læses

> Skrevet 28/9-2026, da det viste sig at `status: færdig` i 78 af filerne ikke betød
> det det så ud som.

## Hvad `status: færdig` betyder — og ikke betyder

De 78 filer med `status: færdig` blev **batch-markeret af en doc-audit 8. juli 2026**.
De deler alle samme frontmatter:

```
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
```

`ground_truth`-linjen er den ærlige del: det der blev verificeret var at **artefakten
findes i træet** — moduler, symboler, referencer. Ikke at hver task i planen var udført.

## Checkboxene er ikke en fremdriftsmåler

Planerne bruger `- [ ]` til at spore tasks. **De blev aldrig vedligeholdt efter auditten.**
På tværs af alle 136 filer: ~275 afkrydsede mod ~4.782 uafkrydsede. 78 filer med
`status: færdig` har **nul** afkrydsede tasks.

Det betyder ikke at 4.782 opgaver mangler. Det betyder at checkbox-systemet blev brugt
til at *skrive* planen, ikke til at *følge* den. Læs dem ikke som en todo-liste.

## Hvad der faktisk er levende arbejde

- **`../SPEC_GAP_BACKLOG.md`** — de verificerede huller. Tre står åbent pr. 28/9-2026.
- **Planer med en reel status:**
  - `2026-07-16-agent-tool-delegation-impl-plan.md` — `draft`
  - `2026-09-02-jarvis-mobile-companion-v2-remote-phase1.md` — omskrevet, klar til implementering

## De 56 uden status

De har ingen `status:`-linje — alle fra juli 2026, da formatet skiftede. De er
**ikke auditeret**. `docs/DOCS_MANIFEST.md` (genereret 8/7) kategoriserer dem sammen
med resten af dokumentationen.

## Hvis du tilføjer en plan

Sæt en ærlig status. `færdig` betyder *verificeret udført*, ikke *skrevet ned*.
