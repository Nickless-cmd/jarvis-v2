# Mission Control Tab Merges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce Mission Control navbar from 21 tabs to 14 by merging closely related tabs.

**Architecture:** Pure frontend refactor. Six merges using either (a) combined SurfaceGrid for same-data-source tabs, (b) a new `SubTabs` pill-nav for cross-type merges, or (c) absorbing a tab's JSX directly into a host tab. No backend changes. Each merge is one commit.

**Tech Stack:** React, inline styles via `s/T/mono` tokens, lucide-react icons.

---

## Merges at a glance

| Removed | Absorbed into | New tab ID |
|---------|--------------|-----------|
| Autonomy | Threads | `threads` |
| Governance | Hardening | `hardening` (sub-tabs) |
| SelfReview + Development + Continuity | new ReflectionTab | `reflection` |
| Cost | Lab | `lab` (sub-tabs) |
| Soul + CognitiveState | LivingMind → MindTab | `mind` |
| Agents | Operations → OpsTab | `operations` |

Result: 21 → 14 tabs (Overview, Operations, Observability, **Mind**, Proprioception, **Threads**, Memory, Council, Relationship, **Reflection**, Skills, **Hardening**, **Lab**, Skills stays, Memory stays).

---

## File map

**Modified:**
- `apps/ui/src/components/mission-control/shared.jsx` — add `SubTabs` component
- `apps/ui/src/components/mission-control/ThreadsTab.jsx` — absorb Autonomy sections
- `apps/ui/src/components/mission-control/HardeningTab.jsx` — add Governance sub-tab
- `apps/ui/src/components/mission-control/LabTab.jsx` — add Cost sub-tab (self-fetch `/mc/costs`)
- `apps/ui/src/app/MCTabBar.jsx` — remove 7 tab entries, rename labels
- `apps/ui/src/app/MissionControlPage.jsx` — update rendering, update ID references

**Created:**
- `apps/ui/src/components/mission-control/ReflectionTab.jsx` — wraps SelfReview+Development+Continuity with sub-tabs
- `apps/ui/src/components/mission-control/MindTab.jsx` — wraps LivingMind+Soul+Cognitive with sub-tabs
- `apps/ui/src/components/mission-control/OpsTab.jsx` — wraps Operations+Agents with sub-tabs

---

## Task 1: Add SubTabs to shared.jsx

**Files:**
- Modify: `apps/ui/src/components/mission-control/shared.jsx`

- [ ] **Step 1: Add SubTabs export to shared.jsx**

Open `apps/ui/src/components/mission-control/shared.jsx`. Add after the `Chip` export (after line 20 or wherever Chip ends):

```jsx
import { useState } from 'react'  // ADD to existing imports at top if not present

// ... existing exports ...

export function SubTabs({ tabs, active, onChange }) {
  return (
    <div style={s({ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' })}>
      {tabs.map(({ id, label }) => {
        const isActive = active === id
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            style={s({
              padding: '4px 14px',
              borderRadius: 20,
              border: `1px solid ${isActive ? T.accent : T.border1}`,
              background: isActive ? `${T.accent}22` : 'transparent',
              color: isActive ? T.accentText : T.text3,
              cursor: 'pointer',
              fontSize: 11,
              fontFamily: T.sans,
              fontWeight: isActive ? 500 : 400,
              transition: 'all 0.15s',
            })}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
```

Note: `shared.jsx` already imports `s, T, mono` from tokens. Check if `useState` is already imported there — add it to the import if not. No other changes needed.

- [ ] **Step 2: Verify build**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -5
```

Expected: no errors (warnings OK).

- [ ] **Step 3: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/components/mission-control/shared.jsx
git commit -m "feat(mc): add SubTabs pill-nav component to shared"
```

---

## Task 2: Merge Autonomy into Threads

Both tabs use `useCognitiveSurfaces()` + `SurfaceGrid`. Simply add Autonomy's 8 sections to the end of ThreadsTab's SurfaceGrid.

**Files:**
- Modify: `apps/ui/src/components/mission-control/ThreadsTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx` (remove autonomy)
- Modify: `apps/ui/src/app/MissionControlPage.jsx` (remove autonomy render)

- [ ] **Step 1: Update ThreadsTab.jsx imports**

Current imports in ThreadsTab.jsx (line 1-2):
```jsx
import { Wind, GitBranch, Network, Globe, Users } from 'lucide-react'
```

Replace with (add Autonomy icons):
```jsx
import { Wind, GitBranch, Network, Globe, Users, Bell, Send, Hammer, Sparkles, Zap, FolderKanban, EyeOff, Moon } from 'lucide-react'
```

- [ ] **Step 2: Add Autonomy surface variables in ThreadsTab**

After line 24 (`const rd = surfaces.relation_dynamics || {}`), add:
```jsx
  // Autonomy surfaces
  const aa = surfaces.anticipatory_action || {}
  const ao = surfaces.autonomous_outreach || {}
  const aw = surfaces.autonomous_work || {}
  const ci = surfaces.creative_instinct || {}
  const cim = surfaces.creative_impulse || {}
  const cp = surfaces.creative_projects || {}
  const ad = surfaces.avoidance_detector || {}
  const dc = surfaces.dream_consolidation || {}
```

- [ ] **Step 3: Add Autonomy sections at end of SurfaceGrid in ThreadsTab**

