# Mobil Direct Reply (statusbar-svar) — Design

**Dato:** 2026-06-20
**Status:** Godkendt design, klar til implementering
**Reference:** FEATURE 3 i `project_mobile_backlog` / Jarvis' note (n1781906203253). Pivot fra chatboble (Samsung renderer ikke Bubbles — `reference_samsung_no_bubbles`).

Lader Bjørn svare Jarvis **direkte fra notifikationen i statusbaren** uden at åbne appen — som beskeder fra andre Android-apps. Ren klient-side; ingen backend-ændring.

## Bærende fund (verificeret)

- **notifee bygger allerede vores notifikationer** (`push.ts display()`), og understøtter RemoteInput-svar via `android.actions` + `input` → ingen native kode.
- **`/chat/stream/v2` spawner et detached, server-autoritativt run eagerly** i handleren (chat_stream_v2.py linje ~120-128, FØR StreamingResponse returneres). En baggrunds-POST starter derfor runnet server-side selvom klienten ikke læser streamen → fire-and-forget virker.
- **Svar leveres tilbage** via den eksisterende FCM `answer_ready`-push (runnet finisher server-side → push) → ny notifikation, som også får en svar-knap → svar-loop fra statusbaren.

## Komponenter

**`src/lib/replyToSession.ts`** (ren, testbar):
- `replyToSession(config, sessionId, text): Promise<boolean>` — `fetch`-POST til `/chat/stream/v2` med body `{message, session_id, mode:'chat', approval_mode:'ask', thinking_mode:'think', model:'', provider_choice:'', attachment_ids:[]}` + auth-header. Afventer kun responsen (headers = run spawnet). Returnér true ved ok, false ved fejl (sluger). Læser IKKE SSE-streamen.

**`src/lib/push.ts`** (display):
- Tilføj `android.actions: [{ title: 'Svar', pressAction: { id: 'jarvis-reply' }, input: { allowFreeFormInput: true, placeholder: 'Skriv til Jarvis…' } }]`. `session_id` ligger allerede i `data`.

**`index.js`**:
- `notifee.onBackgroundEvent(async ({type, detail}) => …)` + samme i forgrunden (eksisterende `attachForegroundHandler` udvides): på `EventType.ACTION_PRESS` && `detail.pressAction.id === 'jarvis-reply'`:
  - `const text = (detail.input ?? '').trim()`; hvis tom → return.
  - `const config = await loadAuthConfig()`; hvis ingen → return.
  - `const sid = detail.notification?.data?.session_id`; hvis ingen → return.
  - `await replyToSession(config, sid, text)`.
  - Opdatér notifikationen (samme id) til "Sendt ✓: <text>" (eller annullér).

## Dataflow

1. Jarvis svarer → FCM-push → notifee viser notifikation **med svar-knap**.
2. Bjørn skriver i statusbaren → `onBackgroundEvent` ACTION_PRESS → `replyToSession` POST'er → run spawnes server-side → notifikation → "Sendt ✓".
3. Run finisher server-side → FCM `answer_ready`-push → ny notifikation (med svar-knap igen).

## Fejlhåndtering

- Ingen auth / intet session_id / tom tekst → stille return (ingen crash).
- `replyToSession` fetch fejler → returnér false; opdatér notifikation til "Kunne ikke sende" (best-effort).
- Forgrund-svar (appen åben): samme handler via `onForegroundEvent`.

## Test

- jest `replyToSession.test.ts`: mocket `fetch` — korrekt URL (`/chat/stream/v2`), method POST, auth-header, body indeholder message+session_id; fetch-fejl → false; ok → true.
- Eksisterende ~115 jest grønne; `tsc --noEmit` rent.
- Manuelt på S24: svar fra statusbaren → besked når Jarvis → svar kommer som ny notifikation.

## Filer

**Ny:** `src/lib/replyToSession.ts` (+ `.test.ts`).
**Modificeret:** `src/lib/push.ts` (svar-action), `index.js` (background/foreground action-handler).

## Ikke i scope (YAGNI)

- Rich-attachments i svar; model-vælger i notifikationen (bruger sessionens default).
- Direct reply til reminder/initiative-notifikationer ud over answer_ready (samme mekanik kan udvides senere).
