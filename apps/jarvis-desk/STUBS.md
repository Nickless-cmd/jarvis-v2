# jarvis-desk — hvad der stadig mangler

Steder hvor der bevidst blev efterladt en stub. **Afstemt mod koden
21/9-2026** efter Codex' punkt 5: listen kaldte fem ting for mangler som
for længst var leveret, og det gør en huskeliste værre end ingen.

Hver linje herunder er efterprøvet i koden, ikke husket. Står der noget her
om et halvt år som er lavet, er det denne fils skyld — ikke læserens.

## Stadig ikke lavet

- **Plugins i `[+]`-menuen** (`Composer.tsx:730`) er en ren attrap:
  `onClick={() => setMenuOpen(false)}`. Knappen lukker menuen og gør intet
  andet.
- **Planlægningstilstand** (`[+]`-menuen) lever kun i klienten. `planMode`
  sendes ikke med i `streamClient.ts`, og serveren kender ikke feltet — målt
  21/9-2026: nul forekomster i `routes/chat.py`.
- **Pin som kapitel** (`MessageActions.tsx`) er en lokal visuel markering.
  Der findes intet kapitel-begreb i backenden at hænge den op på.
- **Virtualisering af transcript**: ikke implementeret. Store samtaler
  renderer alle beskeder på én gang. Målt: intet windowing-bibliotek og
  ingen egen implementering i chat-komponenterne.
- **Rolle-skopet indhold** i Memory/Scheduling håndhæves ikke server-side —
  kun klientens rolle er eksponeret.
- **Proaktiv outreach fra desk**: appen er request-scoped og kan ikke nås når
  den er minimeret. (Push-vejen dækker mobilen, ikke desk-vinduet.)
- **Fejl-tilstand i de resterende lister** (Codex' punkt 2, 21/9-2026): målt
  18 datahentende lister, 14 uden fejl-tilstand. `ListeTilstand` findes nu og
  er taget i brug to steder; de øvrige tolv mangler.

## Leveret — stod fejlagtigt som mangler

Efterprøvet 21/9-2026, hver med sit bevis:

| Påstand i den gamle liste | Virkeligheden |
|---|---|
| «Mac + Windows builds» mangler | Release 0.6.64 har `.dmg`, universal-mac `.zip` OG to Windows-artefakter |
| «Ring-only systray» mangler | Puls-mærket i bakken, 40 animationsbilleder |
| Omdøb/slet af sessioner mangler endpoints | `PUT /sessions/{id}/rename` og `DELETE /sessions/{id}` findes |
| `thinking_delta` er «stadig Phase 1» | Oversættes i `visible_runs_sse_v2.py:553` |
| Attachment-vision «resterende» | Løst 11/6-2026, deployet |

De afsluttede v2-stream-afsnit er fjernet helt. En log over hvad der ER
lavet, hører til i commit-historikken; den her fil skal kunne læses som «hvad
mangler», ellers bliver den ikke læst.