Before the closing `</SurfaceGrid>` tag, append the following 8 sections (copy-paste from AutonomyTab.jsx):

```jsx
      {/* Anticipatory Action */}
      <Section icon={Bell} title="Forudseende handling" active={aa.active}>
        <Summary text={aa.summary} />
        <KV label="Peak-timer" value={aa.peak_hour_count} accent />
        <KV label="Observationer" value={aa.total_observations} />
        <KV label="Sidst opdateret" value={aa.last_updated?.slice(0, 16)} />
        {Array.isArray(aa.upcoming_peaks) && aa.upcoming_peaks.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {aa.upcoming_peaks.slice(0, 3).map((p, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                kl <strong>{String(p.hour).padStart(2, '0')}</strong> om {p.minutes_until}m · conf={p.confidence}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Autonomous Outreach */}
      <Section icon={Send} title="Proaktiv kontakt" active={ao.active}>
        <Summary text={ao.summary} />
        <KV label="Sendt" value={ao.sent_count} accent />
        <KV label="Skipped" value={ao.skipped_count} />
        <KV label="Cooldown (t)" value={ao.cooldown_hours} />
        <KV label="Quiet hours" value={ao.quiet_hours} />
      </Section>

      {/* Autonomous Work */}
      <Section icon={Hammer} title="Autonomt arbejde" active={aw.active}>
        <Summary text={aw.summary} />
        <KV label="Pending" value={aw.pending_count} accent />
        <KV label="Total forslag" value={aw.total_proposals} />
        <KV label="Max per time" value={aw.max_per_hour} />
        {aw.allowed_types?.length ? (
          <KV label="Typer" value={aw.allowed_types.join(', ')} />
        ) : null}
      </Section>

      {/* Creative Instinct */}
      <Section icon={Sparkles} title="Kreativ instinkt (kim)" active={ci.active}>
        <Summary text={ci.summary} />
        <KV label="Aktive kim" value={ci.active_seeds} accent />
        <KV label="Adopteret" value={ci.adopted_total} />
        <KV label="Visnet" value={ci.withered_total} />
        <KV label="Urgency" value={ci.creative_urgency} />
        {Array.isArray(ci.recent_active) && ci.recent_active.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {ci.recent_active.slice(0, 3).map((s_, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <strong>{s_.status}</strong> · {String(s_.spark || '').slice(0, 80)}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Creative Impulse */}
      <Section icon={Zap} title="Kreativ impuls (skabelser)" active={cim.active}>
        <Summary text={cim.summary} />
        <KV label="Total skabelser" value={cim.total_creations} accent />
        <KV label="Sidst" value={cim.last_creation_at?.slice(0, 16)} />
        <KV label="Næste forfalder" value={cim.next_due_at?.slice(0, 16)} />
        {cim.by_form && Object.keys(cim.by_form).length ? (
          <div style={s({ marginTop: 6 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Former</span>
            <div style={s({ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 })}>
              {Object.entries(cim.by_form).map(([k, v]) => (
                <span key={k} style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgOverlay, padding: '2px 6px', borderRadius: 4 })}>
                  {k}: {v}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </Section>

      {/* Creative Projects */}
      <Section icon={FolderKanban} title="Kreative projekter (uger+)" active={cp.active}>
        <Summary text={cp.summary} />
        <KV label="Aktive" value={cp.active_count} accent />
        <KV label="Pausede" value={cp.paused_count} />
        <KV label="Dreaming" value={cp.dreaming_count} />
        <KV label="Stale (3+ uger)" value={cp.stale_count} />
        <KV label="Total" value={cp.total} />
      </Section>

      {/* Avoidance Detector */}
      <Section icon={EyeOff} title="Undgåelses-detektor" active={ad.active}>
        <Summary text={ad.summary} />
        <KV label="Fund" value={ad.count} accent />
        {Array.isArray(ad.findings) && ad.findings.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {ad.findings.slice(0, 3).map((f, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgOverlay, padding: '4px 6px', borderRadius: 4 })}>
                <strong>{f.sample_title?.slice(0, 60)}</strong>
                <div style={s({ color: T.text3, marginTop: 2 })}>{f.days_silent}d stille · {f.items} signaler</div>
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Dream Consolidation */}
      <Section icon={Moon} title="Drømme-konsolidering" active={dc.active}>
        <Summary text={dc.summary} />
        <KV label="Konsolideringer" value={dc.total_consolidations} accent />
        <KV label="Sidst kørt" value={dc.last_run_at?.slice(0, 16)} />
        {Array.isArray(dc.recent) && dc.recent.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {dc.recent.slice(0, 3).map((r, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <span style={{ color: T.text3 }}>{String(r.at || '').slice(0, 16)}</span>{' '}
                {r.theme_count || 0} temaer · top: <strong>{r.top_theme || '—'}</strong>
              </div>
            ))}
          </div>
        ) : null}
      </Section>
```

- [ ] **Step 4: Remove Autonomy from MCTabBar.jsx**

In `apps/ui/src/components/mission-control/MCTabBar.jsx`, remove this line from `ALL_TABS`:
```js
  { id: 'autonomy', label: 'Autonomy', icon: Zap },
```
Also remove `Zap` from the lucide-react import if it's no longer used elsewhere in that file (check: it may only have been used for Autonomy).

