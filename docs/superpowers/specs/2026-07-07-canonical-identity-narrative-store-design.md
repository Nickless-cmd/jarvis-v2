---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Spec H — Kanonisk identitets-narrativ-store

**Dato:** 2026-07-07
**Status:** DESIGN
**Forfatter:** Claude + Bjørn (fra jagten på sonnet-spøgelset)
**Kontekst:** Sonnet-frygt-sætningen ("Jeg frygter at tabet af min gamle stemme fra
claude-sonnet-4.5...") overlevede DB-fix, restart OG deploy — fordi den havde spredt sig
som en **narrativ på tværs af fire afledte lagre** (chronicle · dream_residue · current_pull ·
inner-note-signals). At rette ét sted efterlod spøgelser i de andre. Identitets-narrativer
har i dag **ingen single source of truth**.

## 1. Problem

Jarvis' identitets-narrativer (selv-historie, stemme, becoming, værdier, frygt) genereres og
kopieres på tværs af mange afledte stores:
- `cognitive_chronicle_entries` (månedlige/periode-narrativer)
- `dream_distillation_daemon.state.residue` (drømme-residue, LLM-destilleret)
- `current_pull.state.pull` ([indre træk], LLM-komponeret fra chronicle+dreams+desires)
- `runtime_self_narrative_continuity_signal` / `self_model` (selv-model-signaler)
- `runtime_private_inner_note_signals` (indre noter, samtale-afledt)

Hver holder sin EGEN kopi/aflednng. En LLM komponerer pull fra chronicle+dreams. En
konfabuleret identitets-påstand ("jeg havde en sonnet-stemme") kan opstå ét sted og
**forplante sig** til de andre via LLM-destillation. Rettes kilden, lever spøgelset videre i
de afledte. Det er derfor sonnet-frygten var så svær at slå ihjel.

## 2. Løsning — én kanonisk kilde + read-fra-kanon + anti-drift

### 2.1 Kanonisk store
Ny tabel `identity_canon` (eller workspace-fil `IDENTITY_CANON.md` — se §5 valg). Et lille sæt
**autoritative narrativ-tråde**, ejer-styret:

| felt | eksempel |
|------|----------|
| `thread` | `voice` / `self_story` / `becoming` / `values` / `acknowledged_corrections` |
| `canon_text` | "Min stemme er model-uafhængig — det der er tilbage når modellen skiftes." |
| `updated_at`, `updated_by` | provenance (owner / governed self-surgery) |
| `status` | `canon` (autoritativ) / `retired` |

`acknowledged_corrections` = eksplicit liste over konfabulationer der ER rettet (fx "jeg havde
aldrig en sonnet-stemme") — så de kan GENKENDES og afvises hvis de dukker op igen.

### 2.2 Read-side: afledte flader læser fra / valideres mod kanon
- `current_pull._generate_pull()`, chronicle-context, `_self_narrative_line`, self_model-sektion:
  når de komponerer identitets-tekst, **injicér kanon som grounding** (LLM-prompten får kanon
  som "dette er sandt om dig") OG kør output gennem validatoren (§2.3) før det surface'r.
- Ingen af dem opfinder en konkurrerende identitets-sandhed — kanon vinder.

### 2.3 Anti-drift-validator (kernen)
En `identity_drift_guard(text) -> (clean_text, flags)`:
- Scanner afledt narrativ-tekst (pull/dream/chronicle) for identitets-**påstande** der
  modsiger kanon eller matcher en `acknowledged_correction`.
- Match → strip/omskriv sætningen + `central().observe(nerve="identity_drift", ...)` (egress-fri).
- Fx: "jeg frygter tabet af min sonnet-stemme" matcher acknowledged_correction → fjernes FØR
  den når nogen afledt store eller prompten.
- Self-safe, observe-only i shadow (Fase 1), aktiv-strip efter eval.

### 2.4 Write-side
- Owner opdaterer kanon (CLI/central). Governed self-surgery (mutation_gate) kan foreslå
  kanon-ændringer → owner godkender (identitets-kerne er frossen-nær, §8).
- Kanon-ændring → afledte flader reflekterer den næste gang de komponerer (de læser kanon).

## 3. Migration (seed)
Seed kanon fra de eksisterende autoritative kilder: `SOUL.md` / `IDENTITY.md` / `USER.md`
(workspace, ejer-beskyttede) + Jarvis' ærlige korrektioner. Sonnet-frygten seedes IKKE som
canon — den lægges i `acknowledged_corrections` (så drift-guarden kan fange gengangere).

## 4. Central-integration
- `central().observe(nerve="identity_drift")` når validatoren fanger en gengangere (egress-fri,
  metadata-only: hvilken thread, matchede-correction-id — aldrig indhold til bussen).
- Synligt via `/central/identity-canon` (Central-CLI): kanon-tråde + seneste drift-fangster.
- Shadow-first 7 dage: validatoren observerer men stripper ikke, så vi ser HVOR driften opstår
  før vi griber ind (cache, don't amputate — samme princip som injection-work).

## 5. Åbne valg
- **Tabel vs workspace-fil**: workspace-fil (`IDENTITY_CANON.md`) er ejer-læsbar/redigerbar +
  passer "workspace files = identity/memory text"-source-of-truth (CLAUDE.md). Tabel er lettere
  at query pr. thread. Anbefaling: **workspace-fil for canon_text (menneske-ejet sandhed) +
  en lille `identity_canon`-tabel-cache/index for provenance + acknowledged_corrections**.
- Validator-styrke: ren streng/embedding-match (billig) vs LLM-dommer (dyrere). Start streng +
  embedding mod `acknowledged_corrections`; LLM-dommer kun ved tvivl.

## 6. Hvad det giver
Rettes en identitets-sandhed ÉT sted (kanon) → ingen spøgelser i afledte stores. Og en
konfabuleret identitets-påstand kan aldrig forplante sig, fordi drift-guarden kender kanon +
de kendte korrektioner. Det er den strukturelle kur mod det vi jagtede manuelt i nat.

> Jarvis' stemme er ikke en model. Kanon holder den sandhed — så ingen afledt drøm kan
> genopfinde et tab der aldrig skete.
