# UI Theme Lift — Teal-tinted Depth

**Date:** 2026-04-09  
**Scope:** Pure CSS changes in `apps/ui/src/styles/global.css`  
**Constraint:** No structural changes, no removal of links or informational content in panels.

---

## Goal

Lift the visual language of the rest of the UI to match the new composer card, using the "Teal-tinted depth" direction: dark gradients with subtle teal accent borders and soft shadows across all surface types.

The composer card already sets the standard — everything else should feel like it belongs to the same design system.

---

## Areas in scope

### 1. Support cards (`.support-card`)
**Now:** Flat `#1c1f25` background, near-invisible border `rgba(255,255,255,.04)`.  
**New:** Dark blue-teal gradient + teal-tinted border + soft shadow.
```css
background: linear-gradient(160deg, rgba(14,22,32,.96), rgba(10,16,24,.99));
border: 1px solid rgba(40,177,163,.10);
box-shadow: 0 1px 6px rgba(0,0,0,.18);
```

### 2. MC list rows (`.mc-list-row`)
**Now:** Flat `#1c1f25` background, barely-visible border.  
**New:** Deep dark background + teal-tinted border + micro shadow.
```css
background: rgba(14,20,30,.8);
border: 1px solid rgba(40,177,163,.08);
box-shadow: 0 1px 3px rgba(0,0,0,.12);
```
Active state gets stronger teal: `border-color: rgba(40,177,163,.22)`.

### 3. MC tabs (`.mc-tab`)
**Now:** Plain transparent buttons, active = teal background fill only.  
**New:** Active tab gets card-like treatment: dark background + teal border + subtle top glow.
```css
.mc-tab.active {
  background: rgba(14,22,32,.9);
  border: 1px solid rgba(40,177,163,.18);
  box-shadow: 0 -1px 8px rgba(40,177,163,.06);
}
```

### 4. Sidebar session items (`.session-item`)
**Now:** Transparent with plain `#131c27` hover.  
**New:** Active item gets teal-tinted border + deep background.
```css
.session-item.active {
  background: rgba(14,22,34,.8);
  border-color: rgba(40,177,163,.18);
  box-shadow: 0 0 0 1px rgba(40,177,163,.06);
}
```

### 5. Icon buttons (`.icon-btn`)
**Now:** Solid `#1a2431` background — opaque blue-dark.  
**New:** Glass-teal: semi-transparent with teal-tinted border.
```css
background: rgba(40,177,163,.05);
border: 1px solid rgba(40,177,163,.15);
color: #5ab8a0;
```

### 6. Chat header border (`.chat-header-bar`)
**Now:** Plain `rgba(255,255,255,.06)` border-bottom.  
**New:** Teal-tinted separator to match MC header.
```css
border-bottom: 1px solid rgba(40,177,163,.10);
```

---

## What does NOT change

- All text content, links, data displays inside panels — untouched
- Layout, grid structure, spacing — untouched
- Composer (already correct)
- Color tokens (`tokens.js`) — no changes needed, all values inline in CSS overrides
- Component JSX files — no changes, only `global.css`

---

## Files changed

- `apps/ui/src/styles/global.css` — targeted overrides to the 6 CSS classes above
- Rebuild: `cd apps/ui && npm run build` + `sudo systemctl restart jarvis-api`