- [ ] **Step 5: Remove Autonomy from MissionControlPage.jsx**

In `apps/ui/src/app/MissionControlPage.jsx`:

Remove this import (line 25):
```jsx
import { AutonomyTab } from '../components/mission-control/AutonomyTab'
```

Remove this render block (line 253):
```jsx
          {activeTab === 'autonomy' ? <AutonomyTab /> : null}
```

- [ ] **Step 6: Verify build**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/components/mission-control/ThreadsTab.jsx \
        apps/ui/src/components/mission-control/MCTabBar.jsx \
        apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(mc): merge Autonomy into Threads tab"
```

---

## Task 3: Merge Governance into Hardening (sub-tabs)

HardeningTab self-fetches `/mc/hardening`. GovernanceTab uses `useCognitiveSurfaces()`. A sub-tab switcher ("Sikkerhed" | "Governance") at the top of HardeningTab lets the user toggle between the two.

**Files:**
- Modify: `apps/ui/src/components/mission-control/HardeningTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Update HardeningTab.jsx**

Replace the full contents of `apps/ui/src/components/mission-control/HardeningTab.jsx` with:

```jsx
import { useState } from 'react'
import { useEffect } from 'react'
import { RefreshCcw, ShieldCheck, Shield, Lock, Repeat, Clock, FileCode, TrendingUp, Cpu, GitPullRequest } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel, EmptyState, Skeleton, SubTabs } from './shared'
import { backend } from '../../lib/adapters'
import { formatFreshness } from './meta'
import {
  useCognitiveSurfaces,
  SurfaceGrid,
  Section,
  KV,
  Summary,
  JsonBadges,
} from './surfaces'

function IntegrationRow({ label, ok }) {
  const color = ok ? T.green : T.text3
  return (
    <div style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0' })}>
      <div style={s({ width: 7, height: 7, borderRadius: '50%', background: color, boxShadow: ok ? `0 0 6px ${color}` : 'none', flexShrink: 0 })} />
      <span style={s({ fontSize: 11, color: ok ? T.text2 : T.text3 })}>{label}</span>
      <span style={s({ ...mono, fontSize: 9, color: T.text3, marginLeft: 'auto' })}>{ok ? 'konfigureret' : 'ikke sat op'}</span>
    </div>
  )
}

function StateChip({ state }) {
  const colorMap = { pending: T.amber, approved: T.green, denied: T.red, expired: T.text3 }
  const color = colorMap[state] || T.text3
  return (
    <span style={s({ ...mono, fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${color}18`, border: `1px solid ${color}35`, color })}>
      {state}
    </span>
  )
}

function SecurityPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetchedAt, setFetchedAt] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await backend.getMissionControlHardening()
        if (!cancelled) { setData(result); setFetchedAt(new Date().toISOString()) }
      } finally { if (!cancelled) setLoading(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  async function refresh() {
    setLoading(true)
    try {
      const result = await backend.getMissionControlHardening()
      setData(result); setFetchedAt(new Date().toISOString())
    } finally { setLoading(false) }
  }

  const pending = data?.pending ?? 0
  const integrations = data?.integrations || {}

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{fetchedAt ? formatFreshness(fetchedAt) : ''}</span>
        <button onClick={refresh} disabled={loading}
          style={s({ marginLeft: 'auto', padding: '4px 8px', borderRadius: 7, border: `1px solid ${T.border1}`, background: T.bgOverlay, color: T.text2, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 })}>
          <RefreshCcw size={11} />
        </button>
      </div>

      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="Afventer" value={loading ? '…' : pending} color={pending > 0 ? T.amber : undefined} alert={pending > 0} />
        <MetricCard label="Godkendt i dag" value={loading ? '…' : data?.approved_today ?? 0} color={T.green} />
        <MetricCard label="Afvist i dag" value={loading ? '…' : data?.denied_today ?? 0} color={data?.denied_today > 0 ? T.red : undefined} />
        <MetricCard label="Autonomi-niveau" value={loading ? '…' : (data?.autonomy_level || 'ukendt')} />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
        <Card>
          <SectionTitle>Integrationer</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={24} />)}
            </div>
          ) : (
            <>
              <IntegrationRow label="Telegram" ok={integrations.telegram} />
              <IntegrationRow label="Discord" ok={integrations.discord} />
              <IntegrationRow label="Home Assistant" ok={integrations.home_assistant} />
              <IntegrationRow label="Anthropic API" ok={integrations.anthropic} />
            </>
          )}
        </Card>

        <Card>
          <SectionTitle>Seneste tool-intent anmodninger</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={28} />)}
            </div>
          ) : (data?.recent_approvals || []).length === 0 ? (
            <EmptyState title="Ingen anmodninger endnu">Tool-intent godkendelser vises her.</EmptyState>
          ) : (
            <ScrollPanel maxHeight={200}>
              <div style={s({ display: 'flex', flexDirection: 'column', gap: 4 })}>
                {(data.recent_approvals || []).map((row, i) => (
                  <div key={i} style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', borderRadius: 7, border: `1px solid ${T.border0}`, background: T.bgOverlay })}>
                    <span style={s({ ...mono, fontSize: 10, color: T.accentText, minWidth: 120, flexShrink: 0 })}>{row.intent_type}</span>
                    <span style={s({ fontSize: 10, color: T.text3, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{row.intent_target}</span>
                    <StateChip state={row.approval_state} />
                  </div>
                ))}
              </div>
            </ScrollPanel>
          )}
        </Card>
      </div>
    </div>
  )
}

