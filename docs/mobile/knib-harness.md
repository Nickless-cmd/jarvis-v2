# Instrumenterings-harness til knib-for-zoom

Måler knib-for-zoom i fuldskærms-billedvisningen på en **rigtig telefon**.

## Hvorfor det ikke kan være en jest-test

`FullscreenImagePreview` bruger `PanResponder`, som læser
`e.nativeEvent.touches`. En jest-test skal selv levere det objekt — og en test
der selv leverer inputtet kan aldrig se at INGEN leverer det i virkeligheden.

`adb shell sendevent` duer heller ikke: målt 14/9-2026 giver skrivning til
`/dev/input/event4` «Permission denied», selv om shell-brugeren ER i
`input`-gruppen og noden er `rw` for den. SELinux forbyder shell-konteksten at
røre touchscreenen. En instrumenterings-proces må injicere input, og det er
den eneste vej til et ægte to-finger-knib.

## Hvad der ligger hvor

| Fil | Rolle |
|---|---|
| `KnibZoomTest.kt` | Åbner et billede i fuldskærm, kniber, måler |
| `KnibKontrolTest.kt` | **Kalibrering** — kniber `pinchOpen` overhovedet? |
| `KalibreringsAktivitet.java` | Målestokken kalibreringen kniber på |

`testBuildType "release"` i `app/build.gradle` gør at testene kører mod den
RELEASE-app der faktisk sidder på telefonen — ikke mod en debug-build der
opfører sig anderledes. Det virker fordi release er signeret med debug-nøglen,
og instrumentering kræver fælles certifikat.

## Læs resultatet i DEN HER rækkefølge

1. **Kalibrering rød** → værktøjet kniber ikke. App-testens tal siger INTET, og
   der er intet at konkludere om appen.
2. **Kalibrering grøn, app-test rød** → appen reagerer ikke på et ægte knib.
3. **Begge grønne** → knib-zoom virker.

Uden linje 1 er app-testen et tal uden betydning. Det er ikke teori: app-testen
målte 0,00% pixelændring, og det tal kunne lige så godt have betydet at
`pinchOpen` ikke gjorde noget. Tre forsøg på en kalibrering fejlede på deres
EGEN opsætning, og hver af dem gav et tal der lignede et svar:

- Chrome + `data:`-URL — Android afviser den slags intents.
- Google Fotos — viste en velkomstskærm, ikke et gitter.
- Chrome + en side på LAN'et — stod på sin første-gangs-opsætning, og dens
  vilkår er ikke vores at acceptere på Bjørns telefon.

Derfor er målestokken skrevet i hånden og bor i test-APK'en. Den er i **Java**:
første udgave var Kotlin og crashede med
`NoClassDefFoundError: kotlin.jvm.internal.Intrinsics`, fordi aktiviteten
starter i test-APK'ens egen proces hvor Kotlins runtime ikke er på klassestien.

## Sådan køres det

```bash
cd apps/mobile/android && ./gradlew :app:assembleReleaseAndroidTest
```

```bash
adb install -r -t apps/mobile/android/app/build/outputs/apk/androidTest/release/app-release-androidTest.apk
```

```bash
adb shell am instrument -w -e package dk.srvlab.jarvis.mobile dk.srvlab.jarvis.mobile.test/androidx.test.runner.AndroidJUnitRunner
```

## To ting der spænder ben

**Play Protect** spørger ved HVER installation af test-APK'en om appen må sendes
til Google. Svar **«Send ikke»** — det er en app-binær, og den skal ikke ud af
huset. Dialogen stjæler fokus, så en test der køres umiddelbart efter en
installation fejler med «kom ikke frem».

**Testen kræver en samtale med mindst ét billede.** Den ruller selv op til 25
gange for at finde en vedhæftning, men findes der ingen i samtalen, siger den
det. `Billeder`-skærmen duer ikke som genvej: den åbner filen i en ekstern app,
ikke i den komponent der testes.

## Hvad harnesset har fundet (14/9-2026)

Kalibrering grøn, app-test rød: **appen reagerer ikke på et ægte to-finger-knib**
— 0,00% pixelændring, og billedets grænser er uændret.

En midlertidig aflæsning i komponenten viste hvorfor:
`onMoveShouldSetPanResponder` bliver **aldrig kaldt**. Trykket når slet ikke
frem til gribbetaget. Aflæsningen stod på sin startværdi efter et fuldt knib.

Et andet spor fra samme kørsel: lukkeknappen virkede ikke efter et knibforsøg.

Den nærliggende mistanke er `onStartShouldSetPanResponder: () => false`. En
prøve-rettelse (tag gribbetaget ved start når der ER to fingre, så enkelt-tryk
stadig når knapperne) er bygget, men **ikke målt** — telefonen havde ingen
samtale med et billede tilgængelig efter geninstallationen. Den måling er det
næste skridt, og harnesset kan afgøre den.
