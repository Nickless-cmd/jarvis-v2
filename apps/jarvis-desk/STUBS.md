# jarvis-desk — Stub- & TODO-log

Steder hvor foundation-buildet bevidst efterlod en stub eller delvis
implementation. Skal færdiggøres i de relevante mode-specs (Chat/Cowork/Code/
Memory/Scheduling) eller egne opgaver. Opdateres løbende.

## Composer
- **Tilføj billeder og filer** (`Composer.tsx` `[+]`-menu): åbner fil-vælger, men
  selve attachment-upload til serveren er ikke wired. → Chat-spec.
- **Plugins** (`[+]`-menu): ren placeholder, lukker bare menuen. → senere.
- **Planlægningstilstand** (`[+]`-menu toggle): gemmer kun lokal state; backend
  plan-mode-flag findes ikke endnu. → Chat-spec / backend.

## Beskeder
- **Pin som kapitel** (`MessageActions.tsx`): lokal visuel markering (toggle).
  Kræver et kapitel/bookmark-koncept i backend for at være rigtigt brugbart.
  → senere.

## Sessioner
- **Session "..."-menu** (`Sidebar`): omdøb/slet kræver server-endpoints
  (kun createSession findes pt.). Eksport er klient-side. → afklar API.

## Performance
- **Virtualisering** af transcript: ikke implementeret. Store sessioner renderer
  alle beskeder på én gang (tungt ved load). memo + tool-filter afhjælper, men
  ægte fix er windowing. → constraint noteret i foundation-spec.

## Rolle-skopering (server-kontrakt)
- **Memory/Scheduling**: rolle-skopet INDHOLD (member vs owner) håndhæves ikke
  server-side endnu — kun klient-rolle eksponeret. → Memory-spec + Scheduling-spec.

## Proaktiv outreach
- jarvis-desk er request-scoped; Jarvis kan ikke nå brugeren proaktivt når appen
  er minimeret. → egen spec (Q1 i foundation-planen).