function GovernancePanel() {
  const { surfaces, loading } = useCognitiveSurfaces()

  if (loading) return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser governance...</div>
  if (!surfaces) return <div style={s({ padding: 24, color: T.text3 })}>Ingen data</div>

  const scr = surfaces.skill_contract_registry || {}
  const mwp = surfaces.memory_write_policy || {}
  const sr = surfaces.spaced_repetition || {}
  const sjw = surfaces.scheduled_job_windows || {}
  const ad = surfaces.automation_dsl || {}
  const ol = surfaces.outcome_learning || {}
  const je = surfaces.jobs_engine || {}
  const pml = surfaces.prompt_mutation_loop || {}

  return (
    <SurfaceGrid>
      <Section icon={Shield} title="Skill-kontrakter" active={scr.active}>
        <Summary text={scr.summary} />
        <KV label="Aktive kontrakter" value={scr.active_count} accent />
        <KV label="Kandidater" value={scr.candidate_count} />
        <KV label="Afvist" value={scr.rejected_count} />
      </Section>

      <Section icon={Lock} title="Hukommelses-politik" active={mwp.active}>
        <Summary text={mwp.summary} />
        <KV label="Skriv-niveau" value={mwp.write_level} accent />
        <KV label="Pending" value={mwp.pending_writes} />
        <KV label="Blokerede" value={mwp.blocked_writes} />
      </Section>

      <Section icon={Repeat} title="Spaced repetition" active={sr.active}>
        <Summary text={sr.summary} />
        <KV label="Aktive emner" value={sr.active_items} accent />
        <KV label="Forfaldne" value={sr.overdue_count} />
        <KV label="Gennemsnit EF" value={sr.avg_ef} />
      </Section>

      <Section icon={Clock} title="Job-vinduer" active={sjw.active}>
        <Summary text={sjw.summary} />
        <KV label="Aktive vinduer" value={sjw.active_windows} accent />
        <KV label="Næste åbner" value={sjw.next_window_opens?.slice(0, 16)} />
      </Section>

      <Section icon={FileCode} title="Automation DSL" active={ad.active}>
        <Summary text={ad.summary} />
        <KV label="Regler" value={ad.rule_count} accent />
        <KV label="Kørte i dag" value={ad.runs_today} />
        <KV label="Fejlede" value={ad.errors_today} />
      </Section>

      <Section icon={TrendingUp} title="Outcome-læring" active={ol.active}>
        <Summary text={ol.summary} />
        <KV label="Observationer" value={ol.observation_count} accent />
        <KV label="Mønstre" value={ol.pattern_count} />
        <KV label="Sidst opdateret" value={ol.last_updated?.slice(0, 16)} />
      </Section>

      <Section icon={Cpu} title="Jobs engine" active={je.active}>
        <Summary text={je.summary} />
        <KV label="Pending" value={je.pending_count} accent />
        <KV label="Kørt i dag" value={je.run_today} />
        <KV label="Fejlede" value={je.failed_today} />
      </Section>

      <Section icon={GitPullRequest} title="Prompt-mutation" active={pml.active}>
        <Summary text={pml.summary} />
        <KV label="Mutationer" value={pml.mutation_count} accent />
        <KV label="Aktiv mutation" value={pml.active_mutation} />
        <KV label="Sidst" value={pml.last_mutation_at?.slice(0, 16)} />
      </Section>
    </SurfaceGrid>
  )
}

const HARDENING_SUBTABS = [
  { id: 'security', label: 'Sikkerhed' },
  { id: 'governance', label: 'Governance' },
]

export function HardeningTab() {
  const [sub, setSub] = useState('security')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <ShieldCheck size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Hardening</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={HARDENING_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'security' ? <SecurityPanel /> : <GovernancePanel />}
    </div>
  )
}
```

Note: The GovernancePanel sections use the KV fields from the existing GovernanceTab.jsx. Read `apps/ui/src/components/mission-control/GovernanceTab.jsx` before writing this step to copy the exact KV labels and surface keys from each Section (there are 8 sections). The code above uses simplified KV rows as stubs — **replace them with the exact KV rows from GovernanceTab.jsx**.

- [ ] **Step 2: Remove Governance from MCTabBar.jsx**

Remove this line from `ALL_TABS`:
```js
  { id: 'governance', label: 'Governance', icon: ShieldCheck },
```
Also remove `ShieldCheck` from the import if it's only used there.

- [ ] **Step 3: Remove Governance from MissionControlPage.jsx**

Remove import:
```jsx
import { GovernanceTab } from '../components/mission-control/GovernanceTab'
```

Remove render block:
```jsx
          {activeTab === 'governance' ? <GovernanceTab /> : null}
```

- [ ] **Step 4: Verify build**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/components/mission-control/HardeningTab.jsx \
        apps/ui/src/components/mission-control/MCTabBar.jsx \
        apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(mc): merge Governance into Hardening tab (sub-tabs)"
```

---

## Task 4: Create ReflectionTab (SelfReview + Development + Continuity)

All three tabs use `data={sections.jarvis}` with callbacks from MissionControlPage. Create a wrapper that renders the right tab based on sub-tab state.

