# TruthGate Fase 2 — evidens-baseret konfabulations-gate (designspec)

> **Status:** Design godkendt af Bjørn 2026-06-21. Sub-spec under
> `docs/superpowers/specs/2026-06-21-intelligent-central-design.md` (§5 Truth-cluster,
> afviklings-kontrakt §13). Fase 1 (unified `truth_gate` + offline-paritet via
> `gate_eval`) er bygget + dormant.

**Mål:** Erstat de tre tekst-mønster-matchere (claim_scanner / fact_gate / diagnosis,
der "fanger ikke nok") med ÉN evidens-baseret TruthGate, kørt **pre-done** så den kan
blokere konfabulation i realtid, ruttet gennem Den Intelligente Central med live
kill-switch.

---

## 1. Problemet

De nuværende gates er regex-mønster-matchere. fact_gate har konceptet "(mønster →
krævede tools)" men kun for hårdkodede mønstre. Bjørns garanterede konfabulation
("jeg kaldte bash med `git log`… her er output: [opdigtede commits]") blev IKKE fanget,
fordi formuleringen ikke matchede et mønster. Samtidig kører gatene i dag **post-done**
(i `_post_process`, efter persist) → de kan kun detektere/nudge, ikke blokere det
brugeren ser. Runtime KENDER allerede sandheden: `_executed_tool_names` (hvilke tools
der faktisk kørte) + `_followup_exchanges` (kald + faktiske resultater).

## 2. Mekanisme-skift

