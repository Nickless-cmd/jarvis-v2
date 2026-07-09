# Paste/history-store: store bruger-pastes eksternaliseres med reference

**Dato:** 2026-07-09
**Status:** Godkendt design (spec 4 af 4 fra leaked-Claude-Code-læringer)
**Ejer:** Bjørn / Claude
**Kilde:** Jarvis' analyse af leaked Claude Code (paste store, `[Pasted text #1 +10 lines]`, hash-referencer, `skipSet`)
**Mønster-genbrug:** `core/services/tool_result_store.py` (samme eksternalisering-med-reference-mønster)

---

## 1. Problem

Når en bruger paster en stor tekstblok i chatten bliver hele blokken en del af beskeden — en væg af tekst i composeren, i den persisterede besked og i historik-visningen. Claude Code eksternaliserer store pastes til en paste-store med hash-referencer (`[Pasted text #1 +10 lines]`) og resolver dem lazy; små pastes forbliver inline; race conditions undgås via en `skipSet`.

## 2. Mål

Store bruger-pastes gemmes eksternt med en kompakt reference i beskeden; små pastes forbliver inline. Spejler det eksisterende `tool_result_store`-mønster.

## 3. Besluttede valg (brainstorm)

- **Tærskel:** paste > ~20 linjer / ~2000 tegn → eksternaliseres; under → inline (uændret).
- **Genbrug tool_result_store-mønstret:** ny `paste_store.py` (`save_paste`/`get_paste`/`parse_paste_reference`), fil-baseret, reference-format `[paste:<id> +N linjer]`.
- **Eksternalisering i desk-composeren** ved paste: bruger ser straks en kompakt reference-chip (ikke tekst-væg); beskeden sendes med referencen; serveren gemmer via paste_store.
- **Model ser FULD paste-tekst som default** (paste-store er primært UI/persist-optimering, ikke kontekst-besparelse). Reference-projektion til modellen bag et flag hvis token-besparelse senere ønskes.
- **Race-sikkerhed:** hash-baseret idempotent paste-id (samme paste gemmes ikke dobbelt) — `skipSet`-ækvivalent.

## 4. Ikke-mål (YAGNI)

- Ingen eksternalisering af små pastes (inline uændret).
- Ingen ændring af eksisterende beskeder (kun nye pastes).
- Ingen default-kontekst-besparelse (fuld tekst til model med mindre flag flippes).
- Ingen mobil-composer-ændring nu (jarvisx separat; kan følge senere).

## 5. Komponenter

### 5.1 `core/services/paste_store.py` (spejler tool_result_store)
```python
def save_paste(text: str) -> str          # → paste_id (hash-baseret, idempotent)
def get_paste(paste_id: str) -> dict | None  # {id, text, line_count, created_at}
def build_paste_reference(paste_id, *, line_count) -> str  # "[paste:<id> +N linjer]"
def parse_paste_reference(content: str) -> dict | None     # {paste_id, line_count}
```
Fil-baseret i `PASTE_STORE_DIR` (som `TOOL_RESULTS_DIR`), atomisk write, best-effort read. `save_paste` hasher teksten → deterministisk id → idempotent (samme paste = samme id, ingen dublet).

### 5.2 Desk-composer paste-hook
- `apps/jarvis-desk/src/.../Composer`: `onPaste` — hvis pasted tekst > tærskel, hold teksten lokalt, indsæt en **reference-chip** i input-feltet i stedet for råteksten (viser "📋 Indsat tekst +N linjer", fjernelig).
- Ved send: POST pasten til `/paste` (server `save_paste`) → få `paste_id` → send beskeden med `[paste:<id> +N linjer]`-referencen indlejret.

### 5.3 Server — resolve + model-projektion
- `POST /paste` → `save_paste` → `{paste_id, reference}`.
- `GET /paste/{id}` → fuld tekst (lazy resolve for historik-visning).
- Kontekst-bygger: når en besked indeholder `[paste:<id>]`, ekspandér til fuld tekst FØR modellen (default), via `get_paste`. Flag `paste_inline_to_model` (default ON = fuld tekst) → OFF ville sende referencen i stedet (fremtidig token-besparelse).

### 5.4 Klient — render
- Historik: en besked med `[paste:<id> +N linjer]` viser en reference-chip; klik/hover → lazy `GET /paste/{id}` → udfold fuld tekst. Genbruger reference-parse-mønstret.

## 6. Test

- `paste_store` (unit): save→get round-trip; idempotens (samme tekst → samme id, ingen dublet fil); parse/build reference symmetrisk; ukendt id → None (fejler ikke).
- Composer (component): paste > tærskel → chip; paste < tærskel → inline tekst; chip fjernelig.
- Kontekst-projektion (unit): besked m. `[paste:<id>]` → fuld tekst når flag ON; reference når OFF; uopslåelig id → behold referencen (degradér, fejl ikke).
- Resolve-route: `GET /paste/{id}` returnerer fuld tekst; 404 på ukendt.

## 7. Blast-radius

Ny isoleret `paste_store.py` (spejler etableret mønster) + composer-paste-hook + 2 små routes + reference-render + kontekst-bygger-ekspansion (bag flag, default = nuværende adfærd hvor fuld tekst er i beskeden). Ingen ændring af eksisterende beskeder. Reversibelt (tærskel høj → ingen eksternalisering).

## 8. Åbne detaljer til plan-fasen
- Præcis composer-`onPaste`-integration + reference-chip-komponent i desk.
- `PASTE_STORE_DIR`-konfig (spejl `TOOL_RESULTS_DIR` i `core/runtime/config`).
- Hvor kontekst-byggeren samler bruger-beskeder (ekspansion-punktet) — verificér i Task 1.
- GDPR/oprydning: paste-store-retention (spejl `cleanup_old_results`).
