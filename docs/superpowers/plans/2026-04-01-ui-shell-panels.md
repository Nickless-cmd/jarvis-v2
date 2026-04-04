# UI Shell Panels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the sidebar, header (TopBar), and right panel (ChatSupportRail) to match the mock designs — adding nav items, system health stats, autonomy badges, token meter, emotional state, skills list, memory summary, and inner voice display.

**Architecture:** All three areas already exist as React components. We modify them in place, adding new sections and wiring them to existing backend data. The affective meta state (mock's "emotional state") is already available via `/mc/jarvis`. System health requires a new lightweight backend endpoint. Skills and memory summaries use data already in the jarvis API response. No new npm dependencies needed.

**Tech Stack:** React 18, vanilla CSS (global.css), Lucide icons, FastAPI backend

**Reference files:**
- Mock ChatView: `ui-v2-old/ui-v2/ChatView.jsx` (Sidebar lines 181-317, TopBar lines 319-367, RightPanel lines 645-747)

---

## File Structure

### New files
- `apps/api/jarvis_api/routes/system_health.py` — New lightweight endpoint returning CPU/RAM/Disk stats

### Modified files
- `apps/ui/src/components/layout/AppShell.jsx` — Add nav items (Memory, Skills), new chat button, system stats at bottom
- `apps/ui/src/components/layout/SidebarSessions.jsx` — Relative timestamps on sessions
- `apps/ui/src/components/chat/ChatHeader.jsx` — Autonomy badges, EXP chip, provider chip, token meter
- `apps/ui/src/components/chat/ChatSupportRail.jsx` — Replace runtime stats with emotional state grid, skills list, memory summary, inner voice
- `apps/ui/src/app/ChatPage.jsx` — Pass additional data props to ChatSupportRail
- `apps/ui/src/app/useUnifiedShell.js` — Fetch system health, expose jarvis data for right panel
- `apps/ui/src/lib/adapters.js` — Add system health adapter
- `apps/ui/src/styles/global.css` — New styles for all updated components
- `apps/api/jarvis_api/app.py` — Register system health route

---

## Task 1: Add System Health Backend Endpoint

**Files:**
- Create: `apps/api/jarvis_api/routes/system_health.py`
- Modify: `apps/api/jarvis_api/app.py`

- [ ] **Step 1: Create system health route**

```python
# apps/api/jarvis_api/routes/system_health.py
import shutil
import psutil
from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/system/health")
def system_health() -> dict:
    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    return {
        "cpu_pct": round(cpu_pct, 1),
        "ram_pct": round(mem.percent, 1),
        "disk_free_mb": round(disk.free / (1024 * 1024), 0),
    }
```

- [ ] **Step 2: Register route in app.py**

Read `apps/api/jarvis_api/app.py` and find where other routers are included. Add:

```python
from apps.api.jarvis_api.routes.system_health import router as system_health_router
app.include_router(system_health_router, prefix="/mc")
```

- [ ] **Step 3: Add frontend adapter**

In `apps/ui/src/lib/adapters.js`, add to the `backend` object:

```js
async getSystemHealth() {
  try {
    return await requestJson('/mc/system/health')
  } catch {
    return { cpu_pct: 0, ram_pct: 0, disk_free_mb: 0 }
  }
},
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/routes/system_health.py apps/api/jarvis_api/app.py apps/ui/src/lib/adapters.js
git commit -m "feat: add /mc/system/health endpoint for CPU, RAM, disk stats"
```

---

## Task 2: Upgrade Sidebar — Nav Items, New Chat Button, System Stats

**Files:**
- Modify: `apps/ui/src/components/layout/AppShell.jsx`
- Modify: `apps/ui/src/app/useUnifiedShell.js`
- Modify: `apps/ui/src/app/App.jsx`
- Modify: `apps/ui/src/styles/global.css`

- [ ] **Step 1: Add system health polling to useUnifiedShell**

In `useUnifiedShell.js`, add state and polling:

```js
const [systemHealth, setSystemHealth] = useState({ cpu_pct: 0, ram_pct: 0, disk_free_mb: 0 })

// In the boot/refresh useEffect, add:
async function pollHealth() {
  const health = await backend.getSystemHealth()
  setSystemHealth(health)
}
pollHealth()
const healthInterval = setInterval(pollHealth, 10000)
// In cleanup: clearInterval(healthInterval)
```

Return `systemHealth` from the hook.

- [ ] **Step 2: Update AppShell.jsx with 4 nav items, new chat button, and system stats**

Read `AppShell.jsx` first. Replace its contents with:

```jsx
import { Bot, LayoutDashboard, MessageSquare, Brain, Layers, Plus } from 'lucide-react'

export function AppShell({ activeView, onChangeView, sidebarContent, systemHealth, onNewChat, children }) {
  return (
    <div className="app-shell">
      <aside className="global-sidebar">
        <div className="brand-block">
          <div className="brand-icon"><Bot size={14} /></div>
          <span className="brand-name-text">JARVIS</span>
          <div className="brand-status-dot" />
        </div>

        <button className="sidebar-new-chat-btn" onClick={onNewChat}>
          <Plus size={12} />
          Ny chat
        </button>

        <nav className="global-nav">
          {[
            { id: 'chat', icon: MessageSquare, label: 'Chat' },
            { id: 'memory', icon: Brain, label: 'Memory' },
            { id: 'skills', icon: Layers, label: 'Skills' },
            { id: 'mission-control', icon: LayoutDashboard, label: 'Mission Control' },
          ].map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              className={activeView === id ? 'nav-item active' : 'nav-item'}
              onClick={() => onChangeView(id)}
              title={label}
            >
              <Icon size={13} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        {sidebarContent ? <div className="sidebar-section">{sidebarContent}</div> : null}

        <div className="sidebar-system-stats">
          {[
            { label: 'CPU', value: systemHealth.cpu_pct, unit: '%' },
            { label: 'RAM', value: systemHealth.ram_pct, unit: '%' },
          ].map(({ label, value, unit }) => (
            <div key={label} className="sidebar-stat-row">
              <div className="sidebar-stat-labels">
                <span className="sidebar-stat-name mono">{label}</span>
                <span className="sidebar-stat-value mono">{value}{unit}</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{ width: `${value}%`, background: value > 80 ? '#c05050' : '#3d8f7c' }} />
              </div>
            </div>
          ))}
          <div className="sidebar-stat-labels">
            <span className="sidebar-stat-name mono">DISK</span>
            <span className="sidebar-stat-value mono">{systemHealth.disk_free_mb} MB free</span>
          </div>
        </div>
      </aside>

      <div className="app-content">{children}</div>
    </div>
  )
}
```

- [ ] **Step 3: Pass systemHealth and onNewChat to AppShell in App.jsx**

Read `App.jsx`. Find where `<AppShell>` is rendered. Add the new props:

```jsx
<AppShell
  activeView={activeView}
  onChangeView={setActiveView}
  sidebarContent={sidebarContent}
  systemHealth={systemHealth}
  onNewChat={handleCreateSession}
>
```

Make sure `systemHealth` and `handleCreateSession` are available from the `useUnifiedShell` hook.

For Memory and Skills nav-clicks: `onChangeView` should route `'memory'` and `'skills'` to Mission Control with the appropriate active tab. Add logic in App.jsx:

```js
function handleViewChange(view) {
  if (view === 'memory' || view === 'skills') {
    setActiveView('mission-control')
    // The MC page will need to know to activate the right tab
    // For now, just navigate to MC — the tabs are already there
    return
  }
  setActiveView(view)
}
```

- [ ] **Step 4: Add CSS for new sidebar elements**

```css
/* ─── Sidebar: New Chat Button ─── */
.sidebar-new-chat-btn {
  display: flex; align-items: center; gap: 6px;
  width: calc(100% - 24px); margin: 0 12px 8px; padding: 7px 10px;
  background: rgba(61,143,124,0.10); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px; cursor: pointer;
  color: #5ab8a0; font-size: 11px; font-family: 'DM Sans', sans-serif; font-weight: 500;
  transition: background 0.15s;
}
.sidebar-new-chat-btn:hover { background: rgba(61,143,124,0.18); }

/* ─── Sidebar: System Stats ─── */
.sidebar-system-stats {
  padding: 12px 16px; margin-top: auto;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.sidebar-stat-row { margin-bottom: 8px; }
.sidebar-stat-labels {
  display: flex; justify-content: space-between; margin-bottom: 3px;
}
.sidebar-stat-name { font-size: 9px; color: #4e5262; letter-spacing: 0.1em; }
.sidebar-stat-value { font-size: 9px; color: #8b909e; }

/* ─── Sidebar: Brand name update ─── */
.brand-name-text {
  font-size: 13px; font-weight: 600; letter-spacing: 0.06em; color: #e4e6ed;
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/components/layout/AppShell.jsx apps/ui/src/app/useUnifiedShell.js apps/ui/src/app/App.jsx apps/ui/src/styles/global.css
git commit -m "feat(ui): upgrade sidebar — 4 nav items, new chat button, system health stats"
```

---

## Task 3: Upgrade ChatHeader — Autonomy Badges, Provider Chip, Token Meter

**Files:**
- Modify: `apps/ui/src/components/chat/ChatHeader.jsx`
- Modify: `apps/ui/src/app/ChatPage.jsx`
- Modify: `apps/ui/src/styles/global.css`

- [ ] **Step 1: Update ChatHeader to match mock TopBar**

Read `ChatHeader.jsx`. Replace its content with a design that uses Chip badges for autonomy/exp/provider, and a token meter:

```jsx
import { Activity, Search, Settings, RefreshCw } from 'lucide-react'
import { Chip } from '../shared/Chip'

export function ChatHeader({
  session,
  selection,
  onRefresh,
  isRefreshing,
  isStreaming,
}) {
  const provider = selection.currentProvider || 'unknown'

  return (
    <section className="chat-header-bar">
      <div className="chat-header-left">
        <span className="chat-header-session-title">{session?.title || 'Ny chat'}</span>
        <div className="chat-header-chips">
          <Chip color="#3d8f7c">L3</Chip>
          <Chip color="#d4963a">EXP</Chip>
          <Chip color="#4e5262">{provider}</Chip>
        </div>
      </div>

      <div className="chat-header-right">
        <div className={`chat-token-meter ${isStreaming ? 'active' : ''}`}>
          <Activity size={9} />
          <span className="mono">— tok/min</span>
        </div>

        <button className="icon-btn" onClick={onRefresh} title="Refresh">
          <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
        </button>
        <button className="icon-btn" title="Search"><Search size={14} /></button>
        <button className="icon-btn" title="Settings"><Settings size={14} /></button>
      </div>
    </section>
  )
}
```

Note: The autonomy level (L3) and EXP mode are currently hardcoded. They can be wired to real data later when the workspace status endpoint exists. The token meter shows "— tok/min" as placeholder until token rate polling is implemented.

- [ ] **Step 2: Remove the onSelectionChange prop from ChatHeader usage in ChatPage.jsx**

The old ChatHeader had provider/model dropdowns with `onSelectionChange`. The new design uses chips instead. Update `ChatPage.jsx` to pass `isStreaming` instead of `onSelectionChange`:

```jsx
<ChatHeader
  session={{ title: hero.title }}
  selection={selection}
  onRefresh={onRefresh}
  isRefreshing={isRefreshing}
  isStreaming={isStreaming}
/>
```

- [ ] **Step 3: Add CSS for new ChatHeader**

```css
/* ─── Chat Header: Chips & Token Meter ─── */
.chat-header-left {
  display: flex; align-items: center; gap: 10px;
}
.chat-header-session-title {
  font-size: 12px; font-weight: 500; color: #e4e6ed;
}
.chat-header-chips { display: flex; gap: 4px; }
.chat-header-right { display: flex; align-items: center; gap: 8px; }

.chat-token-meter {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px;
  background: #1c1f25; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px; transition: all 0.3s;
}
.chat-token-meter .mono { font-size: 9px; color: #4e5262; }
.chat-token-meter svg { color: #4e5262; }
.chat-token-meter.active {
  background: rgba(61,143,124,0.10); border-color: #3d8f7c;
}
.chat-token-meter.active .mono { color: #5ab8a0; }
.chat-token-meter.active svg { color: #5ab8a0; }
```

- [ ] **Step 4: Remove old header styles that are no longer needed**

Read global.css and remove/update styles for the old `.header-select-group`, `.header-select`, `.header-model-select`, `.header-status-pill` if they exist and are no longer referenced.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/components/chat/ChatHeader.jsx apps/ui/src/app/ChatPage.jsx apps/ui/src/styles/global.css
git commit -m "feat(ui): upgrade ChatHeader — autonomy badges, provider chip, token meter"
```

---

## Task 4: Upgrade ChatSupportRail — Emotional State, Skills, Memory, Inner Voice

**Files:**
- Modify: `apps/ui/src/components/chat/ChatSupportRail.jsx`
- Modify: `apps/ui/src/app/ChatPage.jsx`
- Modify: `apps/ui/src/app/useUnifiedShell.js`
- Modify: `apps/ui/src/styles/global.css`

- [ ] **Step 1: Add jarvis data fetching to useUnifiedShell**

The right panel needs data from the `/mc/jarvis` response (affective meta state, skills from the jarvis summary, memory summary). This data is already fetched by Mission Control. Add a lightweight fetch for the chat view:

In `useUnifiedShell.js`, add:

```js
const [jarvisSurface, setJarvisSurface] = useState(null)

// In the boot useEffect, after refreshShell:
async function fetchJarvisSurface() {
  try {
    const data = await backend.getJarvisSurface()
    setJarvisSurface(data)
  } catch { /* silent */ }
}
fetchJarvisSurface()
const jarvisInterval = setInterval(fetchJarvisSurface, 30000)
// In cleanup: clearInterval(jarvisInterval)
```

Return `jarvisSurface` from the hook.

In `adapters.js`, add to `backend`:

```js
async getJarvisSurface() {
  const data = await requestJson('/mc/jarvis')
  return data
},
```

Note: Check if `getJarvisSurface` or similar already exists in adapters.js. The MC hook may already call `/mc/jarvis`. If so, reuse the existing method name.

- [ ] **Step 2: Rewrite ChatSupportRail**

```jsx
import { Smile, Frown, Lightbulb, Battery, Brain } from 'lucide-react'

function PanelSection({ title, children }) {
  return (
    <div className="rail-panel-section">
      <div className="rail-panel-title mono">{title}</div>
      {children}
    </div>
  )
}

export function ChatSupportRail({ session, selection, isStreaming, jarvisSurface }) {
  const affective = jarvisSurface?.affectiveMetaState || jarvisSurface?.runtime_affective_meta_state || {}
  const summary = jarvisSurface?.summary || {}
  const memorySummary = summary?.retained_memory || {}

  const emotions = [
    { label: 'CONF', value: affective.confidenceLevel || affective.confidence || 0, color: '#4caf82', icon: Smile },
    { label: 'CURIO', value: affective.curiosityLevel || affective.curiosity || 0, color: '#d4963a', icon: Lightbulb },
    { label: 'FRUS', value: affective.frustrationLevel || affective.frustration || 0, color: '#c05050', icon: Frown },
    { label: 'FATIGUE', value: affective.fatigueLevel || affective.fatigue || 0, color: '#4a80c0', icon: Battery },
  ]

  const innerVoice = jarvisSurface?.protectedVoice?.preview
    || jarvisSurface?.protected_voice?.preview
    || 'ingen tanker endnu...'

  return (
    <aside className="chat-support-rail">
      {/* Emotional State */}
      <PanelSection title="Emotional State">
        <div className="emotion-grid">
          {emotions.map(({ label, value, color, icon: Icon }) => {
            const pct = typeof value === 'number' && value <= 1 ? value * 100 : Number(value) || 0
            return (
              <div key={label} className="emotion-card">
                <div className="emotion-card-header">
                  <Icon size={9} color={color} />
                  <span className="mono">{label}</span>
                </div>
                <div className="emotion-card-value mono">{pct.toFixed(0)}%</div>
                <div className="progress-bar">
                  <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color }} />
                </div>
              </div>
            )
          })}
        </div>
      </PanelSection>

      {/* Skills */}
      <PanelSection title="Skills">
        <div className="rail-skill-list">
          {(jarvisSurface?.skills || []).slice(0, 6).map(sk => (
            <div key={sk.name || sk} className="rail-skill-item">
              <div className={`rail-skill-dot ${sk.status === 'active' || sk.status === 'registered' ? 'active' : ''}`} />
              <span className="mono">{sk.name || sk}</span>
              <span className="rail-skill-uses mono">{sk.uses || 0}</span>
            </div>
          ))}
          {!(jarvisSurface?.skills || []).length && (
            <span className="rail-empty mono">no skills loaded</span>
          )}
        </div>
      </PanelSection>

      {/* Memory */}
      <PanelSection title="Memory">
        {[
          { label: 'Kind', value: memorySummary.kind || 'unknown', color: '#5ab8a0' },
          { label: 'Focus', value: memorySummary.focus || 'none', color: '#8b909e' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rail-memory-row">
            <span>{label}</span>
            <span className="mono" style={{ color }}>{value}</span>
          </div>
        ))}
      </PanelSection>

      {/* Inner Voice */}
      <PanelSection title="Inner Voice">
        <div className="rail-inner-voice">
          <span>{innerVoice}</span>
        </div>
      </PanelSection>
    </aside>
  )
}
```

- [ ] **Step 3: Pass jarvisSurface to ChatSupportRail via ChatPage**

In `ChatPage.jsx`, add `jarvisSurface` prop:

```jsx
export function ChatPage({
  activeSession, selection, error,
  onSelectionChange, onRefresh, onSend,
  isRefreshing, isStreaming, workingSteps,
  jarvisSurface,
}) {
```

And pass it to ChatSupportRail:

```jsx
<ChatSupportRail
  session={activeSession}
  selection={selection}
  isStreaming={isStreaming}
  jarvisSurface={jarvisSurface}
/>
```

Then in `App.jsx`, pass `jarvisSurface` from the shell hook to `ChatPage`.

- [ ] **Step 4: Add CSS for right panel sections**

```css
/* ─── Chat Support Rail: Panel Sections ─── */
.rail-panel-section {
  padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.04);
}
.rail-panel-title {
  font-size: 9px; color: #4e5262; letter-spacing: 0.12em;
  text-transform: uppercase; margin-bottom: 10px;
}

