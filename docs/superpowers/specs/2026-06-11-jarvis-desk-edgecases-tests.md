# jarvis-desk — Edge-case & test-katalog (foundation)

**Status:** spec-tillæg til foundation-design
**Created:** 2026-06-11
**Formål:** Konkrete kanttilfælde foundationen SKAL håndtere, hver med en
test-assertion. Feeder direkte ind i writing-plans' TDD-trin — ingen test er
"skriv tests for ovenstående" uden at vide præcis hvad der skal hævdes.

Udledt af: liveness-state-maskinen, dagens faktiske fejl (presentation-leak,
reconcile-race, coroutine-bug), og kendte produktions-failure-modes i chat-apps.

Notation: hver række er et kanttilfælde + den forventede adfærd + hvor det testes.

---

## 1. Streaming / SSE-reducer (ren funktion `(state, event) → state`)

| Kanttilfælde | Forventet adfærd | Test |
|--------------|------------------|------|
| Stream dør midt i text-block | Partial text bevares lokalt; `status=interrupted`; **ingen auto-re-POST** (R1); "genoptag" = ny tur | reducer + useStream |
| Stream dør midt i tool_use (ufuldstændig input_json) | Tool-block markeres `status:'running'`, partial JSON bevares, ingen crash | reducer |
| `message_stop` kommer aldrig (stream lukker bare) | streamClient signalerer `interrupted` (IKKE blind reconnect — ville duplikere user-msg, R1) | streamClient |
| **Ping-watchdog: ingen event i 90s** (R2) | Watchdog emitter `hung`-status → HangPrompt; kalder IKKE abort→cancelled→onComplete | streamClient (watchdog-path) |
| Blind reconnect forsøgt på chat-lane | **Forbudt** — assertion at chat-lanen ikke re-POST'er samme besked automatisk | useStream |
| `content_block_delta` for index uden forudgående `content_block_start` | Ignorér gracefully (log), ingen crash | reducer |
| Interleaved blocks (text@0, thinking@1, text@2, tool@3) | Hver index holdes adskilt; rækkefølge bevaret | reducer |
| Ukendt `system_event.kind` | Ignorér gracefully, ingen crash | reducer |
| `message_delta.stop_reason` ukendt værdi | Behandl som `done` (afslut rent) | reducer |
| Tomt svar (`message_start`→`message_stop`, intet indhold) | `status=done`, ingen tom besked persisteres; Jarvis sagde intet | reducer + reconcile |
| Delta > 50MB (MAX_BODY_BYTES) | Droppes med log, stream fortsætter | streamClient (findes) |
| Unicode/emoji splittet over delta-grænse | TextDecoder `stream:true` samler; markdown-buffer flasher ikke | streamClient + MarkdownRenderer |
| `stop_reason: "cancelled"` (efter abort) | `status=done`/`idle`, ingen fejl-banner | reducer |

## 2. Markdown / rich-rendering (ren funktion `(content, density) → element`)

