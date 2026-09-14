# Broen valgte den klient der forsvinder

**14/9-2026.** Bjørn: «Ham svare ikk».

## Hvad der skete

Hans telefon stod som udfører. Dispatch-loggen viste `operator_bash` hvert
tredje sekund indtil 20:37:18. Otte sekunder senere:

    jarvisx_bridge: unregistered user=… client=mobil-2j1dxlnh

og alt arbejde stoppede dødt. Desk-appen sad forbundet hele tiden — den stod
i `andre=[…]` på præcis den samme logline.

## Hvorfor telefonen vandt

`get_bridge` valgte den nyest forbundne blandt dem der melder værktøjet:

    return max(kan, key=lambda c: c.reg_seq)

Telefonen gen-registrerer hver gang appen kommer i forgrunden, så dens
`reg_seq` er altid den højeste. Reglen valgte altså systematisk den klient
der har mindst chance for at være der om et øjeblik.

Bjørn: «det sker ikk kun når skærmen går i sort men også når man bar går ud
af appen». Det er ikke en sjælden hændelse — det er hvert eneste app-skift.

## To ændringer, og de gør hver sit

**1. Kan FLERE klienter værktøjet, vælges den der ikke kan forsvinde.**
`_kan_forsvinde()` ser på `platform`: `android`, `ios`, `ipados`. Målt:
mobilen melder `android` (`apps/mobile/src/lib/broKlient.ts:233`), desk melder
`linux-x64`.

«Sidst i hånden» er stadig den rigtige regel for ENHEDS-specifikke værktøjer
— `phone_location` kan desk umuligt udføre — men dér melder kun én klient
værktøjet, så den gren når aldrig ned til præferencen.

En ukendt eller tom platform regnes som STABIL. At behandle tavshed som «kan
forsvinde» ville flytte rundt på ældre broer uden belæg.

**2. Forsvinder udføreren midt i et kald, prøves en anden klient.**
Bjørn: «Et run må aldrig dø». En præference kan gætte forkert; en fail-over
retter sig selv.

## Hvorfor fail-overen ikke måtte ligge bag `_looks_like_closed_ws`

Første udgave lagde den dér. Det var forkert af to grunde.

Den praktiske: testen ramte den aldrig, fordi `_looks_like_closed_ws` er en
**stregmatch på exceptionens tekst**. Den slags holder op med at virke i det
øjeblik et bibliotek omformulerer sin fejl — tavst, og først under en
nedbrud-situation hvor ingen kigger.

Den principielle: kan klienten ikke tage kaldet, er det ligegyldigt HVORDAN
fejlen staves. Der sad måske en anden klient hos samme bruger der kan udføre
det. Fail-overen hører til på ENHVER send-fejl.

Kun ÉT ekstra forsøg. `_evict_if_current` har fjernet den døde bro, så
`get_bridge` kan ikke give den samme igen, og en løkke over alle klienter
ville gøre et dødt kald til en runde af timeouts. En ærlig fejl er bedre end
en langsom.

## Mutations-prøve

Fire mutationer, `tests/test_bro_routing_stabilitet.py`:

| Mutation | Udfald |
|---|---|
| præferencen fjernes (`if False`) | 3 røde |
| tom platform regnes som flygtig | 2 røde |
| ingen fail-over | 1 rød |
| `len(kan) > 1` → `True` | **8 grønne — ÆKVIVALENT** |

Den sidste er ikke et testhul: med én kandidat er `stabile` enten den ene
klient eller tom, og `return max(kan, …)` dækker det tomme tilfælde. Guarden
er en kortslutning, ikke en gren.

## En fejl i testen selv

Første kørsel timede ud. Jeg læste det som «fail-overen virker ikke». Den
virkede: `deliver_result` sidder på FORBINDELSEN, ikke på registret, er async
og tager nøgleord — testen målte sin egen fejl.

Og første udgave af testen gjorde TELEFONEN død. Det tvang valget hen på
desk, så den målte præferencen én gang til i stedet for fail-overen. Nu er
det desk — altså den præferencen faktisk vælger — der er død.
