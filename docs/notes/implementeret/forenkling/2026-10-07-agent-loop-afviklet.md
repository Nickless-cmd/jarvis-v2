---
status: implementeret
slags: forenkling
dato: 2026-10-07
forfatter: jarvis
---

# Agent-loop-ruten er afviklet

Status: implementeret

## Problem

`apps/api/jarvis_api/routes/agent_loop.py` (1.458 linjer, otte endpoints) var
den klientstyrede loop for `jarvis-code`. Bjørn 7/10-2026: «vi bruger slet ikk
jarvis-code? det er droppet... vi abrjeder kun i desk og containeren».

Målt før fjernelsen:

* **0 kald** på alle otte endpoints i hele logvinduet (3/10 → 7/10).
* Ingen klient i `apps/jarvis-desk/src` eller `apps/mobile/src` nævner nogen
  af dem.
* `jc_agent_audit`: 1.857 af 1.861 rækker er fra juli; nyeste 25/9.
* Filen bar en hårdkodet DeepSeek-default uden ejerport i sidste fallback — et
  latent hul, som begge reviews pegede på.

Klyngen hang sammen: `client_turn_live`, `client_turn_absorb` og
`jc_tool_telemetry` blev **kun** importeret af ruten, og `agent_audit.py`
hentede sin `_resolve_role` fra den. At fjerne ruten alene ville efterlade tre
døde services og et dødt import.

## Beslutning

Ruten **afvikles** — ikke «lukkes særskilt». 23 filer fjernet, 2.923 linjer.

Fjernet: `agent_loop.py`, `jc_env.py`, `agent_audit.py`, `db_agent_audit.py`,
`client_turn_live.py`, `client_turn_absorb.py`, `jc_tool_telemetry.py` plus 16
testfiler og imports/mounts i `app.py`.

Beholdt: `env_block.py` — den levende efterfølger til `jc_env.py`, brugt af
`truth_gate_v2`, `prompt_contract` og `workbench`. `jc_agent_audit`-tabellen
står urørt; kun koden omkring den er væk.

## Overvejede alternativer

* **«Lukkes særskilt»: afmontér routeren, behold filen.** Fravalgt. Det lukker
  hullet (ruten bliver unåelig), men efterlader 1.458 linjer død kode med en
  DeepSeek-default der skal revideres for evigt — og tre services som kun ruten
  kaldte. Det er præcis «to sandheder»-problemet begge reviews advarer om.
* **Patche hullet og beholde ruten.** Fravalgt: spec'ens §3 forbyder genbrug
  («må ikke genbruges som subagentmotor»), og der er ingen klient at patche for.
* **Fjerne hele klyngen uden at måle først.** Fravalgt — og det var tæt på at gå
  galt: `jc_tool_telemetry.py` har sin EGEN testsuite og ser ud som en
  selvstændig service. Først da jeg målte hvem der importerede den, stod det
  klart at ruten var eneste kalder.

## Konsekvenser

* **Hullet er lukket ved konstruktion.** Der findes ikke længere en rute der
  kan falde til DeepSeek for en anden ejer.
* `agent_turn_absorb_enabled` i `runtime.json` er nu et forældreløst flag — det
  læses ikke længere. Inert, men bør ryddes.
* **24 testfiler blev berørt.** 18 af dem fejlede i forvejen på
  `No module named 'textual'` (manglende afhængighed i dette miljø, ikke denne
  ændring); de 6 der fejlede på mit, er fjernet. Hele suiten samler nu 18.444
  tests.
* **Det jeg IKKE kan love:** at intet eksternt kalder ruterne. Målingen er 0
  trafik i logvinduet og 0 referencer i klientkoden — ikke en garanti mod en
  klient jeg ikke kan se.
