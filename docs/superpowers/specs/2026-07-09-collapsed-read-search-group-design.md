# CollapsedReadSearchGroup: fold sammenhængende read/søge-tool-kort

**Dato:** 2026-07-09
**Status:** Godkendt design (spec 2 af 4 fra leaked-Claude-Code-læringer)
**Ejer:** Bjørn / Claude
**Kilde:** Jarvis' analyse af leaked Claude Code (`CollapsedReadSearchGroup`, `collapsedCount`)
**Afhænger af:** [[project_structured_content_blocks]] (bygger på content_json-render-modellen)

---

## 1. Problem

Når Jarvis laver mange read/søge-kald i træk (fx 10 `read_file` for at forstå en fil-struktur) vises 10 individuelle tool-kort i chatten — visuel støj der begraver det egentlige svar. Claude Code grupperer sammenhængende læse/søge-værktøjer til ét kort med en tæller (`collapsedCount`), foldbart.

## 2. Mål

Ren **desk-klient-UX**: en render-lags-transform der folder ≥3 sammenhængende read/søge-tool-kort til ét kompakt, foldbart kort ("🔍 Læste/søgte N gange"). Virker både live (streaming) og ved reload — fordi den opererer på den samme content-blok-array.

## 3. Ikke-mål (YAGNI)

- Ingen backend-ændring, ingen wire-ændring, ingen persist-ændring — ren render-transform.
- Ingen gruppering af muterende handlinger (skal altid være synlige enkeltvis).
- Ingen kill-switch nødvendig (ren visuel, klient-lokal, ikke-destruktiv). Kan valgfrit gemmes bag en desk-indstilling.
- Ingen mobil-implementering (jarvisx er tekst-only markdown — ingen tool-kort at gruppere).

## 4. Besluttede valg (brainstorm)

- **Foldbare tools (read/søge, read-only):** `read_file`/`Read`, `list_dir`, `find_files`, `grep`/search, `search_sessions`, `search_memory`, `web_search`. Kategorisering via tool-navn.
- **ALDRIG foldbare (muterende/handling):** `write_file`, `edit`, `bash`-mutationer, operator-handlinger — altid synlige enkeltvis.
- **Fold-regel:** ≥3 sammenhængende foldbare kald i træk → ét collapsed kort m. tæller. <3 → vis enkeltvis (skjul aldrig en enkelt handling).
- **Fejl-undtagelse:** et read/søge-kald der FEJLEDE brydes altid ud som synligt eget kort (fejl må aldrig skjules i "N gange"-samlingen).
- **Interaktion:** default foldet; klik folder ud til de individuelle kort (status/resultat bevaret).

## 5. Arkitektur

Ren funktion + ét komponent i desk-render-laget:

```
content_json ─► foldToolResults(blocks) ─► groupReadSearch(blocks) ─► MessageView
                (eksisterende)             (NY: gruppér read/søge-runs)
```

### 5.1 `groupReadSearch(blocks)` — ren funktion
`apps/jarvis-desk/src/lib/groupReadSearch.ts`:
- Input: `ContentBlock[]` (efter fold).
- Scan for maksimale runs af ≥3 sammenhængende `tool_use`-blokke hvis `name` ∈ READ_SEARCH_TOOLS OG `status !== 'error'`.
- Erstat hver sådan run med én ny render-blok-type `{type:'tool_group', kind:'read_search', count:N, tools:[...de originale blokke]}`.
- Kald med fejl eller ikke-foldbart navn afbryder run'et (bevares enkeltvis).
- Rent deterministisk, fuldt enhedstestbar.

### 5.2 `READ_SEARCH_TOOLS`-sæt
Konstant liste (kategorisering). Konservativ default (§4). Ukendt tool-navn → behandles som IKKE-foldbart (fail-safe: vis hellere enkeltvis end skjul noget forkert).

### 5.3 `ToolGroupCard`-komponent
`apps/jarvis-desk/src/components/.../ToolGroupCard.tsx`:
- Foldet: "🔍 Læste/søgte {count} gange" + expand-chevron.
- Udfoldet: render de originale `tool_use`-kort (genbrug eksisterende tool-kort-komponent).
- Lokal `useState` for foldet/udfoldet; default foldet.

### 5.4 Render-type-udvidelse
Tilføj `tool_group` til den RENDER-lokale blok-union (IKKE `sseProtocol.ContentBlock` som er wire/persist-formatet — dette er en ren view-transform der aldrig persisteres eller sendes). Hold transformen i view-laget så persist/wire er urørt.

## 6. Test

- `groupReadSearch` (unit): 3+ sammenhængende reads → ét `tool_group` m. count=3; 2 reads → uændret (enkeltvis); read→write→read → ingen gruppe (muterende afbryder); fejlet read midt i → bryder ud; blandet read/grep/search → grupperes sammen; tomt/ingen tools → uændret.
- `ToolGroupCard` (component): foldet viser count; klik udfolder til N kort.
- Ingen regression i eksisterende MessageView-render (tekst + enkelt-tool urørt).

## 7. Blast-radius

Nul backend, nul wire, nul persist. Kun: én ren funktion + ét komponent + en view-lokal blok-type + et wiring-punkt i MessageView (mellem fold og render). Fail-safe kategorisering (ukendt → ikke foldet). Reversibelt (fjern wiring-punkt → uændret).

## 8. Åbne detaljer til plan-fasen
- Præcist MessageView-wiring-punkt hvor blokke render-dispatches (verificér i Task 1).
- Eksakt eksisterende tool-kort-komponent at genbruge i udfoldet tilstand.
- Endeligt READ_SEARCH_TOOLS-sæt mod den faktiske tool-navne-registrering i desk.