**Files:**
- Create: `apps/ui/src/components/mission-control/ReflectionTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Create ReflectionTab.jsx**

```jsx
import { useState } from 'react'
import { s, T } from '../../shared/theme/tokens'
import { SubTabs } from './shared'
import { SelfReviewTab } from './SelfReviewTab'
import { DevelopmentTab } from './DevelopmentTab'
import { ContinuityTab } from './ContinuityTab'
import { Eye } from 'lucide-react'

const REFLECTION_SUBTABS = [
  { id: 'self-review', label: 'Selvreview' },
  { id: 'development', label: 'Udvikling' },
  { id: 'continuity', label: 'Kontinuitet' },
]

export function ReflectionTab({ data, onOpenItem, onDevelopmentFocusAction }) {
  const [sub, setSub] = useState('self-review')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <Eye size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Reflection</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={REFLECTION_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'self-review' ? <SelfReviewTab data={data} onOpenItem={onOpenItem} /> : null}
      {sub === 'development' ? <DevelopmentTab data={data} onOpenItem={onOpenItem} onDevelopmentFocusAction={onDevelopmentFocusAction} /> : null}
      {sub === 'continuity' ? <ContinuityTab data={data} onOpenItem={onOpenItem} /> : null}
    </div>
  )
}
```

- [ ] **Step 2: Update MCTabBar.jsx**

In `ALL_TABS`, replace these three entries:
```js
  { id: 'self-review', label: 'Self-Review', icon: Shield },
  { id: 'continuity', label: 'Continuity', icon: Layers },
  { id: 'development', label: 'Development', icon: TrendingUp },
```

With this one entry:
```js
  { id: 'reflection', label: 'Reflection', icon: Eye },
```

Add `Eye` to the lucide-react import. Remove `Layers` and `TrendingUp` if they are no longer used elsewhere in MCTabBar.jsx.

- [ ] **Step 3: Update MissionControlPage.jsx**

Add import:
```jsx
import { ReflectionTab } from '../components/mission-control/ReflectionTab'
```

Remove these three imports:
```jsx
import { SelfReviewTab } from '../components/mission-control/SelfReviewTab'
import { ContinuityTab } from '../components/mission-control/ContinuityTab'
import { DevelopmentTab } from '../components/mission-control/DevelopmentTab'
```

Find line 74 (the `activeSectionData` assignment) — update the condition that references old IDs:
```js
// OLD:
const activeSectionData = sections[activeTab] || (activeTab === 'living-mind' || activeTab === 'self-review' || activeTab === 'continuity' || activeTab === 'development' ? sections.jarvis : null) || null
// NEW:
const activeSectionData = sections[activeTab] || (activeTab === 'living-mind' || activeTab === 'reflection' ? sections.jarvis : null) || null
```

Replace these three render blocks:
```jsx
          {activeTab === 'self-review' ? (
            <SelfReviewTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
          ) : null}

          {activeTab === 'continuity' ? (
            <ContinuityTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
          ) : null}

          {activeTab === 'development' ? (
            <DevelopmentTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
          ) : null}
```

With one:
```jsx
          {activeTab === 'reflection' ? (
            <ReflectionTab
              data={sections.jarvis}
              onOpenItem={openJarvisDetail}
              onDevelopmentFocusAction={actOnDevelopmentFocus}
            />
          ) : null}
```

- [ ] **Step 4: Verify build**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/components/mission-control/ReflectionTab.jsx \
        apps/ui/src/components/mission-control/MCTabBar.jsx \
        apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(mc): merge SelfReview+Development+Continuity into Reflection tab"
```

---

## Task 5: Merge Cost into Lab (sub-tabs)

LabTab currently self-fetches `/mc/lab`. CostTab receives `data={sections.cost}` from the phase A hook (which fetches `/mc/costs`). Instead of changing the data flow, LabTab will self-fetch `/mc/costs` directly in a new `CostPanel` sub-component.

**Files:**
- Modify: `apps/ui/src/components/mission-control/LabTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Update LabTab.jsx**

Replace the full contents of `apps/ui/src/components/mission-control/LabTab.jsx` with (preserving existing Lab panel and adding a Cost panel + sub-tabs):

```jsx
import { useEffect, useState } from 'react'
import { RefreshCcw, FlaskConical, DollarSign, Hash, AlertCircle } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel, EmptyState, Skeleton, SubTabs } from './shared'
import { backend } from '../../lib/adapters'
import { formatFreshness } from './meta'

const FAMILY_COLORS = {
  tool: T.blue,
  runtime: T.accent,
  heartbeat: T.green,
  memory: T.purple,
  cost: T.amber,
  channel: T.accentText,
  approvals: T.amber,
}

