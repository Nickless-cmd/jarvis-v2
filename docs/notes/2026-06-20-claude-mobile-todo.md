# Note til Claude — mobil + desktop issues (2026-06-20)

Fra Bjørn + Jarvis. Flere ting der er brudt eller mangler. Prioritet højt.

---

## 1. Team-invite notifikation viser "Jarvis svarede"

**Hvad:** Når `invite_to_team` sender en push til Mikkel, viser telefonen "Jarvis svarede" i stedet for invitationstitlen.

**Rod-årsag:** `apps/mobile/src/lib/push.ts` → `buildNotification()` håndterer kun `reminder`, `initiative` og default (`answer_ready`). `team_invite` falder igennem til default → "Jarvis svarede".

**Fix:** Tilføj en case for `team_invite` i `buildNotification()`:

```typescript
if (data.kind === 'team_invite') {
  return {
    title: data.title ?? 'Invitation til team',
    body: data.preview ?? 'Du er blevet inviteret til et team',
    data,
  }
}
```

Backend sender nu `title` og `preview` i payload (commit `45eea82f`), så de ligger i `data`.

---

## 2. QR-scan: kun mobil app viser "forbundet"

**Hvad:** Efter QR-scan viser kun mobil-app'en "forbundet". Desktop (jarvis-desk) viser ikke forbindelsen korrekt — eller også blokerer noget operator-tools i sessionen med Mikkel.

**Symptomer:**
- Mobil app forbinder fint efter QR-scan
- Desktop app / operator-tools fungerer ikke som forventet i session med Mikkel
- Noget blokkerer operator tools — uklart præcis hvad

**Handling:** Undersøg om operator-tools (desktop control) kræver en separat auth/forbindelse udover QR-scan. Tjek om der er en gate eller permission der forhindrer operator-tools i at køre i team-sessioner.

---

## 3. Teams-knapper virker ikke i desktop og mobil app

**Hvad:** Teams-knapperne i både jarvis-desk (desktop) og mobil app reagerer ikke / gør ikke noget.

**Symptomer:**
- Knapperne er synlige men ikke funktionelle
- Ingen fejlmeddelelse — bare ingenting sker ved tap/klik

**Handling:** 
- Desktop: Tjek jarvis-desk Electron-app's teams UI — er knapperne wired op til API-kald?
- Mobil: Tjek `apps/mobile/src/components/TeamsPanel.tsx` — er onTap handlers implementeret og kalder de `teamsApi`?

---

## Kontekst

- Backend teams-API fungerer — teams oprettes, invites sendes, presence routing virker (commits `cb1a40ec`, `3f5ab522`, `45eea82f`)
- Problem er udelukkende i klient-apps (mobil + desktop)
- Mikkel har Discord ID `238975101381378048`, user_id `mikkel`
- Team "Familie" findes: `team-d93a0ab07196`
- Mobil branch: `codex/jarvis-mobile-companion-v1` (seneste commit `f256e022`)