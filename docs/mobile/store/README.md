# Play-butiksmateriale

> Oprettet 28/9-2026, da butiks-materialet blev gennemgået (#8).

Dette er de filer der uploades til Google Play Console under
*Grow → Store presence → Main store listing*. De er **ikke** en del af
appen og hører derfor ikke i `apps/mobile/assets/` — kun filerne her.

## Hvad der ligger her

| Fil | Krav | Status |
|---|---|---|
| `ikon-512.png` | 512×512, PNG (ingen alpha) | ✅ lavet |
| `feature-graphic-1024x500.png` | 1024×500, PNG/JPEG | ✅ lavet |
| Skærmbilleder | 2–8 stk., telefon | ❌ mangler |

Ikonet er skaléret fra appens eget ikon (`apps/mobile/assets/icon.png`,
1024×1024) med Lanczos — ikke genereret, så motivet matcher appen præcist.

**NB:** `apps/jarvisx/assets/icon-512.png` er et *andet* ikon (hvid EKG-linje
på sort). Det er JarvisX' ikon, ikke mobilappens. Brug ikke det til Play.

## Farver

Samplet fra app-ikonet, så materialet er konsistent med appen:

- Baggrund: `#0D1117`
- Accent (teal): `#49C9B8`

## Skærmbilleder — det der mangler

Play kræver **mindst 2, op til 8** skærmbilleder pr. enhedstype. Telefon-
skærmbilleder skal være mellem 320 og 3840 px på den lange led, og
stående (9:16) er standard.

De skal være **ægte** skærmbilleder af appen — Google afviser mockups der
ikke afspejler den faktiske oplevelse. Derfor kan de ikke laves her:
appen kører på Bjørns telefon, og der er hverken enhed eller emulator
tilgængelig fra serveren (verificeret 28/9: `adb devices` tom,
`phone_adb_address` peger på en nedlagt router, ingen AVD).

**Foreslåede skærme at fotografere** (dækker de funktioner der er unikke
for appen — ikke bare tomme skærme):

1. **Chatten** med et svar fra Jarvis (kernen i appen)
2. **Indstillinger** — den nye grupperede liste med værdier på hver række
3. **Sanser & privatliv** — sensor-dashboardet med risikotiers
4. **Datastyring** — de fire datalag med tællinger
5. **Hukommelse** — hvad Jarvis ved om én
6. **Arbejde** — opgaver/agent-tråde

Tag dem i mørkt tema (appen er `userInterfaceStyle: dark`), og sørg for
at statuslinjen ikke viser personlige notifikationer.