| Kanttilfælde | Forventet adfærd | Test |
|--------------|------------------|------|
| Ufærdig code-fence under streaming (` ``` ` uden luk) | Buffer holder tilbage; flasher ikke brækket; flush ved message_stop | MarkdownRenderer |
| Ufærdig inline-mark (`**fed` uden anden `**`) | Vises som rå tekst til den lukker, ingen layout-blink | MarkdownRenderer |
| Code-block uden sprog-tag | Render som plaintext, ingen crash | CodeBlock |
| Mermaid der ikke kan parses | Fallback til rå code-block + diskret "kunne ikke tegne" | MermaidBlock |
| KaTeX parse-fejl | Fallback til rå `$$`-tekst | MathBlock |
| Malformet markdown-tabel | Render bedst muligt eller som tekst, ingen crash | Table |
| **Rå HTML i markdown** | **Saniteres — ALDRIG dangerouslySetInnerHTML / rehype-raw.** XSS-vektor (tool-resultater kan indeholde fjendtligt indhold, fx web_fetch) | MarkdownRenderer (sikkerhedstest) |
| **Link-URL policy** (skarp, P2) | **Allowlist:** kun `http:`, `https:`, `mailto:`. **Blokér:** `javascript:`, `file:`, `data:`, `blob:`, custom schemes. Normalisér/parse URL før åbning; malformet URL → render som inert tekst. Klik → `shell.openExternal` med `rel="noopener noreferrer"`. Navigerer ALDRIG WebView/vindue. | MarkdownRenderer (assertion per scheme) |
| **Billede-kilde policy** (skarp, P2) | **Tilladt:** backend-attachment-URLs + eksplicit `https:`. **Blokér default:** `file:`, `data:` (medmindre internt genereret + type/størrelse-tjekket). SVG-data-URI blokeres (script-vektor). Remote img → bevidsthed om tracking/exfil. | ImageBlock (assertion per kilde) |
| Billede med brudt src | Vis alt-tekst/placeholder, ingen crash | ImageBlock |
| Meget langt code-block | Render uden at fryse UI (lazy/virtualiser hvis nødvendigt — constraint-noteret) | CodeBlock |
| Kopiér code-block | Kopierer rå kildetekst UDEN linjenumre | CodeBlock |
| Kopiér besked | Kopierer rå markdown, ikke renderet HTML | MessageRow |
| Thinking-block | Foldet sammen som default ("tænkte 3s"), klik åbner | MessageRow |
| **Tool-result injection** (P2) | Tool-navn, argumenter, stdout/stderr/result, hentet HTML (web_fetch), OG approval-tekst rendres som **inert tekst/markdown gennem SAMME sanitizer** som chat-tekst. Ingen klikbare spoofede "approve"-links; ApprovalCard-knapper er ægte UI-elementer, ikke renderet fra model/tool-tekst. | ToolCard + ApprovalCard (sikkerhedstest) |

## 3. Session / state

| Kanttilfælde | Forventet adfærd | Test |
|--------------|------------------|------|
| Session-skift midt i stream | Abort nuværende run; partial leaker IKKE ind i ny session | useStream + useSessions |
| Send mens der allerede streames | Blokeres (composer disabled) | App/Composer |
| **Reconcile-race: server ikke persisteret ved session-reload** | Stream-blocks er sandhed til server bekræfter; blank-load ALDRIG (dagens bug) | reconcile |
| Optimistisk bruger-besked + stream fejler | Bruger-besked bliver stående; tilbyd retry; mist aldrig | SessionContext |
| `create()` fejler | Fejl-banner, ingen halv-oprettet session i UI | useSessions |
| Tom session-liste | Empty-state ("Hej. Skriv hvad du arbejder på."), ingen crash | ChatView |
| Aktiv session slettet andetsteds | Graceful: fald tilbage til liste/empty, ikke brækket | useSessions |
| Session-titel ændrer sig server-side (auto-titel) | `refresh()` opdaterer; klient fryser aldrig titel | useSessions |

## 4. Auth / rolle

| Kanttilfælde | Forventet adfærd | Test |
|--------------|------------------|------|
| whoami fejler ved boot (offline) | Cache-first sidste-kendte rolle; app booter stadig | SettingsContext |
| Token udløber midt i session (401) | `AuthError` → tydelig "log ind igen", session-tekst bevares | api + streamClient |
| Intet/ugyldigt token | SetupScreen, ikke brækket tom app | App |
| Rolle-downgrade (var owner, nu member) | UI re-gater: owner-only flader/knapper forsvinder | rolle-gate |
| **Member prøver owner-only read (manipuleret klient)** | **Server returnerer 403, ikke filtreret 200** (klient er ikke grænsen) | server-kontrakt (Memory/Scheduling-spec) |

## 5. Liveness / cancel

| Kanttilfælde | Forventet adfærd | Test |
|--------------|------------------|------|
| `abort()` når run allerede er færdigt | Idempotent no-op; ingen fejl | useStream |
| `abort()` POST fejler (netværk) | Abort stadig lokalt; UI går til idle | useStream |
| Hang ved 90s, men event ankommer under HangPrompt | Recover: tilbage til `working`, skjul prompt | liveness-maskine |
| Elapsed-timer på tværs af reconnect | Akkumulerer korrekt, nulstilles ikke ved reconnect | liveness-maskine |
| Vindue lukkes midt i stream (P3 — testbar mekanik) | **Main-process** ejer aktivt `run_id` (renderer sender det via IPC ved run-start/-slut). `before-quit`/`close` i main kalder cancel-endpoint FØR vindue destrueres (renderer-fetch er upålidelig ved shutdown). Fallback: persistér aktivt run_id; ryd op (cancel) ved næste opstart hvis det stadig er åbent. | Electron main (lifecycle) |
| Window ude af fokus + done/approval | `needsAttention` → dock-badge + notifikation | StreamContext |

## 6. Approval

| Kanttilfælde | Forventet adfærd | Test |
|--------------|------------------|------|
| Approval-request men bruger lukker vinduet | Server-timeout (5 min) håndteres; ved genåbning vis status | ApprovalCard + server |
| Approve/deny POST fejler | Retry-mulighed; kortet forbliver interaktivt | ApprovalCard |
| Flere approval-requests i kø | Hver vises som eget kort, løses uafhængigt | reducer |
| Member ser approval-kort (ikke owner) | Read-only (ingen approve-knap); owner gates server-side | rolle-gate |

## 7. Window / Electron / config

| Kanttilfælde | Forventet adfærd | Test |
|--------------|------------------|------|
| Config-fil mangler/korrupt | Falder tilbage til defaults → SetupScreen, ingen crash | SettingsContext |
| **Composer min-height bug** (kendt) | Composer altid synlig/brugbar uanset vindue-højde | Composer (layout) |
| Meget smalt vindue | Responsivt; sidebar kan kollapse | shell (manuel/snapshot) |
| To app-instanser | Single-instance lock (Electron); anden instans fokuserer første | Electron main |
| Send-fejl | Composer-tekst bevares, mist aldrig det skrevne | Composer |

---

## Test-stack & konventioner

- **Vitest** + React Testing Library (matcher Vite).
- **Reduceren testes som ren funktion** — ingen mocks, bare `(state, event) →
  state` over hele sekvenser. Det er det billigste, mest værdifulde testlag.
- **Rich-komponenter** med fixtures; snapshot kun hvor stabilt, ellers
  eksplicitte assertions (fx "ufærdig fence → ingen `<pre>` endnu").
- **Sikkerhedstests eksplicit**: XSS-sanitering + ekstern-link-håndtering er
  ikke "nice to have" — de er prod-gates for en multi-user app.
- **Ingen E2E i foundation** — kommer når Chat-mode er fuld.

## Prioritering (hvilke der er prod-gates vs nice-to-have)

**Prod-gates (skal være grønne før release):**
- Reconcile-race (dagens bug må ikke gentage sig)
- Partial-besked overlever stream-død
- XSS-sanitering + ekstern-link
- Server-cancel idempotens
- Auth 401 midt i session uden tab af tekst

**Vigtige men ikke release-blokerende:**
- Markdown fallback-grene (mermaid/katex fejl)
- Hang-recovery
- Composer min-height

Resten er robusthed der gør appen Claude Desktop-klasse, men hver enkelt
blokerer ikke en intern alpha.
