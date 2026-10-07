# Værnene — optælling efter hvad de udretter

Målt 3/10-2026. Udløst af Bjørns stående regel: *alt der ikke er skrevet fra hans
composer skal mærkes som fra systemet* — og hans iagttagelse at mange værn **kun
bør være advarsler**, men kan ende med at blokere eller starte nye runder.

Akslen er **ikke hvad værnet siger, men hvad det skal udrette.**

## De tre klasser

| Klasse | Definition | Hvor teksten må lande |
|---|---|---|
| **1 — skal handle** | Runnet dør eller hænger uden det | Begge, men MÆRKET |
| **2 — skal advare næste runde** | Modellen skal vide det for ikke at gentage sig | TILFØJET i `compose_exchange_text`, MÆRKET, tredje person, ingen invitation — og IKKE i `_a_parts`, så Bjørn ikke ser en dublet |
| **3 — kun til Bjørn** | Et menneske skal forstå hvorfor; modellen vinder intet | I `_a_parts` (så den persisteres og ses), men FILTRERET ud i `compose_exchange_text` — og strippet fra historikken på tværs af ture |

## RETTELSE 3/10 — jeg havde de to lister byttet om

Første udgave af denne optælling sagde at `_all_followup_parts` er «det næste
runde LÆSER». **Det er forkert.** Verificeret i koden bagefter:

- **`_a_parts`** → `compose_exchange_text(base_parts, ...)`, hvis egen docstring
  siger: «Assistant-turen til **næste rundes model-input** = det ægte svar
  (`base_parts`) + evt. efemere decision-noter.» Den persisteres OGSÅ.
- **`_all_followup_parts`** → kun `partial_text` til cutoff/genoprettelse, og
  den trunkeres ved retry (`visible_runs.py:3707`).

Konsekvensen er at problemet er **større** end først meldt: alle fem noter
appender til `_a_parts`, så **alle fem når modellen** — ikke tre.
`_empty_guard_msg` og `_guard_msg` er altså ikke «kun skærm».

Tabellen nedenfor er rettet. Jeg stolede på mit eget dokument i stedet for at
læse sømmen, og det er samme fejl som har kostet mest i dag: et navn der lød
rigtigt (`_all_followup_parts` → «followup» → «næste runde») i stedet for at
følge variablen til dens forbrug.

## Optællingen

| Værn | Sted | Udretter | Lander | Jeg-form | Invitation | Fjernes fra historik | Bør være | Status |
|---|---|---|---|---|---|---|---|---|
| `_empty_guard_msg` | `visible_runs.py:4379` | **holder runnet i gang** — DeepSeek stopper tavst uden besked | skærm **+ model** | nej (engelsk) | «try again» | nej | **1** | nødvendig, men umærket og på engelsk |
| `_hp_note` | `:4092` → `hollow_promise_round.py:83` | intet — melder EFTER to tvungne forsøg | skærm **+ model** | **JA** | **JA** «Sig til, så tager jeg den forfra» | **nej** | **2** | **ØDELAGT** |
| `_exhaust_note` | `:3763` | intet — melder at forbindelsen svigtede | skærm **+ model** | **JA** | **JA** «sig til» | **nej** | **3** | **ØDELAGT** |
| `_stop_note` | `:4204` | intet — forklarer hvorfor svaret er kort | skærm **+ model** | **JA** | **JA** «Sig til, så tager jeg den derfra» | **nej** | **3** | **ØDELAGT** |
| `_guard_msg` | `:4531` | intet — melder tool-call-loop | skærm **+ model** | **JA** | nej | nej | **3** | **ØDELAGT** (jeg meldte den som i orden) |
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

**Det er mønsteret.** FIRE værn mangler det — og sømmen for dem er en anden
end afbrydelses-notens, se nedenfor.

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

**`_exhaust_note` + `_stop_note` + `_guard_msg` → klasse 3.** Ingen ny tekst. De
skal BLIVE i jeg-form med deres invitation, fordi Bjørn skal kunne læse dem som
Jarvis' ord.

Men sømmen er en ANDEN end afbrydelses-notens. Den strippes i
`transcript_sections` — altså i historikken på tværs af ture. Disse tre skal
også ud af **samme tur**, og dér er sømmen `compose_exchange_text`:

> «Assistant-turen til næste rundes model-input = det ægte svar (`base_parts`)
> + evt. efemere decision-noter. `base_parts` selv røres ALDRIG.»

Den funktion adskiller ALLEREDE «hvad der gemmes» fra «hvad modellen ser», og i
begge retninger: den kan tilføje noget modellen ser uden at det gemmes. Et
filter dér giver os klasse 3 (fjern fra model-input, behold i `_a_parts`) og
klasse 2 (tilføj til model-input, ikke til `_a_parts`) med ét greb.

Begge lag skal med: `compose_exchange_text` for samme tur, og
`transcript_sections` for de følgende.

**`_empty_guard_msg` → klasse 1, bliver.** Bjørn 3/10: «en nødvendighed, det kan
starte eller holde et run i gang fordi DeepSeek har det med at stoppe uden at
sende en besked». Den bliver som mekanisme, men skal mærkes, så Jarvis ved at
runden blev **tvunget af et værn** og ikke bedt om af Bjørn.

Og den er på **engelsk** modsat resten af huset — sigende for at den blev
tilføjet for sig som en nødvendighed og aldrig harmoniseret.

**`_guard_msg` → klasse 3.** Jeg meldte den først som «kun skærm, ikke farlig».
Det var forkert — den appender til `_a_parts` som de andre og når altså modellen.
Samme behandling som `_exhaust_note` og `_stop_note`.

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
