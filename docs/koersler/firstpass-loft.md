# «Den hænger bar på tænker..» — 900 sekunder uden ét tegn

**14/9-2026.** Seks synlige kørsler døde samme aften uden at vise noget:

| start | slut | levetid |
|---|---|---|
| 20:31:57 | 20:47:04 | 906 s |
| 20:35:52 | 20:51:00 | 908 s |
| 21:59:21 | 22:14:45 | 923 s |
| 22:08:43 | 22:24:23 | 940 s |
| 22:24:26 | 22:39:32 | 906 s |

## Hvad jeg troede, og hvad der var sandt

Jeg tog fejl tre gange undervejs, og hver rettelse kom fra en måling:

1. **«Jarvis arbejder fint — se bash-kaldene.»** Jeg tilskrev `operator_bash`-kald
   hans kørsel uden at tjekke. `costs`-tabellen viste nul deepseek-kald i femten
   minutter. Kørslen arbejdede ikke.
2. **«Det er min kode i aften.»** Nej: API-processen kørte uafbrudt fra før 19:30
   til 21:44, så kørslen der virkede 20:25 og den der hang 20:31 kørte i samme
   proces med samme kode. `runtime.json` var urørt siden 07:59.
3. **«Det er de store prompts / den lange samtale.»** Nej: «Er du der?» — tre ord
   i en ny, tom session — hang i 906 sekunder.

## Hvad det faktisk er

`py-spy` fandt tråden blokeret i `ssl.read` under `iter_lines`. `ss -tin` viste
at der KOM bytes: ca. 41 hvert 8. sekund. Sporet sagde hvad de var:

    [firstpass-trace] FIRST item efter 905.6s: VisibleModelStreamDone

En strøm der lukkede helt uden indhold. De 41 bytes var keepalive, ikke tekst.

**Derfor kunne httpx' 60-sekunders læse-timeout aldrig fyre. Den måler om der
kommer BYTES. Ingen målte om der kom FREMDRIFT.**

Det er tilfældigt, ikke totalt: kl. 22:27 svarede samme udbyder på samme
spørgsmål i samme session efter **5 sekunder**, mens det første forsøg stadig
hang i baggrunden.

## Målingen fandtes allerede

`[firstpass-trace]` har hele tiden regnet tiden til første element ud — og
*logget* den. Ingen grænse, ingen handling. Husets hyppigste fejl i endnu en
form: instrumentet var der, ingen aflæste det.

## Tærsklen kommer fra data

227 første-elementer over tre døgn. De 222 sunde:

    p95   25,3 s
    p99   27,2 s
    max   40,0 s      (de seks langsomste: 26,7 27,0 27,2 30,0 33,3 40,0)

De fem syge lå alle på 900+. Der er over tyve gange mellem den værste sunde og
den hurtigste syge, så 120 sekunder er ikke et skøn — det ligger midt i et
tomrum. Tre gange luft over den værste målte sunde kørsel, og 7,5 gange
hurtigere end i aften.

## Fase-navnet løj

Hjerteslaget sendte `phase: "prompt_assembly"` uanset hvor længe der var gået.
Gættet var rimeligt da koden blev skrevet, men medianen for første element er
6,8 s — så efter ni minutter er påstanden grov. Den narrede mig selv: mit
første gæt i aften var prompt-bygning, fordi serveren sagde det.

Loopet kan ikke se hvor ventetiden ligger. Nu påstår det det heller ikke.
Ingen klient læste feltet, så ændringen brækker intet.

## Mutations-prøve

| Mutation | Udfald |
|---|---|
| loftet → 900 s (for tæt på det syge) | 1 rød |
| loftet → 30 s (under den langsomste sunde) | 2 røde |
| fasen lyver igen | 2 røde |
| udbyderens navn ud af beskeden | 1 rød |
| loftet spørges aldrig (koblingen fjernet) | 1 rød |
| pumpen standses ikke ved loftet | 1 rød |
| «usædvanlig» fyrer ved normal ventetid | 1 rød |

Koblings-testen er en kilde-vagt, ikke en ægte kørsel — loopet ligger inde i en
5.000-linjers async-generator. Den er svagere, og det står i testen. Men den
fanger præcis den fejl der ellers gør hele filen til død kode.

## Genforsøget (15/9)

Et loft giver en ærlig fejl. Et **nyt forsøg** giver et svar — og Bjørn
leverede selv beviset kl. 22:27: samme spørgsmål, nyt forsøg, svar på fem
sekunder mens det første stadig hang.

Det er delt i to, så cheap-lane ikke røres:

**Detektionen** sidder i læse-loopet i `cheap_provider_runtime_streaming.py`.
Keepalive-linjerne nåede allerede derned og blev sprunget over — de har nu et
ur på. To tilfælde dækker hinanden: linjer uden indhold fanges af tælleren,
total stilhed af httpx' egen timeout, som nu bærer samme kode. Vagten afhænger
derfor ikke af hvilken form udbyderens keepalive tilfældigvis har.

**Genforsøget** sidder i `visible_model_adapters.py`, som kun den synlige lane
bruger. Ét forsøg, samme regel som bro-failoveren.

Det er sikkert at gentage kaldet, fordi `STALL_KODE` kun rejses når
strøm-funktionen ikke har sendt ét eneste event — og hver `yield` i adapteren
drives af et event. Koden er dermed samtidig beviset for at intet er nået
skærmen.

Genforsøget står **før** bogføringen i Centralen, så et vellykket nyt forsøg
ikke efterlader en fejl-observation for noget der gik godt.

### De tre tal

    STALL_UDEN_DATA_S  <  2 x STALL  <  FOERSTE_ELEMENT_LOFT_S
           60                120              240

Loftet stod på 120 da det blev bygget alene. Med et genforsøg nedenunder ville
120 slå netop det forsøg ihjel som var ved at lykkes: 60 s til at opdage
stilheden plus 40 s (den langsomste sunde kørsel) er 100 s. Loftet er derfor
flyttet til 240 og er nu et bagstop for det den indre vagt ikke kan se.

Det han **mærker** er den indre vagt: værst 60 + 40 = 100 sekunder mod
aftenens 906. Ni gange hurtigere.

### Mutations-prøve

| Mutation | Udfald |
|---|---|
| stilheds-vagten fjernes | 1 rød |
| vagten fyrer også efter indhold (ville gentage tekst) | 1 rød |
| `_har_data` sættes aldrig | 1 rød |
| genforsøget fjernes fra adapteren | 1 rød |
| løkken fjernes | 1 rød |
| stall-tærsklen over det ydre loft | 5 røde |
| ubegrænset antal forsøg | 1 rød |

### En fejl i testen selv

Første udgave udskiftede et auth-navn jeg havde gættet på, så den målte
«auth-not-ready» i stedet for vagten. Den så rød ud af den rigtige grund og
ville have set grøn ud af den forkerte.