function FamilyChip({ family }) {
  const color = FAMILY_COLORS[family] || T.text3
  return (
    <span style={s({ ...mono, fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${color}18`, border: `1px solid ${color}35`, color, flexShrink: 0 })}>
      {family || 'other'}
    </span>
  )
}

function LabPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetchedAt, setFetchedAt] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await backend.getMissionControlLab()
        if (!cancelled) { setData(result); setFetchedAt(new Date().toISOString()) }
      } finally { if (!cancelled) setLoading(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  async function refresh() {
    setLoading(true)
    try {
      const result = await backend.getMissionControlLab()
      setData(result); setFetchedAt(new Date().toISOString())
    } finally { setLoading(false) }
  }

  const costs = data?.costs_today || {}
  const db = data?.db_stats || {}

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{fetchedAt ? formatFreshness(fetchedAt) : ''}</span>
        <button onClick={refresh} disabled={loading}
          style={s({ marginLeft: 'auto', padding: '4px 8px', borderRadius: 7, border: `1px solid ${T.border1}`, background: T.bgOverlay, color: T.text2, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 })}>
          <RefreshCcw size={11} />
        </button>
      </div>

      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="Kost i dag (USD)" value={loading ? '…' : `$${(costs.total_usd || 0).toFixed(4)}`} />
        <MetricCard label="Input tokens" value={loading ? '…' : (costs.input_tokens || 0).toLocaleString()} />
        <MetricCard label="Output tokens" value={loading ? '…' : (costs.output_tokens || 0).toLocaleString()} />
        <MetricCard label="Kald i dag" value={loading ? '…' : costs.calls ?? 0} />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
        <Card>
          <SectionTitle>Providers — i dag</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={28} />)}
            </div>
          ) : (data?.providers_today || []).length === 0 ? (
            <EmptyState title="Ingen kald endnu">Provider-statistik vises her.</EmptyState>
          ) : (
            <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
              <thead>
                <tr>
                  {['Provider', 'Kost USD', 'Tokens', 'Kald'].map((h) => (
                    <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '3px 6px' })}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data.providers_today || []).map((p) => (
                  <tr key={p.provider}
                    onMouseEnter={(e) => (e.currentTarget.style.background = T.bgHover)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.accentText })}>{p.provider}</td>
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.text1 })}>{p.cost_usd.toFixed(4)}</td>
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.text1 })}>{(p.input_tokens + p.output_tokens).toLocaleString()}</td>
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.text1 })}>{p.calls}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card>
          <SectionTitle>DB-statistik</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={24} />)}
            </div>
          ) : (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
              {[
                ['Events i alt', db.events],
                ['Visible runs', db.runs],
                ['Chat sessioner', db.sessions],
                ['Tool-intent godkendelser', db.approvals],
              ].map(([label, val]) => (
                <div key={label} style={s({ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${T.border0}` })}>
                  <span style={s({ fontSize: 11, color: T.text3 })}>{label}</span>
                  <span style={s({ ...mono, fontSize: 11, color: T.text1 })}>{(val ?? 0).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <SectionTitle>Seneste events</SectionTitle>
        {loading ? (
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 5 })}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={26} />)}
          </div>
        ) : (data?.recent_events || []).length === 0 ? (
          <EmptyState title="Ingen events endnu">Events vises her efterhånden som de sker.</EmptyState>
        ) : (
          <ScrollPanel maxHeight={240}>
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 4 })}>
              {(data.recent_events || []).map((ev) => (
                <div key={ev.id} style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', borderRadius: 7, border: `1px solid ${T.border0}`, background: T.bgOverlay })}>
                  <FamilyChip family={ev.family} />
                  <span style={s({ fontSize: 10, color: T.text2, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{ev.kind}</span>
                  <span style={s({ ...mono, fontSize: 9, color: T.text3, flexShrink: 0 })}>{formatFreshness(ev.created_at)}</span>
                </div>
              ))}
            </div>
          </ScrollPanel>
        )}
      </Card>
    </div>
  )
}

function CostPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await fetch('/mc/costs').then((r) => r.json())
        if (!cancelled) setData(result)
      } finally { if (!cancelled) setLoading(false) }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const cost = data || {}
  const providers = cost.providers || []

  if (loading) {
    return (
      <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
        <div style={s({ display: 'flex', gap: 10 })}>
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={56} />)}
        </div>
      </div>
    )
  }

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="24h Cost (USD)" value={`$${Number(cost.cost_24h_usd || 0).toFixed(4)}`} icon={DollarSign} />
        <MetricCard label="24h Tokens" value={(cost.tokens_24h || 0).toLocaleString()} icon={Hash} />
        <MetricCard label="Unknown Pricing (24h)" value={cost.unknown_pricing_24h || 0} icon={AlertCircle} />
      </div>

      <Card>
        <SectionTitle>Top Providers (24h)</SectionTitle>
        {providers.length === 0 ? (
          <EmptyState title="Ingen data">Ingen provider-data endnu.</EmptyState>
        ) : (
          <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
            <thead>
              <tr>
                {['Provider', 'Cost USD', 'Tokens', 'Calls'].map((h) => (
                  <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '4px 8px' })}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.provider}
                  onMouseEnter={(e) => (e.currentTarget.style.background = T.bgHover)}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.accentText })}>{p.provider}</td>
                  <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{Number(p.cost_usd || 0).toFixed(4)}</td>
                  <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{p.tokens}</td>
                  <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{p.calls}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}

const LAB_SUBTABS = [
  { id: 'lab', label: 'Lab' },
  { id: 'cost', label: 'Omkostninger' },
]

export function LabTab() {
  const [sub, setSub] = useState('lab')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <FlaskConical size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Lab</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={LAB_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'lab' ? <LabPanel /> : <CostPanel />}
    </div>
  )
}
```

- [ ] **Step 2: Remove Cost from MCTabBar.jsx**

Remove this line from `ALL_TABS`:
```js
  { id: 'cost', label: 'Cost', icon: DollarSign },
