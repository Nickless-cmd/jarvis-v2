# UI Theme Lift — Teal-tinted Depth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift all non-composer UI surfaces to use the "teal-tinted depth" visual language — dark gradients, subtle teal borders, soft shadows — matching the style of the existing composer card.

**Architecture:** Pure CSS changes to `apps/ui/src/styles/global.css`. Six CSS class groups updated. No layout, sizing, padding, or content changes. No JSX touched.

**Tech Stack:** CSS, Vite build (`npm run build`), systemd (`sudo systemctl restart jarvis-api`)

---

## File map

| File | Change |
|------|--------|
| `apps/ui/src/styles/global.css` | Modify 6 class groups: colors, backgrounds, borders, shadows only |

---

## Task 1: Support cards and MC stat cards

**Files:**
- Modify: `apps/ui/src/styles/global.css:75` (`.support-card, .mc-stat`) and `apps/ui/src/styles/global.css:492` (`.support-card` override in rail section)

Note: `.support-card` appears twice — line 75–79 (general) and line 492 (rail section override). Both must be updated.

- [ ] **Step 1: Update `.support-card, .mc-stat` (line ~75)**

Find:
```css
.support-card, .mc-stat {
  background: #1c1f25;
  border:1px solid rgba(255,255,255,.04);
  border-radius:10px; padding:10px 12px;
}
```

Replace with:
```css
.support-card, .mc-stat {
  background: linear-gradient(160deg, rgba(14,22,32,.96), rgba(10,16,24,.99));
  border:1px solid rgba(40,177,163,.10);
  border-radius:10px; padding:10px 12px;
  box-shadow: 0 1px 6px rgba(0,0,0,.18);
}
```

- [ ] **Step 2: Update `.support-card` rail override (line ~492)**

Find:
```css
.support-card { padding:10px 12px; background: #1c1f25; border: 1px solid rgba(255,255,255,.04); border-radius: 10px; box-shadow: none; }
```

Replace with:
```css
.support-card { padding:10px 12px; background: linear-gradient(160deg, rgba(14,22,32,.96), rgba(10,16,24,.99)); border: 1px solid rgba(40,177,163,.10); border-radius: 10px; box-shadow: 0 1px 6px rgba(0,0,0,.18); }
```

