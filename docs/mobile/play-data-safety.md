# Play Console — Data Safety (#5)

> Udfyldt 28/9-2026. Dette er **svararket** til Play Consoles «Data safety»-formular.
> Formularen udfyldes i konsollen; her ligger de præcise svar og begrundelserne,
> så de kan kopieres ind uden at gætte — og revideres når appen ændrer sig.

## Forudsætning: hvad appen faktisk gør

Verificeret mod koden 28/9-2026. Uden det her er resten gætværk.

- **Ingen analytics, ingen sporing, ingen annoncer.** `apps/mobile/package.json`
  har ingen Sentry/Amplitude/Mixpanel/Segment/Firebase-analytics. Kun
  `@react-native-firebase/messaging` — og det er til push, ikke til måling.
- **Alt går til brugerens egen server.** Appen er en klient; der er ingen
  srvlab-cloud, der opsamler data.
- **Lyd transskriberes lokalt** på serveren (`faster-whisper`). Optagelsen
  forlader ikke brugerens eget setup.
- **Alt er valgfrit undtagen samtalen selv.** Placering, kamera, mikrofon og
  baggrundsplacering kan slås fra i indstillingerne.

---

## Svar pr. datakategori

Play spørger for hver kategori: **indsamles?** · **deles med tredjepart?** ·
**behandlingsformål** · **valgfrit?**

| Kategori | Indsamles | Deles | Formål | Valgfrit |
|---|---|---|---|---|
| **Placering → Omtrentlig** | Ja | Nej | App-funktionalitet | **Ja** |
| **Placering → Præcis** | Ja | Nej | App-funktionalitet | **Ja** |
| **Personlige oplysninger → Navn** | Ja | Nej | App-funktionalitet, Kontostyring | Nej |
| **Personlige oplysninger → Bruger-ID'er** | Ja | Nej | App-funktionalitet, Kontostyring | Nej |
| **Beskeder → Andre beskeder i appen** | Ja | **Ja** | App-funktionalitet | Nej |
| **Lyd → Stemme- eller lydoptagelser** | Ja | Nej | App-funktionalitet | **Ja** |
| **Fotos og videoer → Fotos** | Ja | **Ja** | App-funktionalitet | **Ja** |
| **Enheds- eller andre ID'er** | Ja | **Ja** | App-funktionalitet | Nej |

### Bemærkninger til de enkelte svar

**Placering (begge).** Kræver at brugeren aktivt slår det til. Baggrundsplacering
er en separat tilladelse, der skal bekræftes særskilt af Android. Data forlader
ikke brugerens eget setup — «deles» = Nej.

**Beskeder → deles = Ja.** Chat-teksten sendes til en sprogmodel-udbyder
(DeepSeek, OpenRouter eller OpenAI) for at kunne besvares. Det er en teknisk
nødvendighed, ikke et valg — og det **skal** erklæres som deling, ellers er
formularen usand. Formålet er app-funktionalitet, ikke reklame eller analyse.

**Lyd.** Transskriberes lokalt. Optagelsen sendes ikke til nogen tredjepart →
deles = Nej.

**Fotos → deles = Ja.** Når et billede sendes med en besked og skal beskrives,
går det til en sprogmodel-udbyder (vision). Samme begrundelse som beskeder.

**Enheds-ID'er → deles = Ja.** Push-token gives til Google (Firebase Cloud
Messaging) for at kunne levere notifikationer. Det er selve mekanismen for
Android-push og kan ikke undgås, hvis notifikationer skal virke.

---

## Sikkerhedspraksis

| Spørgsmål | Svar | Begrundelse |
|---|---|---|
| Krypteres data under overførsel? | **Ja** | HTTPS/TLS hele vejen |
| Tilbyder appen en måde at anmode om sletning? | **Ja** | Datastyring-skærmen: lagvis sletning + eksport |
| Er data krypteret i hvile? | **Nej** *(for ejeren)* | Se nedenfor — dette er det ene svar der ikke må pyntes |
| Er appen målrettet børn? | **Nej** | — |
| Er data uafhængigt valideret mod en sikkerhedsstandard? | Nej | Ikke relevant |

### Det svære svar: kryptering i hvile

Play spørger, om data er krypteret i hvile. Svaret er **Nej**.

`core/services/encryption.py` §16.2 undtager eksplicit ejerens egen workspace:
data for andre konti er krypteret, men ejerens er ikke. Og i praksis er ejeren
den eneste bruger af denne app.

Det er den samme fælde som UI-teksten i `DataControlsScreen` faldt i, og som blev
rettet samme dag (commit `b9c41671c`): en påstand om kryptering, der ikke gælder
for den, der læser den. Her må man ikke svare «Ja» for at gøre formularen nem at
komme igennem. Et forkert svar her er en falsk erklæring til Google.

Sættes der kryptering af ejerens workspace op senere, ændres svaret til «Ja» —
og politikken skal følge med.

---

## Hvad der stadig mangler (uden for formularen)

1. **Privatlivspolitik-URL** indsættes i Play Console → *App content*:
   `https://api.srvlab.dk/privatlivspolitik.html`
2. **Baggrundsplacering-erklæring** — separat formular, kræver en video der viser
   hvorfor appen har brug for det.
3. **Demo-adgang til reviewer.** Appen kræver en token til en selvhostet server.
   Uden testadgang afvises den som «ikke funktionel». Det er en konkret ting at
   løse før indsendelse.
