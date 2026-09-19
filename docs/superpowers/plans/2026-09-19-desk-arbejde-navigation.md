# Desk Arbejde Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Saml alle Arbejde-funktioner i kategoriserede, konsekvent opbyggede sider.

**Architecture:** Behold den eksisterende cowork-zonekanal og alle funktionskomponenter. Giv sidebaren et mindre sæt destinationer, map gamle zone-id'er til nye sider, og komponer eksisterende komponenter i fælles side- og sektionslayout. Læg nye styles i en selvstændig CSS-fil, fordi `app.css` er over repositoryets Boy Scout-grænse.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, CSS.

**Spec:** `docs/superpowers/specs/2026-09-19-desk-arbejde-navigation-design.md`

## Global Constraints

- Bevar `emitZone` som indgang for eksisterende kaldesteder.
- Skjul owner-only komponenter for andre roller.
- Ændr ikke backend eller godkendelsespolitik.
- Rør ikke `app.css` uden først at splitte en naturlig CSS-enhed ud.

---

### Task 1: Navigation og kompatibilitet

**Files:** `apps/jarvis-desk/src/lib/coworkZone.ts`, `apps/jarvis-desk/src/lib/coworkZone.test.ts`, `apps/jarvis-desk/src/components/shell/Sidebar.tsx`, `apps/jarvis-desk/src/components/shell/Sidebar.cowork.test.tsx`

**Interfaces:** `normalizeZone(zone: Zone): Zone` returnerer kanonisk destination; `COWORK_ZONES` er de synlige destinationer.

- [x] Skriv failing tests for alle gamle zone-id'er og for de nye grupper i sidebaren.
- [x] Kør de to relevante Vitest-filer og kontrollér forventet fejl.
- [x] Indfør kategorier og aliasmapping. Lad sidebaren markere `normalizeZone`-resultatet.
- [x] Kør de samme tests igen og kontrollér grønt resultat.

### Task 2: Samlede sider

**Files:** `apps/jarvis-desk/src/views/CoworkView.tsx`, `apps/jarvis-desk/src/views/CoworkView.test.tsx`, `apps/jarvis-desk/src/components/cowork/CategoryPage.tsx` (ny), `apps/jarvis-desk/src/styles/cowork-categories.css` (ny), `apps/jarvis-desk/src/App.tsx`

**Interfaces:** `CategoryPage` tager `title`, `description`, `children`; `CategorySection` tager `title`, `children`. `CoworkView` samler eksisterende funktionskomponenter efter spec-tabellen.

- [x] Skriv failing render-tests for Generelt, Konto og sikkerhed, Værktøjer og forbindelser og owner-only skjulning.
- [x] Kør testen og kontrollér forventet fejl.
- [x] Implementér fælles sider og sektioner; importér ny CSS i `App.tsx`.
- [x] Kør render-tests igen og kontrollér grønt resultat.

### Task 3: Agent pool og finish

**Files:** `apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.tsx`, `apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.test.tsx`, `apps/jarvis-desk/src/styles/cowork-categories.css`

**Interfaces:** Agent pool bruger de eksisterende `.mc-tab`-klasser; nøgletal får et eget grid i den nye stylesheet.

- [x] Skriv failing test, der kræver stylingsklasser på fanerne.
- [x] Kør testen og kontrollér forventet fejl.
- [x] Ret klasser og nøgletalslayout; kør testen igen.
- [x] Kør Desk-testpakken og `npm run build:renderer`.
- [x] Inspicér de samlede sider visuelt og ret eventuelle layoutbrud.
