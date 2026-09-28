# Signering af mobil-appen

> Skrevet 28/9-2026, da release-APK'en blev undersøgt mod Google Plays krav.
> Status: **upload-nøglen er ikke taget i brug endnu.** Release signeres
> fortsat med debug-nøglen, med vilje.

## Kort

| Nøgle | Fil | Bruges til | I git? |
|---|---|---|---|
| Debug | `android/app/debug.keystore` | sideload til egen telefon, instrumenterings-tests | **ja** — den er offentlig |
| Upload | `android/app/jarvis-upload.keystore` | AAB'er til Google Play | **nej** — gitignored |

## Hvordan det hænger sammen

`android/app/build.gradle` læser `android/keystore.properties` ved build:

- **Findes filen** → `signingConfigs.release` defineres, og release-APK'en
  signeres med upload-nøglen.
- **Findes den ikke** → `signingConfigs.release` findes ikke, og release falder
  tilbage til debug-nøglen.

Fallbacken er der for to grunde: en frisk klon skal kunne bygge uden at have
nøglen, og Bjørns installerede app skal ikke brække midt i en almindelig
opdatering.

## ⚠️ Når upload-nøglen tages i brug

**Android opdaterer kun en app, hvis den nye APK er signeret med samme
certifikat som den installerede.** Skifter certifikatet fra debug til upload,
kan den nye APK **ikke** lægges ovenpå den gamle. Telefonen skal ryddes:

```bash
adb uninstall dk.srvlab.jarvis.mobile
adb install -r apps/mobile/android/app/build/outputs/apk/release/app-release.apk
```

App-data (login-token, indstillinger) ligger i secure store og forsvinder ved
afinstallering. Regn med at logge ind igen bagefter.

Det er derfor skiftet er en **bevidst handling** og ikke sker af sig selv: sæt
`keystore.properties` op, når du er klar til at rydde telefonen.

## Nøglen er permanent

Upload-nøglen kan ikke genskabes. Mister man den, kan appen aldrig opdateres på
Play igen — man må udgive en ny app under et nyt pakkenavn.

**Back den op to steder, uden for repoet.** F.eks. en krypteret kopi i
password-manageren og én på et drev der ikke er i huset.

`keystore.properties` indeholder passwordet i klartekst og skal bakkes op
sammen med `.keystore`-filen — de to hører sammen.

## Generér nøglen

```bash
cd apps/mobile/android/app
keytool -genkeypair -v \
  -keystore jarvis-upload.keystore \
  -alias jarvis-upload \
  -keyalg RSA -keysize 2048 -validity 10000
```

`-validity 10000` (~27 år) er Googles anbefaling — en udløbet nøgle kan ikke
fornyes uden at udgive en ny app.

Skriv derefter `android/keystore.properties`:

```properties
storeFile=jarvis-upload.keystore
storePassword=<password>
keyAlias=jarvis-upload
keyPassword=<password>
```

## Verificér hvilken nøgle en APK er signeret med

```bash
apksigner verify --print-certs app-release.apk
```

Debug-nøglen har `CN=Android Debug`. Alt andet er upload-nøglen.

## AAB til Play

```bash
cd apps/mobile/android && ./gradlew :app:bundleRelease
```

AAB'en lander i `app/build/outputs/bundle/release/`. `eas.json`s `production`-profil
peger også på `app-bundle`, hvis EAS bruges i stedet.

## Kendt forbehold

`testBuildType "release"` (se `knib-harness.md`) kræver at test-APK'en deler
certifikat med app-APK'en. Det holder så længe begge signeres ens — også når
upload-nøglen tages i brug, fordi begge så bruger den.
