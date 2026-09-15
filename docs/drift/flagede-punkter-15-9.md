# De flagede punkter, taget i rækkefølge

**15/9-2026.** Seks ting jeg havde flaget og ikke fået lov til at røre.

## 1 · Crash-beaconen (10.0.0.36)

To af mine tre påstande holdt. Den tredje gjorde ikke, og den retter jeg her.

**Holdt: 20 sekunder var for langsomt.** Målt over 2.091 prøver: CPU-temperaturen
sprang **≥20 °C mellem to prøver 211 gange**, største spring 29 °C. Takten er nu
5 sekunder.

**Holdt: `ambC` var en død kanal.** `acpitz` rapporterede 27,8 °C i **12 timer**
uden at rykke sig, mens CPU'en svingede fra 35 til 62 grader. Den ligner data og
er det ikke. Skiftet til `SYSTIN` fra nct6798-chippen.

**Holdt ikke: «13 af 15 spændingskanaler er frosne».** De står stille fordi
skinnerne er *regulerede* — det er hvad rask ser ud. Scriptet alarmerer i
forvejen på ATX-tolerance (3,135–3,465 V), så de er ikke pynt.

**Og en bekymring der var ubegrundet:** jeg frygtede at skrivningerne kun nåede
sidens cache og ville gå tabt ved et hårdt crash. Linje 69 har `sync -d` efter
hver skrivning.

### Hvad målingen bagefter viste

Efter 15 minutter på ny takt: 176 prøver (forventet ~180 — takten virker), og
**største spring 28 °C på 5 sekunder.**

Det er en vigtig korrektion af min egen begrundelse: jeg troede 5 s ville give
~7 °C-trin. CPU'ens termiske hastighed er hurtigere end nogen fornuftig
måletakt — 28 °C på fem sekunder er turbo-belastning, ikke kølesvigt. **Hurtigere
sampling løser altså ikke THERMTRIP-detektion.** Det tidlige varsel ligger i
pumpe-omdrejningerne (`fan5`) og `streak`-tælleren, som beaconen allerede fører.

`sysC` har indtil videre kun én værdi, men det er målt over 15 minutter —
omgivelses-temperatur *skal* stå stille så længe. `acpitz` var bevist død over
12 timer. Afventer samme vindue før jeg dømmer.

## 2 · Udgivelses-kapløbet

Mac-jobbet fejlede på 0.3.70, Windows på 0.3.71 — forskelligt job hver gang,
altså et kapløb. Tre jobs uploader til samme release, og
`softprops/action-gh-release` **henter** release'en før den uploader; netop det
opslag gav `HttpError`. Linux-filerne nåede frem begge gange.

Erstattet med `gh release upload` + fem forsøg med voksende ventetid.
`prepare`-jobbet har allerede oprettet release'en, så opslaget er overflødigt,
og `--clobber` gør en gentagelse ufarlig — også når man kører et fejlet job om.

## 3 · De tre røde tests

**`test_suggest_respects_context_tags` — forældet, rettet.** Den udskiftede
`hf_inference_tools.semantic_similarity`, men matcheren skiftede til den lokale
embedder 12/9 da HF svarede «HTTP 402: You have depleted your monthly included
credits». Testen målte en vej der ikke fandtes og fejlede på en tom liste.

Undervejs afslørede den noget mere: dens attrap gav alle «coding»-kandidater
samme vektor, så `skill name: coding-helper` vandt over `use_when: code tasks`.
Det leksikalske anker måles kun mod **vinderen**, hvis ord er
{coding, helper, name} — og forespørgslen har «code», ikke «coding». En ægte
embedder ville have valgt `use_when`. Attrappen rangerer nu som en rigtig.

**`test_execution_pilot_publishes_live_chat_event` — kapløb, rettet.** Bussen har
en skrive-tråd der batcher, og testen læste før eventet var skrevet. `flush()`
findes netop til dette — «Intended for tests» står i dens egen docstring — og
testen kaldte den ikke. Den fejlede med et bart `StopIteration`.

Vinduet var desuden `limit=8`, så udfaldet afhang af hvor meget andet der
tilfældigvis blev skrevet. Den fælde har bidt fire gange i dette hus.

**`test_reflection_prompt_bridge` — IKKE løst.** Se nedenfor.

## 4 · Den flaky test — hvad jeg fandt og hvad jeg ikke fandt

Blokken bygges korrekt (`_reflection_support_signal_instruction` returnerer
altid indholdet), men i prompten stod nogle gange kun overskriften:

    'Reflection support signal:\n\nKERNE-VÆRKTØJER (grupperet — …'

Det er en **ægte prompt-defekt**, uafhængigt af testen: en overskrift der lover
et signal og leverer intet er støj der ligner data. `apply_section_budget`
dropper nu en sektion der ville blive klippet til sin overskrift — med to
forbehold som `test_attention_budget` straks krævede: en `must_include`-sektion
må aldrig droppes, og en sektion der i forvejen kun er én linje har ingen krop
at miste.

**Men det fiksede ikke testen.** Jeg påstod det to gange og tog fejl begge gange:

| | grønne |
|---|---|
| uden budget-rettelsen | 5/6 |
| med budget-rettelsen | 4/6 |
| med profil-binding | 10/10, så 2/5 |
| sammen med `test_attention_budget` | 5/5 |

Raten varierer mellem kørsler af samme kommando. **Udelukket:** DB-isolationen
(den ER isoleret, i `/tmp/pytest-of-*`), blok-byggeren, og mine egne ændringer.
Budget-profilen afhænger af udbyder og kontekstvindue — som testen ikke bandt —
men bindingen stabiliserede den ikke. Kilden er ikke fundet.

Bindingen bliver stående alligevel: en test skal måle noget den kontrollerer,
uanset om det var kuren.

## 5-6 · Ikke rørt

**Desks sammenfoldede gruppelinje uden `+/−`** og **knib-zoom-rettelsen** —
begge er UI-arbejde der kræver at han ser resultatet. Næste tur.

**`skill_autosurface_enabled`** — afvist med begrundelse tidligere samme dag:
den styrer jarvis-code's loop, som ikke bruges, og tilladelses-listen er tom.