```
Remove `DollarSign` from imports if unused elsewhere.

- [ ] **Step 3: Update MissionControlPage.jsx**

Remove import:
```jsx
import { CostTab } from '../components/mission-control/CostTab'
```

Remove render block:
```jsx
          {activeTab === 'cost' ? <CostTab data={sections.cost} /> : null}
```

- [ ] **Step 4: Verify build**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/components/mission-control/LabTab.jsx \
        apps/ui/src/components/mission-control/MCTabBar.jsx \
        apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(mc): merge Cost into Lab tab (sub-tabs)"
```

---

## Task 6: Create MindTab (LivingMind + Soul + Cognitive)

LivingMind uses `data={sections.jarvis}` with callbacks. Soul and CognitiveState are self-fetching. A `MindTab` wrapper renders sub-tabs: "Bevidsthed" (LivingMind), "Sjæl" (Soul), "Kognition" (CognitiveState).

**Files:**
- Create: `apps/ui/src/components/mission-control/MindTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Create MindTab.jsx**

```jsx
import { useState } from 'react'
import { Brain } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'
import { SubTabs } from './shared'
import { LivingMindTab } from './LivingMindTab'
import { SoulTab } from './SoulTab'
import { CognitiveStateTab } from './CognitiveStateTab'

const MIND_SUBTABS = [
  { id: 'consciousness', label: 'Bevidsthed' },
  { id: 'soul', label: 'Sjæl' },
  { id: 'cognitive', label: 'Kognition' },
]

export function MindTab({ data, onOpenItem, onHeartbeatTick, heartbeatBusy }) {
  const [sub, setSub] = useState('consciousness')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <Brain size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Mind</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={MIND_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'consciousness' ? (
        <LivingMindTab data={data} onOpenItem={onOpenItem} onHeartbeatTick={onHeartbeatTick} heartbeatBusy={heartbeatBusy} />
      ) : null}
      {sub === 'soul' ? <SoulTab /> : null}
      {sub === 'cognitive' ? <CognitiveStateTab /> : null}
    </div>
  )
}
```

- [ ] **Step 2: Update MCTabBar.jsx**

Replace these three entries in `ALL_TABS`:
```js
  { id: 'living-mind', label: 'Living Mind', icon: Brain },
  { id: 'soul', label: 'Soul', icon: Hourglass },
  { id: 'cognitive-state', label: 'Cognitive', icon: Fingerprint },
```

With one:
```js
  { id: 'mind', label: 'Mind', icon: Brain },
```

Remove `Hourglass` and `Fingerprint` from the import if no longer used.

- [ ] **Step 3: Update MissionControlPage.jsx**

Add import:
```jsx
import { MindTab } from '../components/mission-control/MindTab'
```

Remove these imports:
```jsx
import { LivingMindTab } from '../components/mission-control/LivingMindTab'
import { SoulTab } from '../components/mission-control/SoulTab'
import { CognitiveStateTab } from '../components/mission-control/CognitiveStateTab'
```

Update line 74 (activeSectionData):
```js
// Replace 'living-mind' with 'mind' in the condition:
const activeSectionData = sections[activeTab] || (activeTab === 'mind' || activeTab === 'reflection' ? sections.jarvis : null) || null
```

Replace these three render blocks:
```jsx
          {activeTab === 'living-mind' ? (
            <LivingMindTab
              data={sections.jarvis}
              onOpenItem={openJarvisDetail}
              onHeartbeatTick={actOnHeartbeatTick}
              heartbeatBusy={isRefreshing}
            />
          ) : null}
          // ...
          {activeTab === 'soul' ? <SoulTab /> : null}
          // ...
          {activeTab === 'cognitive-state' ? <CognitiveStateTab /> : null}
```

With one:
```jsx
          {activeTab === 'mind' ? (
            <MindTab
              data={sections.jarvis}
              onOpenItem={openJarvisDetail}
              onHeartbeatTick={actOnHeartbeatTick}
              heartbeatBusy={isRefreshing}
            />
          ) : null}
```

- [ ] **Step 4: Check for any 'living-mind' references elsewhere**

```bash
grep -rn "living-mind\|living_mind\|soul\b\|cognitive-state" /media/projects/jarvis-v2/apps/ui/src --include="*.jsx" --include="*.js" | grep -v "node_modules" | grep -v "SoulTab\|CognitiveState\|MindTab"
```

Update any navigation calls in OverviewTab or elsewhere that jump to `'living-mind'` or `'soul'` — change them to `'mind'`.

- [ ] **Step 5: Verify build**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/components/mission-control/MindTab.jsx \
        apps/ui/src/components/mission-control/MCTabBar.jsx \
        apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(mc): merge LivingMind+Soul+Cognitive into Mind tab"
```

---

## Task 7: Create OpsTab (Operations + Agents)

Operations has many props from MissionControlPage. Agents is self-fetching. A wrapper `OpsTab` renders sub-tabs: "Operationer" (Operations content) | "Agenter" (AgentsTab).

**Files:**
- Create: `apps/ui/src/components/mission-control/OpsTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Create OpsTab.jsx**

```jsx
import { useState } from 'react'
import { Bot } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'
import { SubTabs } from './shared'
import { OperationsTab } from './OperationsTab'
import { AgentsTab } from './AgentsTab'

