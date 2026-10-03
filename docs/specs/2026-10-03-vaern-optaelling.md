# Værnene — optælling efter hvad de udretter

Målt 3/10-2026. Udløst af Bjørns stående regel: *alt der ikke er skrevet fra hans
composer skal mærkes som fra systemet* — og hans iagttagelse at mange værn **kun
bør være advarsler**, men kan ende med at blokere eller starte nye runder.

Akslen er **ikke hvad værnet siger, men hvad det skal udrette.**

## De tre klasser

| Klasse | Definition | Hvor teksten må lande |
|---|---|---|
| **1 — skal handle** | Runnet dør eller hænger uden det | Begge, men MÆRKET |
| **2 — skal advare næste runde** | Modellen skal vide det for ikke at gentage sig | Followup, MÆRKET, tredje person, ingen invitation |
| **3 — kun til Bjørn** | Et menneske skal forstå hvorfor; modellen vinder intet | Skærmen ALENE, fjernet fra model-historikken |

## Optællingen

| Værn | Sted | Udretter | Lander | Jeg-form | Invitation | Fjernes fra historik | Bør være | Status |
|---|---|---|---|---|---|---|---|---|
| `_empty_guard_msg` | `visible_runs.py:4379` | **holder runnet i gang** — DeepSeek stopper tavst uden besked | skærm | nej (engelsk) | «try again» | n/a | **1** | nødvendig, men umærket og på engelsk |
| `_hp_note` | `:4092` → `hollow_promise_round.py:83` | intet — melder EFTER to tvungne forsøg | skærm **+ followup** | **JA** | **JA** «Sig til, så tager jeg den forfra» | **nej** | **2** | **ØDELAGT** |
| `_exhaust_note` | `:3763` | intet — melder at forbindelsen svigtede | skærm **+ followup** | **JA** | **JA** «sig til» | **nej** | **3** | **ØDELAGT** |
| `_stop_note` | `:4204` | intet — forklarer hvorfor svaret er kort | skærm **+ followup** | **JA** | **JA** «Sig til, så tager jeg den derfra» | **nej** | **3** | **ØDELAGT** |
| `_guard_msg` | `:4531` | intet — melder tool-call-loop | skærm | **JA** | nej | n/a | **3** | i orden, bør mærkes |
| `interruption_notice` | `interruption_notice.py` | intet — melder afbrydelse | skærm | JA | JA | **JA** | **3** | **KORREKT** |
| R2 `verification_gate` | `verification_gate.py` | advarer, blokerer ikke | — | nej | nej | n/a | mekanisme | i orden |
| R2.5 `r2_5_blocking_gate` | `r2_5_blocking_gate.py` | **nægter mutation** | — | nej | nej | n/a | mekanisme | i orden |
| `loop_nudge` | `:4498` | blød, bærer opmærksomhed | — | nej | nej | n/a | mekanisme | i orden |

## Svaret findes allerede i huset — anvendt på ÉT værn

`interruption_notice.py` gør præcis det rigtige, og dens første linje siger det:

> «Afbrydelses-noten — en besked til **MENNESKET**, ikke til modellen.»

Den har en note i jeg-form MED en invitation («Skriv bare igen, så samler jeg
tråden op») — og så `strip_interruption_notices()`, der **fjerner den fra den
historik modellen får**. Verificeret live: kaldt fra
`prompt_sections/transcript_sections.py:295-296`, altså koblet og ikke død kode.

**Det er mønsteret.** Tre værn mangler det.

## Hvad der skal gøres, per værn

**`_hp_note` → klasse 2.** Den eneste der skal have NY tekst frem for blot at
blive strippet, fordi modellen *skal* vide det for ikke at gentage sig.

Og her er det vigtigste fund: **modellen får i dag aldrig at vide det med ord.**
Forløbet er:

```
runde N    lover, kalder intet   → note_detected udsender et EVENT, modellen får INTET
runde N+1  next_round_tool_choice TVINGER et værktøjsvalg → ingen ord
runde N+2  tvinges igen                                   → ingen ord
slut       hollow_promise_note taler  → «Sig til, så tager jeg den forfra»
```

Modellen tvinges i tavshed to gange og får først ord når det er for sent — og de
ord er netop dem der kan starte en runde i Bjørns navn.

Så «advarsel til næste runde» er **ikke en flytning, det er en tilføjelse**.
Den advarsel findes ikke. Den vil være strengt bedre end tvangen alene: den
fortæller modellen hvad der gik galt *mens den stadig kan rette det*. Formen:

```
[SYSTEM — IKKE FRA BJØRN]
Et værn observerede: forrige runde lovede en handling og kaldte nul værktøjer.
Dette er en iagttagelse, ikke en anmodning. Ingen har bedt om en gentagelse.
```

Tredje person. Ingen «sig til». Og den eksplicitte linje om at det ikke er en
anmodning — uden den kan en systembesked blive et «ja».

**`_exhaust_note` + `_stop_note` → klasse 3.** Ingen ny tekst. De skal BLIVE i
jeg-form med deres invitation, fordi Bjørn skal kunne læse dem som Jarvis' ord —
og de skal strippes fra model-historikken, præcis som afbrydelses-noten.
Mekanisk: samme mønster, samme sted i `transcript_sections`.

**`_empty_guard_msg` → klasse 1, bliver.** Bjørn 3/10: «en nødvendighed, det kan
starte eller holde et run i gang fordi DeepSeek har det med at stoppe uden at
sende en besked». Den bliver som mekanisme, men skal mærkes, så Jarvis ved at
runden blev **tvunget af et værn** og ikke bedt om af Bjørn.

Og den er på **engelsk** modsat resten af huset — sigende for at den blev
tilføjet for sig som en nødvendighed og aldrig harmoniseret.

**`_guard_msg` → klasse 3.** Lander kun på skærmen, så den er ikke farlig. Men
den er i jeg-form og bør mærkes af samme grund.

## To ting om selve målingen

Min automat fandt **stederne** pålideligt (ni injektions-udtryk i
`visible_runs.py`) men klassificerede **teksten** upålideligt: for `_hp_note`
kommer teksten fra en funktion, og min strengsøgning fangede funktionens
docstring i stedet for dens returværdi — så den rapporterede «ingen jeg-form» om
en note der ordret siger «Jeg sagde hvad jeg ville gøre». De fire ødelagte er
derfor klassificeret ved **læsning**, ikke ved mønstersøgning.

Og `strip_interruption_notices` blev tjekket for kaldere før den blev udnævnt til
mønstret. Det er husets hyppigste fejl at koden er rigtig og ingen kalder den;
her er den koblet.