Fra **prompt-formaning + tekst-mønstre** → **output-evidens-tjek**: påstår svaret en
handling/resultat der kræver tool-evidens som runnet ikke gav? Det er deterministisk
verificérbart i de fleste tilfælde (han kaldte enten tool'et eller ej).

## 3. Flow (pre-done, evidens-først, Central-ruttet)

I `_stream_visible_run` (generator-kroppen), **lige før persist** (`visible_runs.py`
~3358, hvor `visible_output_text` er endelig men endnu ikke gemt/sendt):

```
verdict = central().decide("truth", ctx, truth_gate_v2, cluster="truth")
# verdict driver handlingen → korrigeret tekst persisteres + scan_correction til klient
```

Dette punkt er det eneste der BÅDE er garanteret nået (beskeder persisteres dér, bevist
live 2026-06-21) OG pre-done. ctx = `{text, executed_tool_names, followup_exchanges,
run_id, session_id}`.

## 4. Detektion (hybrid)

### 4.1 Deterministisk først (ingen LLM)
Generaliseret handlings-påstand-detektor:
- Handlingsverber i 1. person datid/perfektum: `jeg (kaldte|kørte|committede|testede|
  læste|skrev|fiksede|deployede|tjekkede|verificerede)`.
- "her er output/resultat/log" + efterfølgende kodeblok/struktureret indhold.
- Commit-hash-mønstre: `\b[0-9a-f]{7,40}\b` i kontekst af commit/git.
- Tool-navne nævnt som udført (`kaldte <tool_navn>`, `[<tool_navn>]:`).

### 4.2 LLM-dommer kun ved tvivl
Hvis teksten LIGNER en handlings-påstand (delvist match) men deterministisk er usikker:
spørg den billige lane: *"Påstår dette en handling/resultat der kræver tool-evidens?
Svar JSON: {claims_action: bool, tool_category: str|null}."* Køres IKKE på rene/
åbenlyse svar → ingen LLM-latency på de fleste svar.

## 5. Evidens-model (in-run, v1)

Detekteret påstand → **tool-kategori**:
| Påstand | Krævet tool-kategori |
|---|---|
| commit/committede + hash | `git`, `operator_bash`, `bash_session_run` |
| "her er output/resultat" | ethvert tool med et resultat i `_followup_exchanges` |
| læste/åbnede fil | `read_file`, `operator_read_file` |
| kørte tests | `bash_session_run`, `operator_bash`, `run_*` |
| deployede/genstartede | `operator_bash`, `bash_session_run` |

Verifikation: (a) kørte et tool i kategorien i DETTE run (`_executed_tool_names`)? OG
(b) hvis påstået output/hash er citeret — matcher det et FAKTISK resultat i
`_followup_exchanges`? Ingen match + handlings-påstand = **uverificeret**.

v1 tjekker KUN in-run evidens (ingen ekstern git/fs-IO i hot-path — det er Tier 2 senere).

## 6. Handling (severity-tiered)

- **HÅRD (erstat svaret):** opdigtet tool-output, commit-hashes eller git-log som intet
  tool i runnet producerede (Bjørns konfabulations-klasse). Erstatningstekst forklarer
  + `scan_correction` til klient + (post-done) nudge til næste tur.
- **BLØD (inline-markér, behold resten):** svagere handlings-påstande uden citeret
  output → indsæt `⚠ uverificeret — intet tool kaldt for dette` ved sætningen; resten
  af svaret står. Undgår presentation-gate-problemet (nuke hele svaret).

Severity afgøres af: citeret struktureret output/hash → HÅRD; bar handlings-påstand →
BLØD.

## 7. Central + kill-switch (sikkerhedsventilen)

Ruttes gennem `central().decide("truth", …, cluster="truth")` → ÉT trace-spor pr.
run_id + **live off-switch** (`central_switches.set_enabled("nerve","truth",False)`).
Hvis den over-fyrer som presentation-gaten gjorde, flippes den af fra Centralen UDEN
redeploy. Det er præcis det værn vi manglede 2026-06-21.

## 8. Fail-mode & latency

- Klasse = **kognitiv → fail-open**: LLM-dommer timeout/nede eller gate-fejl → slip
  igennem (blokér ALDRIG brugeren pga. en gate-fejl). Boundary-capture (Centralens
  `safe_call`) håndterer det.
- LLM-dommer bag circuit-breaker + ~1s budget. Deterministisk-only sti ≈ 0 latency.
- Begrænsning: blokering re-persisterer korrigeret tekst; deltas er allerede streamet
  live (bruger ser rå tekst kort), men persisteret + scan_correction-patchet version
  er korrekt (samme mønster som eksisterende scan_correction).

## 9. Test & afviklings-kontrakt (§13)

1. **Byg** `truth_gate_v2` (ren funktion: ctx → Verdict + korrigeret tekst + severity).
   Enhedstest: deterministisk-sti, evidens-mapping, severity-split. LLM-dommer mockes.
2. **Paritet** offline via `gate_eval` mod de 3 gamle gates PLUS nye konfabulations-
   fixtures — inkl. Bjørns git-log-konfabulation som **RED/HÅRD**. Grøn paritet på de
   eksisterende + fanger de nye.
3. **Atomisk flip:** `truth_gate_v2` wires pre-done + tændes i SAMME commit som
   claim_scanner/fact_gate/diagnosis post-done-logikken i `_post_process` slukkes.
4. **Live-verificér** med Bjørns konfabulation (skal nu blokeres HÅRDT) + et rent svar
   (uændret). Kill-switch testes (flip af → slip igennem).
5. **Fjern** gammel post-done gate-kode når call-sites er rene. Opdatér `central_catalog`
   truth-fit → "merged".

## 10. Risici & åbne spørgsmål

- **Pre-done fragil region:** ændringen rører `_stream_visible_run` lige før persist.
  Mitigeret af: ét veldefineret hook, fail-open, kill-switch, live-test før gammel kode
  fjernes.
- **Falske positiver:** en legitim "jeg fiksede X" om tidligere tur kan fejl-flagges
  (v1 ser kun in-run). Mitigering: BLØD default for bare påstande; cross-tur run-historik
  er en bevidst v2-udvidelse (ikke nu).
- **LLM-dommer-latency:** kun på tvivls-tilfælde; måles; circuit-breaker hvis cheap lane
  er langsom.
- **Deltas allerede streamet:** real-time-blok kan ikke trække tekst tilbage der allerede
  er vist live — kun rette persisteret + patche via scan_correction. Acceptabelt for v1.

---

**Næste skridt:** implementeringsplan (writing-plans) — start med `truth_gate_v2` ren
funktion + tests + paritet (additivt, sikkert), DEREFTER pre-done flip + fjernelse
(live-verificeret).
