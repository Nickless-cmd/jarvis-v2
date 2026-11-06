# Executive contradiction: en critical-regel der fyrer på et signal der ikke må veto

**Status:** konklusion — ingen kodeændring uden Bjørns godkendelse
**Slags:** analyse
**Dato:** 6. november 2026
**Side-opgave:** side-6514e3c2f6

## Spørgsmål

Reglen `executive_contradiction_blocks_until_resolved` (`core/services/rule_definitions.py:232`)
har priority 95, priority_delta +45, urgency `critical`, og fyrer på
`executive_contradiction.active`. Målt 6/11-2026: 339 aktive rækker i
`runtime_executive_contradiction_signals`, 339 distinkte canonical_keys, nul
nogensinde lukket.

Tre spørgsmål skulle besvares med måling. Alle tre er nu målt.

## Målinger

| måling | resultat |
|---|---|
| rækker i alt | **339** — alle `status='active'` |
| distinkte canonical_keys | **339** (1:1 med rækker) |
| nøgle-form | `executive-contradiction:contradiction-pressure:<run_id>` |
| ældste række | 2026-11-04T12:10:50Z → **1,86 døgn** |
| nyeste række | 2026-11-06T08:54:05Z |
| `stale_after_days` i spec | **7** |
| sweep kørt manuelt nu | `{'stale_marked': 0}` — korrekt, intet er over 7 døgn |
| fladens svar lige nu | `active_count: 2`, `authority: non-authoritative`, `execution_veto_state: not-authorized` |

## Svar 1 — skal et non-authoritative signal udløse en critical-blokering?

**Nej, og kilden siger det selv.** Signalets egen `status_reason` lyder:
*«Bounded executive contradiction remains runtime support only and is not yet
allowed to directly veto execution.»* Fladen rapporterer samtidig
`authority: non-authoritative` og `execution_veto_state: not-authorized`.

Reglen gør det modsatte: den løfter et signal der eksplicit er nægtet
veto-rettighed til `urgency="critical"` med `priority_delta=+45`. Det er ikke en
fortolkning — det er to felter i samme system der modsiger hinanden, og reglen
vælger det stærkeste af dem.

**Anbefaling:** reglen skal ikke fyre på `active` alene. Enten skal den kræve at
signalet har veto-rettighed (`execution_veto_state != "not-authorized"`), eller
den skal nedprioriteres til `medium` så den ikke konkurrerer med ægte kritiske
regler. Det er en governance-nær beslutning og kræver Bjørns ord.

## Svar 2 — skal domain_key være stabil på tværs af kørsler?

**Nej — og sammenligningen med open loops viser hvorfor det er bevidst.**

`canonical_key` bærer run-id'et (`visible-4ff1376db67b…`), så hver kørsel får sin
egen nøgle. Det betyder at `supersede` aldrig kan ramme på tværs af kørsler.

Men det er **korrekt design**, ikke en defekt. Open-loop-familien gør præcis det
samme med vilje: run-nøgler er 1:1 med kørsler, fordi hver kørsel er en
selvstændig hændelse der ikke skal overskrive den forrige. Det der gør
open-loop-familien sund er ikke en stabil nøgle — det er at den har en
**to-trins lukkevej** (stale efter 5 dage, closed efter yderligere 7).

Konsekvensen for contradiction-familien: 339 rækker er ikke 339 dubletter. De er
339 historiske hændelser, og de forsvinder af sig selv når de passerer 7 døgn.
Den ældste er 1,86 døgn, så den første stale-markering falder omkring **11.
november**.

## Svar 3 — mangler der en stale→closed-vej?

**Nej. Vejen findes, er konfigureret, og virker.**

`_SPEC` sætter `stale_after_days=7`, og `build_surface()` i
`signal_tracking_framework.py:496` kalder `refresh_statuses(spec)` ved hver
flade-bygning. Fladen bygges fra fem produktionskaldere
(`runtime_cognitive_conductor.py:1249`, `runtime_operational_memory.py:114`,
`chronicle_consolidation_signal_tracking.py:120`, og to søster-familier).

Jeg kørte sweepen direkte: `{'stale_marked': 0}`. Det er det **korrekte** svar —
intet er over 7 døgn endnu. Sweepen er ikke død; den har bare ikke haft noget at
gøre.

**Men der er en ægte asymmetri:** contradiction-familien har kun **trin 1**
(stale). Den har ingen `stale → closed`-overgang, som open loops har i trin 2.
Rækkerne bliver altså `stale` efter 7 dage og ligger derefter fast for evigt som
`stale` i stedet for at blive lukket. Det er ikke en blokering — `stale` er ikke
i `surface_active_statuses`, så reglen fyrer ikke på dem — men det er en
ophobning der vokser med ~170 rækker i døgnet.

## Den samlede konklusion

Reglen er defekt i sin **betingelse**, ikke i sin kæde. Kæden virker: signal
oprettes, flade bygges, sweep kører, stale-markering falder om 5 dage.

Det der er galt er at reglen behandler et signal med
`execution_veto_state: not-authorized` som en critical-blokering. Det er den
eneste ændring der er værd at lave, og den kræver Bjørns godkendelse fordi den
rører regel-laget.

Den sekundære mangel — ingen `stale → closed` for denne familie — er kosmetisk
ophobning, ikke en funktionsfejl.

## Overvejede alternativer

**Stabil domain_key på tværs af kørsler.** Fravalgt: det ville gøre 339
historiske hændelser til én rullende række og fjerne sporet af hvornår
contradiction faktisk opstod. Open-loop-familien har samme 1:1-design med vilje,
og den er sund — fordi den har en lukkevej, ikke fordi dens nøgle er stabil.

**Sætte `active=False` ved generering.** Fravalgt: signalet beskriver en reel
tilstand i den kørsel der genererede det. At undertrykke det ved kilden ville
skjule data for at undgå en regel-fejl — det er at rette symptomet.

**Bygge `stale → closed` med det samme.** Fravalgt indtil videre: det er
kosmetisk ophobning, ikke en blokering, og opgaven kræver udtrykkeligt ingen
kodeændring uden Bjørns ord.

## Filer

- `core/services/rule_definitions.py:232` — reglen
- `core/services/executive_contradiction_signal_tracking.py:331` — `_SPEC`
- `core/services/signal_tracking_framework.py:496` — `build_surface` → `refresh_statuses`
- `core/services/open_loop_signal_tracking.py:33-34` — to-trins lukning til sammenligning