- [ ] **Step 3: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/styles/global.css
git commit -m "style: teal-tinted support cards and mc-stat"
```

---

## Task 2: MC list rows

**Files:**
- Modify: `apps/ui/src/styles/global.css:732` (`.mc-list-row`), `~737` (`.mc-list-row.active`), `~739` (`.mc-list-row-subtle`)

- [ ] **Step 1: Update `.mc-list-row` base (line ~732)**

Find:
```css
.mc-list-row {
  width:100%; text-align:left; display:flex; align-items:center; justify-content:space-between; gap:10px;
  padding:6px 10px; border-radius:8px; border:1px solid rgba(255,255,255,.04); background:#1c1f25; color:#e4e6ed;
  transition: border-color .14s ease, background .14s ease;
}
```

Replace with:
```css
.mc-list-row {
  width:100%; text-align:left; display:flex; align-items:center; justify-content:space-between; gap:10px;
  padding:6px 10px; border-radius:8px; border:1px solid rgba(40,177,163,.08); background:rgba(14,20,30,.8); color:#e4e6ed;
  transition: border-color .14s ease, background .14s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,.12);
}
```

- [ ] **Step 2: Update `.mc-list-row.active` (line ~737)**

Find:
```css
.mc-list-row.active { border-color: rgba(40,177,163,.25); background:#16222f; }
```

Replace with:
```css
.mc-list-row.active { border-color: rgba(40,177,163,.22); background:rgba(16,28,40,.85); }
```

- [ ] **Step 3: Update `.mc-list-row-subtle` (line ~739)**

Find:
```css
.mc-list-row-subtle { margin-left:10px; background:#101721; border-color:rgba(255,255,255,.035); }
```

Replace with:
```css
.mc-list-row-subtle { margin-left:10px; background:rgba(10,16,24,.85); border-color:rgba(40,177,163,.05); }
```

- [ ] **Step 4: Commit**

```bash
git add apps/ui/src/styles/global.css
git commit -m "style: teal-tinted mc list rows"
```

---

## Task 3: MC tabs

**Files:**
- Modify: `apps/ui/src/styles/global.css:666` (`.mc-tab`), `~669` (`.mc-tab.active`)

- [ ] **Step 1: Update `.mc-tab` base (line ~666)**

Find:
```css
.mc-tab {
  border:none; background:transparent; color:#8b909e; border-radius:8px; padding:8px 14px; white-space:nowrap; font-size:12px;
}
```

Replace with:
```css
.mc-tab {
  border:1px solid transparent; background:transparent; color:#8b909e; border-radius:8px; padding:8px 14px; white-space:nowrap; font-size:12px;
  transition: border-color .14s ease, background .14s ease, color .14s ease;
}
```

- [ ] **Step 2: Update `.mc-tab.active` (line ~669)**

Find:
```css
.mc-tab.active { background:rgba(40,177,163,.12); color:#e4e6ed; }
```

Replace with:
```css
.mc-tab.active { background:rgba(14,22,32,.9); border-color:rgba(40,177,163,.18); color:#e4e6ed; box-shadow: 0 0 8px rgba(40,177,163,.06); }
```

- [ ] **Step 3: Commit**

```bash
git add apps/ui/src/styles/global.css
git commit -m "style: teal-tinted mc tabs active state"
```

---

## Task 4: Sidebar session items

**Files:**
- Modify: `apps/ui/src/styles/global.css:110` (`.session-item.active`), `~111` (`.session-item.active:hover`)

Active state only — hover and base state unchanged (no layout impact).

- [ ] **Step 1: Update `.session-item.active` (line ~110)**

Find:
```css
.session-item.active { border-color: rgba(40,177,163,.22); background:#16202c; }
.session-item.active:hover { background:#172330; }
```

Replace with:
```css
.session-item.active { border-color: rgba(40,177,163,.22); background:rgba(14,22,34,.85); box-shadow: 0 0 0 1px rgba(40,177,163,.06); }
.session-item.active:hover { background:rgba(16,26,40,.9); }
```

- [ ] **Step 2: Commit**

```bash
git add apps/ui/src/styles/global.css
git commit -m "style: teal-tinted session item active state"
```

---

## Task 5: Icon buttons

**Files:**
- Modify: `apps/ui/src/styles/global.css:92` (`.icon-btn`), `~96` (`.icon-btn:hover`), `~100` (`.icon-btn.subtle`)

- [ ] **Step 1: Update `.icon-btn` base (line ~92)**

Find:
```css
.icon-btn {
  width:30px; height:30px; border-radius:10px; border:1px solid rgba(255,255,255,.08); background:#1a2431; color:#8b909e;
  display:grid; place-items:center; transition: background .14s ease, border-color .14s ease, color .14s ease, transform .14s ease;
}
```

Replace with:
```css
.icon-btn {
  width:30px; height:30px; border-radius:10px; border:1px solid rgba(40,177,163,.15); background:rgba(40,177,163,.05); color:#5ab8a0;
  display:grid; place-items:center; transition: background .14s ease, border-color .14s ease, color .14s ease, transform .14s ease;
}
```

- [ ] **Step 2: Update `.icon-btn:hover` (line ~96)**

Find:
```css
.icon-btn:hover { background:#202c3a; color:#e4e6ed; border-color:rgba(255,255,255,.14); }
```

Replace with:
```css
.icon-btn:hover { background:rgba(40,177,163,.10); color:#7dd8c4; border-color:rgba(40,177,163,.28); }
```

- [ ] **Step 3: Commit**

```bash
git add apps/ui/src/styles/global.css
git commit -m "style: teal-tinted icon buttons"
```

---

## Task 6: Chat header border

**Files:**
- Modify: `apps/ui/src/styles/global.css:127` (`.chat-header-bar` — border-bottom only)

- [ ] **Step 1: Update border-bottom on `.chat-header-bar` (line ~135)**

Find:
```css
  border-bottom:1px solid rgba(255,255,255,.06);
```
(inside `.chat-header-bar` block)

Replace with:
```css
  border-bottom:1px solid rgba(40,177,163,.10);
```

- [ ] **Step 2: Commit**

```bash
git add apps/ui/src/styles/global.css
git commit -m "style: teal-tinted chat header separator"
```

---

## Task 7: Build and deploy

- [ ] **Step 1: Build the UI**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build
```

Expected output ends with: `✓ built in X.XXs`

- [ ] **Step 2: Restart the service**

```bash
sudo systemctl restart jarvis-api && sleep 2 && sudo systemctl status jarvis-api --no-pager | grep "Active:"
```

Expected: `Active: active (running)`

- [ ] **Step 3: Visually verify at http://localhost/**

Check each area:
- Mission Control → support cards have teal-tinted border and gradient bg
- MC list rows → subtle teal border, darker bg
- MC tabs → active tab has dark bg + teal border outline
- Sidebar → active session has teal border glow
- Icon buttons (+ new chat, refresh) → teal tint
- Chat header → teal separator line
- Composer card, chat width, transcript padding → **unchanged**

- [ ] **Step 4: Final commit if any tweaks needed**

```bash
git add apps/ui/src/styles/global.css
git commit -m "style: final tweaks after visual review"
```
