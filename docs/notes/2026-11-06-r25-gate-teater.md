# R2.5-gaten: ægte eller teater? (6/11-2026)

**Dom: gaten er ÆGTE. Ikke teater.** Problemet er (b) gatens besked/optælling i
én bestemt situation — parallelle værktøjskald — ikke (a) og ikke (c).

## Målt (jarvis.db, 6/11-2026)

| Spor | Tal |
|---|---|
| `events.kind='r2_5_gate.blocked'` | 485 |
| `r2_5_gate.mutation_refused` | 363 |
| `r2_5_gate.released` | 429 (400 `kig_tilbage`, 29 `udløbet`) |
| `veto_events` feeling=`r2_5_gate`, blocked | 627 (bash 549, edit_file 56, memory_upsert_section 14, write_file 7) |
| `central_incidents` nerve=r2_5_gate, kind=gate_fired | 139 totalt siden 25/9 |

Kommentaren i `tests/test_r2_5_blocking_gate.py:62` («0 forekomster over 738.510
events») er **forældet**: den stammer fra før håndhævelsen (19/9) og beskriver
tilstanden da gaten kun var prompt-tekst. Den er ikke længere sand.

## 1. Indgangsbetingelsen — kan den opfyldes?

Ja, og den opfyldes dagligt. `r2_5_blocking_gate.py:222-232` (tærskel) og
`:236-249` (heed_rate). Blokken sættes når
`failed>=1 ELLER unverified_effective >= min(tier-tærskel, ceiling=5)` OG
`heed_rate(24t) < 0.4` OG cooldown 60s er ude.

Kl. 05:16:20 6/11: `unverified_effective=5 >= 5 (tier=fast)`, `heed_rate=0.376 < 0.4`
→ `r2_5_gate.blocked`. Aktivitetsloftet (`settings.py:44`, 5) er det der gør
det opnåeligt: uden det ville tier=fast kræve 8.

Svaghed (ikke teater): heed_rate sad på 0.376 mod grænsen 0.4 — gaten er
knap-tændt. Falder heed_rate over 0.4, går den i `heed_rate ok` og blokerer
intet. Det er en designvalg, men det betyder at gaten slukker sig selv når
den virker.

Håndhævelsen: `r2_5_haandhaevelse.afvis_mutation` (`:207`) kaldes fra
`simple_tool_executor.py:205-206` og returnerer `status=gate_blocked`.

## 2. gate_enforce (info) vs gate_fired (error)

Forskellige ting, ikke «slipper igennem» vs «blokerer»:

* `gate_enforce` (`gate_shadow.py:91`) er governance-hændelser fra
  *andre* gates' shadow/enforce-lag. Ikke R2.5's blokering. R2.5 har ingen
  `gate_enforce`-incidents.
* `gate_fired` (`r2_5_haandhaevelse.py:271`) udløses af **2. afvisning i samme
  blok** (`:252`, `antal >= 2`). Den er altså ikke «gaten blokerer» — hver
  afvisning er allerede sket. Den er «han prøvede igen».
* 108 vs 6 siger derfor intet om at gaten «mest observerer».

## 3. De 7 overrides på (edit_file, "r2_5_gate")

Overrides er en **anden vej**, ikke bevis for at tærsklen nås.
`veto_gate._adaptive_threshold` (`veto_gate.py:617`) = base + `_override_lift`
− honored·dæmpning; kun brugt af `check_veto` for de følelser
`pushback._affective_pressure` producerer. `r2_5_gate` er en nerve, ikke en
følelse → tærsklen beregnes (summaries, `veto_gate.py:1017`) men afgør intet.
R2.5 beslutter på `_afvist_i_blokken` + `_blok`, ikke på den adaptive tærskel.
`tests/test_honored_kobling.py:158` har ret. De 68 `overridden_by_user`
(10/10–3/11) er `gate_override`-one-shots (`r2_5_haandhaevelse.py:223`).
Læringssløjfen for r2.5 er således død kode — men gaten er det ikke.

## 4. Konklusion: (b), snævert

**(a) adfærd:** delvist. Kl. 05:16 blev begge bash-kald afvist med 29 ms
mellemrum (`05:16:20.322` / `.351`, tool_use_id `call_00_…` og `call_01_…`) —
det er ét parallelt batch. Jeg kunne ikke have læst afvisning #1 før #2 gik
af sted. Det var ikke «gentagelse uden at læse tilbage».

**(b) beskeden/optællingen:** her er fejlen. `afvis_mutation` tæller
`_afvist_i_blokken` pr. kald (`r2_5_haandhaevelse.py:229-231`), også for
søskende i samme batch, og `_rapporter_gentagelse` (`:252-253`, `:271`) skriver
så «mutation forsøgt igen uden kig tilbage» (severity=warning→error). Målt:
af 70 andenafvisninger lå **37 (53 %) under 1 sekund** efter den første —
parallelle søskende, ikke gentagelse. `gate_fired` overdriver altså hvor
meget han ignorerer gaten, og beskeden forklarer ikke at *hele batchet* er
afvist fordi blokken blev sat under prompt-opbygningen, før batchet startede.

**(c) betingelsen:** nej. Den er opnåelig, og den er opnået 485 gange.

## Anbefalet (ikke gjort — opgaven var kun diagnose)

1. Tæl afvisninger pr. *tur/batch* (kald-tidsstempel eller tool_use_id-gruppe),
   så `gate_fired` kun fyrer ved en reel gentagelse efter at afvisningen kunne
   være læst.
2. Skriv i afvisningsteksten at andre mutationer i samme batch også afvises.
3. Ret den forældede kommentar i `tests/test_r2_5_blocking_gate.py:62`.
4. Overvej at fjerne `feeling=NERVE`-rækkerne fra den adaptive tærskel, eller
   sige direkte at de er ren registrering — læringen virker ikke for r2.5.
