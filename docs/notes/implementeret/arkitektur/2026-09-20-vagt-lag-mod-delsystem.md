# Note: plans, todos, goals og wakeup hører ikke til i tool-nudgen

Status: implementeret

## Problem

Bjørn spurgte 20/9-2026, mens tool-nudgen blev bygget: «hvad med regler om
self wakeup og plans og todos og goals? eller de høre ikk til der?»

Det er et rigtigt spørgsmål, for nudgen peger allerede på to af dem. Den
minder om `schedule_self_wakeup` når han starter baggrundsarbejde, og om
`flag_side_task` når han lige har læst arbejde nogen har udskudt. Derfra er
der kort vej til at lægge REGLERNE for de fire ind i vagten.

## Beslutning

Nej. Vagten er et lag, ikke et samlested.

DeepSeek-harness' struktur siger det samme uden at forklare det: `plan/`,
`todo/`, `goal/` og `schedule/` er fire selvstændige pakker, og `guard/` er
en femte ved siden af dem.

Revideret her samme dag — vi har allerede alle fire, og alle fire kan nås:

| Delsystem | Modul | Værktøjer |
|---|---|---|
| Plan | `plan_proposals` | `propose_plan` |
| Todo | `agent_todos`, `central_todo` | `todo_write` |
| Goal | `autonomous_goals`, `emergent_goals` | `goal_create`, `goal_list`, `goal_update`, `goal_decompose` … |
| Wakeup | `self_wakeup`, `session_wakeup` | `schedule_self_wakeup`, `schedule_recurring` |

Grænsen er: **en vagt må NÆVNE et værktøjsnavn som en streng, aldrig
importere delsystemet.** `scripts/verify_vagt_graenser.py` håndhæver det,
også for sen-import inde i en funktion — det er den nemmeste vej udenom.

## Overvejede alternativer

**Give nudgen en regel pr. delsystem.** Afvist, og det er den vigtigste del
af beslutningen. Jeg fjernede i dag nudgens regel 1 fordi den fyrede 7 gange
og var falsk alle 7. Fire nye regler uden en måling bag sig ville være
præcis den fejl igen, bare gange fire. Kommer der et målt, entydigt signal
for «han burde have lagt en plan», kan reglen tilføjes DA — og den vil
stadig kun nævne et værktøjsnavn.

**Lade nudgen importere delsystemerne for at spørge om tilstand** («har han
allerede en plan for det her?»). Afvist: så står reglen to steder, og den
ene er den man glemmer at rette. Vagten ser kald og resultater; det er det
den har adgang til, og det er nok til at pege.

**Samle de fire i ét «opgave»-delsystem.** Afvist. De har forskellige
levetider og forskellige ejere: en todo lever i én tur, en plan er en
kontrakt, et mål lever på tværs af uger, og en wakeup er et tidspunkt. At
slå dem sammen ville skjule præcis de forskelle.

## Konsekvenser

Nudgen kan pege på et delsystem uden at kende det. Skifter et værktøj navn,
knækker strengen synligt i vagtens konstanter i stedet for at rådne stille.

Vagten beviser at vagt-laget ikke importerer de syv navngivne moduler. Den
beviser ikke at et delsystem er rigtigt designet, og den ser ikke en vej
udenom via et tredje modul der re-eksporterer.

`VAGTER`-listen har i dag ét medlem. Kommer der flere vagter, skal de skrives
ind — og en vagt der forsvinder fra træet melder fejl i stedet for stille at
holde op med at måle noget.