/* Emotion grid (2x2) */
.emotion-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.emotion-card {
  padding: 8px; background: #1c1f25;
  border: 1px solid rgba(255,255,255,0.04); border-radius: 8px;
}
.emotion-card-header {
  display: flex; align-items: center; gap: 4px; margin-bottom: 4px;
}
.emotion-card-header .mono { font-size: 8px; color: #4e5262; letter-spacing: 0.08em; }
.emotion-card-value { font-size: 14px; color: #e4e6ed; margin-bottom: 4px; }
.emotion-card .progress-bar { height: 2px; }

/* Skills list */
.rail-skill-list { display: flex; flex-direction: column; gap: 1px; }
.rail-skill-item {
  display: flex; align-items: center; padding: 5px 6px;
  border-radius: 5px; transition: background 0.15s; cursor: pointer;
}
.rail-skill-item:hover { background: #272b35; }
.rail-skill-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #2d303d; margin-right: 7px; flex-shrink: 0;
}
.rail-skill-dot.active { background: #4caf82; box-shadow: 0 0 5px #4caf82; }
.rail-skill-item .mono { font-size: 10px; color: #8b909e; flex: 1; }
.rail-skill-uses { font-size: 9px; color: #4e5262; }
.rail-empty { font-size: 10px; color: #4e5262; font-style: italic; }

/* Memory rows */
.rail-memory-row {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 7px; font-size: 11px; color: #8b909e;
}
.rail-memory-row .mono { font-size: 10px; }

/* Inner voice */
.rail-inner-voice {
  padding: 8px 10px; background: #1c1f25;
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 7px; border-left: 2px solid #2d303d;
}
.rail-inner-voice span {
  font-size: 11px; color: #4e5262; font-style: italic; line-height: 1.5;
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/components/chat/ChatSupportRail.jsx apps/ui/src/app/ChatPage.jsx apps/ui/src/app/useUnifiedShell.js apps/ui/src/app/App.jsx apps/ui/src/lib/adapters.js apps/ui/src/styles/global.css
git commit -m "feat(ui): upgrade right panel — emotional state, skills, memory, inner voice"
```

---

## Task 5: Update Sidebar Sessions with Relative Timestamps

**Files:**
- Modify: `apps/ui/src/components/layout/SidebarSessions.jsx`

- [ ] **Step 1: Add relative time formatting and update session items**

Read `SidebarSessions.jsx`. Update the session item meta to show relative time:

```jsx
import { Plus } from 'lucide-react'

function relativeTime(dateStr) {
  if (!dateStr) return ''
  const delta = Date.now() - new Date(dateStr).getTime()
  const sec = Math.floor(delta / 1000)
  if (sec < 60) return 'lige nu'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m siden`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}t siden`
  return `${Math.floor(hr / 24)}d siden`
}

export function SidebarSessions({ sessions, activeSessionId, onSelect, onCreate }) {
  return (
    <section className="sidebar-sessions">
      <div className="sidebar-sessions-head">
        <span className="sidebar-mini-label mono">Seneste</span>
      </div>

      <div className="session-list">
        {sessions.map((session) => (
          <button
            className={session.id === activeSessionId ? 'session-item active' : 'session-item'}
            key={session.id}
            onClick={() => onSelect(session.id)}
            title={session.title}
          >
            <div className="session-item-title">{session.title}</div>
            <div className="session-item-time mono">{relativeTime(session.updated_at)}</div>
          </button>
        ))}

        {!sessions.length ? (
          <div className="sidebar-empty-state">
            <span>Ingen chats endnu</span>
          </div>
        ) : null}
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Add/update CSS for session items**

```css
.session-item-title {
  font-size: 11px; color: #e4e6ed; margin-bottom: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.session-item-time { font-size: 9px; color: #4e5262; }
```

- [ ] **Step 3: Commit**

```bash
git add apps/ui/src/components/layout/SidebarSessions.jsx apps/ui/src/styles/global.css
git commit -m "feat(ui): sidebar sessions with relative timestamps and simplified layout"
```

---

## Summary

| Task | Description | Scope |
|------|-------------|-------|
| 1 | System health backend endpoint + adapter | Backend + adapter |
| 2 | Upgrade sidebar — 4 nav items, new chat btn, system stats | AppShell + useUnifiedShell + CSS |
| 3 | Upgrade ChatHeader — autonomy badges, token meter | ChatHeader + ChatPage + CSS |
| 4 | Upgrade ChatSupportRail — emotional state, skills, memory, inner voice | Right panel + data wiring + CSS |
| 5 | Sidebar sessions with relative timestamps | SidebarSessions + CSS |