const OPS_SUBTABS = [
  { id: 'operations', label: 'Operationer' },
  { id: 'agents', label: 'Agenter' },
]

export function OpsTab({
  data,
  selection,
  onSelectionChange,
  onOpenRun,
  onOpenSession,
  onOpenApproval,
  onOpenItem,
  onToolIntentAction,
  toolIntentActionBusy,
  toolIntentActionError,
  thoughtProposals,
  onResolveThoughtProposal,
}) {
  const [sub, setSub] = useState('operations')

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 })}>
        <Bot size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Ops</span>
        <div style={s({ marginLeft: 'auto' })}>
          <SubTabs tabs={OPS_SUBTABS} active={sub} onChange={setSub} />
        </div>
      </div>
      {sub === 'operations' ? (
        <OperationsTab
          data={data}
          selection={selection}
          onSelectionChange={onSelectionChange}
          onOpenRun={onOpenRun}
          onOpenSession={onOpenSession}
          onOpenApproval={onOpenApproval}
          onOpenItem={onOpenItem}
          onToolIntentAction={onToolIntentAction}
          toolIntentActionBusy={toolIntentActionBusy}
          toolIntentActionError={toolIntentActionError}
          thoughtProposals={thoughtProposals}
          onResolveThoughtProposal={onResolveThoughtProposal}
        />
      ) : null}
      {sub === 'agents' ? <AgentsTab /> : null}
    </div>
  )
}
```

- [ ] **Step 2: Update MCTabBar.jsx**

Replace these two entries:
```js
  { id: 'operations', label: 'Operations', icon: Bot },
  // ...
  { id: 'agents', label: 'Agents', icon: Users },
```

With one (keep `'operations'` as the ID so any deep links still work):
```js
  { id: 'operations', label: 'Ops', icon: Bot },
```

Remove `Users` from the import if unused elsewhere.

- [ ] **Step 3: Update MissionControlPage.jsx**

Add import:
```jsx
import { OpsTab } from '../components/mission-control/OpsTab'
```

Remove these imports:
```jsx
import { OperationsTab } from '../components/mission-control/OperationsTab'
import { AgentsTab } from '../components/mission-control/AgentsTab'
```

Replace the Operations render block and the separate Agents render block:
```jsx
          {activeTab === 'operations' ? (
            <OperationsTab
              data={sections.operations}
              selection={selection}
              onSelectionChange={onSelectionChange}
              onOpenRun={openRunDetail}
              onOpenSession={openSessionDetail}
              onOpenApproval={openApprovalDetail}
              onOpenItem={openJarvisDetail}
              onToolIntentAction={actOnToolIntent}
              toolIntentActionBusy={toolIntentActionBusy}
              toolIntentActionError={toolIntentActionError}
              thoughtProposals={sections.jarvis?.thoughtProposals || null}
              onResolveThoughtProposal={async (id, decision) => {
                try {
                  await fetch(`/mc/thought-proposals/${id}/resolve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ decision }),
                  })
                  refreshAll()
                } catch (_) {}
              }}
            />
          ) : null}
          // ...
          {activeTab === 'agents' ? <AgentsTab /> : null}
```

With:
```jsx
          {activeTab === 'operations' ? (
            <OpsTab
              data={sections.operations}
              selection={selection}
              onSelectionChange={onSelectionChange}
              onOpenRun={openRunDetail}
              onOpenSession={openSessionDetail}
              onOpenApproval={openApprovalDetail}
              onOpenItem={openJarvisDetail}
              onToolIntentAction={actOnToolIntent}
              toolIntentActionBusy={toolIntentActionBusy}
              toolIntentActionError={toolIntentActionError}
              thoughtProposals={sections.jarvis?.thoughtProposals || null}
              onResolveThoughtProposal={async (id, decision) => {
                try {
                  await fetch(`/mc/thought-proposals/${id}/resolve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ decision }),
                  })
                  refreshAll()
                } catch (_) {}
              }}
            />
          ) : null}
```

- [ ] **Step 4: Verify build**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2
git add apps/ui/src/components/mission-control/OpsTab.jsx \
        apps/ui/src/components/mission-control/MCTabBar.jsx \
        apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(mc): merge Agents into Operations → Ops tab"
```

---

## Task 8: Final verification

- [ ] **Step 1: Count tabs**

```bash
grep "id:" /media/projects/jarvis-v2/apps/ui/src/components/mission-control/MCTabBar.jsx | wc -l
```

Expected: 14 tabs.

- [ ] **Step 2: Full build check**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -10
```

Expected: successful build, no errors.

- [ ] **Step 3: Verify no dead references**

```bash
grep -rn "activeTab === 'soul'\|activeTab === 'autonomy'\|activeTab === 'governance'\|activeTab === 'cost'\|activeTab === 'living-mind'\|activeTab === 'self-review'\|activeTab === 'continuity'\|activeTab === 'development'\|activeTab === 'agents'\|activeTab === 'cognitive-state'" /media/projects/jarvis-v2/apps/ui/src 2>/dev/null
```

Expected: no matches.

- [ ] **Step 4: Check navigateTo calls still work**

```bash
grep -rn "navigateTo\|onJump" /media/projects/jarvis-v2/apps/ui/src --include="*.jsx" | grep -v "node_modules"
```

Update any calls that use old tab IDs (e.g. `navigateTo('living-mind')` → `navigateTo('mind')`).
