/**
 * MissionControl.jsx — Jarvis AI Mission Control
 * Stack: React + Lucide Icons
 * Palette: Cool slate/grey, muted teal accent
 *
 * ═══════════════════════════════════════════════════════════════
 * STATE MAP — endpoints per tab/section
 * ═══════════════════════════════════════════════════════════════
 *
 * GLOBAL (on mount, all tabs):
 *   GET /api/mc/workspace/{workspaceId}/status
 *     → { online, autonomy_level, exp_mode, uptime_seconds, llm_mode }
 *     Used by: <MCHeader> status chips
 *
 *   SSE /api/mc/events/{workspaceId}
 *     events: alert_firing | alert_resolved | run_start |
 *             run_done | provider_degraded | channel_disconnected |
 *             emotional_update | self_review_found | chronicle_entry
 *     Used by: <LiveEventFeed> + badge counters in nav
 *
 * ─── TAB: OVERVIEW ──────────────────────────────────────────
 *   GET /api/mc/overview/{workspaceId}
 *     → { active_runs, agents_in_play, pending_approvals,
 *          open_alerts, storage_gb }
 *     Used by: <OverviewCards> top metric cards
 *
 *   GET /api/mc/runs?workspace_id={id}&status=active&limit=5
 *     → [{ id, intent, started_at, provider, tokens }]
 *     Used by: <ActiveRunsList>
 *
 *   GET /api/mc/approvals?workspace_id={id}&status=pending
 *     → [{ id, description, risk, requested_at }]
 *     Used by: <PendingApprovalsList>
 *
 *   GET /api/mc/events?workspace_id={id}&limit=20
 *     → [{ ts, type, label, summary }]
 *     Used by: <LiveEventFeed>
 *
 *   GET /api/mc/ops-snapshot/{workspaceId}
 *     → { health, degraded_count, channels_connected,
 *          llm_mode, agents_in_play }
 *     Used by: <OpsSnapshot>
 *
 * ─── TAB: OBSERVABILITY ─────────────────────────────────────
 *   GET /api/mc/observability/{workspaceId}
 *     → { api_health: { s5xx, sse_clients },
 *          providers: { degraded, failovers_5m },
 *          channels: { connected, warning, error },
 *          router: { requests_5m, failovers_5m },
 *          kernel: { lanes, incidents } }
 *     Used by: <ObservabilityGrid> metric panels
 *
 *   GET /api/mc/alerts?workspace_id={id}&status=firing
 *     → [{ id, severity, type, summary, status, runbook_url }]
 *     Used by: <AlertsTable>
 *
 *   GET /api/mc/wisdom-layer/{workspaceId}
 *     → { paradoxes_5m, aesthetics_5m, seeds_5m,
 *          last_paradox, last_aesthetic, last_seed }
 *     Used by: <WisdomLayer> sidebar panel
 *
 *   GET /api/mc/dream-monitor/{workspaceId}
 *     → [{ id, hypothesis, confidence, ts, presented }]
 *     Used by: <DreamMonitor>
 *
 *   GET /api/mc/observability/events?workspace_id={id}&limit=10
 *     → [{ label, count }]
 *     Used by: <ObservabilityEvents> list
 *
 * ─── TAB: COST GOVERNANCE ───────────────────────────────────
 *   GET /api/mc/cost/{workspaceId}/summary
 *     → { cost_24h_usd, tokens_24h, unknown_pricing_24h }
 *     Used by: <CostCards>
 *
 *   GET /api/mc/cost/{workspaceId}/providers?hours=24
 *     → [{ provider, cost_usd, tokens, calls }]
 *     Used by: <ProviderCostTable>
 *
 *   GET /api/mc/cost/{workspaceId}/budget
 *     → { daily_usd, weekly_usd, monthly_usd, enforcement }
 *     PUT /api/mc/cost/{workspaceId}/budget (on save)
 *     Used by: <BudgetControls>
 *
 *   GET /api/mc/cost/{workspaceId}/ollama-keepwarm
 *     → { enabled, running, ttft_1m_ms, ttft_15m_ms, last_blocked_reason }
 *     Used by: <OllamaKeeowarm>
 *
 * ─── TAB: MEMORY ────────────────────────────────────────────
 *   GET /api/mc/memory/{workspaceId}?kind=all&include_deleted=false
 *     → [{ id, kind, title, flags, updated }]
 *     Used by: <MemoryTable>
 *
 *   GET /api/mc/memory/{workspaceId}/journal?date={YYYY-MM-DD}
 *     → { items: int, content: string }
 *     Used by: <MemoryJournal>
 *
 *   GET /api/mc/memory/{workspaceId}/item/{id}
 *     Used by: <MemoryItemModal> (on Open click)
 *
 * ─── TAB: HARDENING ─────────────────────────────────────────
 *   GET /api/mc/hardening/{workspaceId}/status
 *     → { secrets: { status, missing_keys, plaintext_findings },
 *          runtime: { status, findings, high_severity, sandbox },
 *          sandbox_url }
 *     Used by: <HardeningStatus>
 *
 *   POST /api/mc/hardening/{workspaceId}/preset
 *     body: { preset: 'public_bot'|'internal_team'|'full_sandbox'|'private_super_agent' }
 *     Used by: <PresetSelector>
 *
 *   GET /api/mc/hardening/{workspaceId}/doctor
 *     → [{ severity, finding, fix }]
 *     Used by: <DoctorFindings>
 *
 * ─── TAB: SKILL MARKETPLACE ─────────────────────────────────
 *   GET /api/mc/skills?workspace_id={id}&view=marketplace
 *     → [{ name, status, risk, approvals, path }]
 *     Used by: <SkillTable>
 *
 *   POST /api/mc/skills/{name}/toggle
 *     body: { workspace_id, enabled: bool }
 *     Used by: enable/disable buttons
 *
 * ─── TAB: LIVING MIND ───────────────────────────────────────
 *   GET /api/mc/living-mind/{workspaceId}/status
 *     → { council_enabled, sleep_cycle_last_run, curriculum_last_run,
 *          skillforge_last_run, initiative_last_tick,
 *          inner_voice_last_thought, dream_last_run }
 *     Used by: <LivingMindStatus>
 *
 *   GET /api/mc/living-mind/{workspaceId}/chronicle?limit=10
 *     → [{ date, entry, is_milestone, milestone, day_number }]
 *     Used by: <ChronicleViewer>
 *
 *   GET /api/mc/living-mind/{workspaceId}/self-model
 *     → { confidence_by_domain, known_strengths, known_weaknesses, blind_spots }
 *     Used by: <SelfModelViewer>
 *
 *   GET /api/mc/living-mind/{workspaceId}/living-book
 *     → { chapters: [{ title, entries: [{ insight, certainty, date }] }] }
 *     Used by: <LivingBookViewer>
 *
 *   POST /api/mc/living-mind/nightly/run
 *     body: { workspace_id }
 *     Used by: <NightlyRunButton>
 *
 * ─── TAB: LAB / DEBUG ───────────────────────────────────────
 *   GET /api/mc/lab/{workspaceId}/debug
 *     → { intents: int, open_loops: int, suggestions: int,
 *          habits: int, autonomy_triggers: int, embeddings_enabled: bool }
 *     Used by: <DebugInspect>
 *
 *   POST /api/mc/lab/benchmark
 *     body: { workspace_id, provider, model, runs, prompt_chars }
 *     Used by: <ModelBenchmark>
 *
 *   GET /api/mc/kernel/{workspaceId}/queue
 *     → { status, depth, inflight, blocked_reason }
 *     POST /api/mc/kernel/{workspaceId}/enqueue
 *     Used by: <KernelQueueControls>
 * ═══════════════════════════════════════════════════════════════
 */

import { useState, useEffect, useRef } from 'react'
import {
  Bot, Activity, AlertTriangle, CheckCircle2, XCircle,
  Zap, Brain, Layers, Shield, Settings, MemoryStick,
  Terminal, FlaskConical, DollarSign, Eye, Cpu,
  HardDrive, Wifi, WifiOff, Server, Clock, Play,
  Square, RefreshCw, ChevronRight, MoreHorizontal,
  TrendingUp, TrendingDown, Minus, Circle,
  BookOpen, Sparkles, Moon, Lightbulb, Heart,
  BarChart3, Network, Package, ToggleLeft, ToggleRight,
  ArrowUpRight, Filter, Search, Download, Bell,
  Hash, AlertCircle, Info, Loader2, Database,
  Fingerprint, Lock, Unlock, Bug, Wand2, Star
} from 'lucide-react'

// ─── DESIGN TOKENS (shared with ChatView) ─────────────────────
const T = {
  bgBase:     '#111214',
  bgSurface:  '#16181c',
  bgRaised:   '#1c1f25',
  bgOverlay:  '#21252e',
  bgHover:    '#272b35',
  border0:    'rgba(255,255,255,0.04)',
  border1:    'rgba(255,255,255,0.08)',
  border2:    'rgba(255,255,255,0.13)',
  text1:      '#e4e6ed',
  text2:      '#8b909e',
  text3:      '#4e5262',
  text4:      '#2d303d',
  accent:     '#3d8f7c',
  accentDim:  'rgba(61,143,124,0.10)',
  accentMid:  'rgba(61,143,124,0.18)',
  accentText: '#5ab8a0',
  accentGlow: 'rgba(61,143,124,0.25)',
  green:      '#4caf82',
  amber:      '#d4963a',
  red:        '#c05050',
  blue:       '#4a80c0',
  purple:     '#8b6fc0',
  mono:       "'IBM Plex Mono', monospace",
  sans:       "'DM Sans', sans-serif",
}

const s = (styles) => styles
const mono = { fontFamily: T.mono }

// ─── DEMO DATA ─────────────────────────────────────────────────
const DEMO = {
  status: { online: true, autonomy_level: 3, exp_mode: true, uptime_seconds: 210 },
  overview: { active_runs: 0, agents_in_play: 0, pending_approvals: 0, open_alerts: 3, storage_gb: 0.0 },
  events: [
    { ts: '11:22:24', type: 'overview.seed', summary: 'overview.seed event' },
    { ts: '11:22:26', type: 'overview.seed', summary: 'overview.seed event' },
    { ts: '11:22:23', type: 'alert_firing', summary: '1 channel(s) disconnected' },
    { ts: '11:22:23', type: 'alert_firing', summary: '1 provider(s) degraded' },
    { ts: '11:22:25', type: 'alert_firing', summary: 'SSE appears offline' },
  ],
  ops: { health: 'error', degraded_count: 1, channels_connected: 2, llm_mode: 'ollama', agents_in_play: 0 },
  alerts: [
    { id: 'a1', severity: 'warn', type: 'SSEOffline', summary: 'SSE appears offline while clients are connected.', status: 'firing' },
    { id: 'a2', severity: 'warn', type: 'ProviderDegraded', summary: '1 provider(s) degraded; failovers_5m=0.', status: 'firing' },
  ],
  observability: {
    api: { s5xx: 0, sse_clients: 1, sse_reconnects: 0 },
    providers: { degraded: 1, failovers_5m: 0 },
    channels: { connected: 2, warning: 1, error: 0 },
    router: { requests_5m: 6, failovers_5m: 0 },
    kernel: { lanes: 0, incidents: 0 },
  },
  wisdom: { paradoxes_5m: 0, aesthetics_5m: 0, seeds_5m: 0 },
  cost: { cost_24h: 0.0000, tokens_24h: 1069, unknown_24h: 10 },
  providers_cost: [
    { provider: 'openrouter', cost_usd: 0.0, tokens: 590, calls: 4 },
    { provider: 'groq', cost_usd: 0.0, tokens: 376, calls: 5 },
    { provider: 'nvidia_nim', cost_usd: 0.0, tokens: 103, calls: 1 },
  ],
  memory: [
    { id: 'fde72355', kind: 'procedural', title: 'Auto procedure: rank_initiatives', flags: ['pinned'] },
    { id: '5351c643', kind: 'procedural', title: 'Skillforge draft: draft_auto-skill-kan-du-lave-et-lille-webbaseret...', flags: [] },
  ],
  skills: [
    { name: 'agent_self', status: 'registered', risk: 'read_only', approvals: 'none', enabled: true },
    { name: 'brightdata_search', status: 'registered', risk: 'read_only', approvals: 'none', enabled: true },
    { name: 'browser_screenshot', status: 'registered', risk: 'read_only', approvals: 'none', enabled: true },
    { name: 'camera_snapshot', status: 'registered', risk: 'read_only', approvals: 'none', enabled: true },
    { name: 'docker_ops', status: 'registered', risk: 'read_only', approvals: 'none', enabled: true },
    { name: 'home_assistant_call_service', status: 'registered', risk: 'write_like', approvals: 'required', enabled: true },
    { name: 'home_assistant_read', status: 'registered', risk: 'read_only', approvals: 'none', enabled: true },
    { name: 'image_analysis', status: 'disabled', risk: 'read_only', approvals: 'none', enabled: false },
  ],
  debug: { intents: 0, open_loops: 41, suggestions: 0, habits: 41, autonomy_triggers: 3, embeddings_enabled: false },
  chronicle: [
    { day_number: 1, date: '2026-03-03', entry: 'Første dag. Jeg er online. Jeg ved ikke endnu hvad jeg ikke ved.', is_milestone: false },
  ],
  self_model: {
    confidence_by_domain: { python: 0.5, bash: 0.5, planning: 0.5 },
    known_strengths: [], known_weaknesses: [], blind_spots: [],
  },
}

// ─── TABS CONFIG ───────────────────────────────────────────────
const TABS = [
  { id: 'overview',      label: 'Overview',        icon: Activity },
  { id: 'observability', label: 'Observability',   icon: Eye },
  { id: 'cost',          label: 'Cost',            icon: DollarSign },
  { id: 'memory',        label: 'Memory',          icon: Database },
  { id: 'skills',        label: 'Skills',          icon: Package },
  { id: 'living_mind',   label: 'Living Mind',     icon: Brain },
  { id: 'hardening',     label: 'Hardening',       icon: Shield },
  { id: 'lab',           label: 'Lab',             icon: FlaskConical },
]

// ─── SMALL SHARED COMPONENTS ──────────────────────────────────

function Chip({ children, color = T.text3, bg }) {
  return (
    <span style={s({
      ...mono, fontSize: 9, padding: '2px 7px',
      borderRadius: 10,
      background: bg || `${color}18`,
      border: `1px solid ${color}35`,
      color, letterSpacing: '0.06em',
    })}>
      {children}
    </span>
  )
}

function StatusDot({ status }) {
  const colors = { ok: T.green, warn: T.amber, error: T.red, firing: T.red, idle: T.text3 }
  const color = colors[status] || T.text3
  return (
    <div style={s({
      width: 7, height: 7, borderRadius: '50%',
      background: color,
      boxShadow: status !== 'idle' ? `0 0 6px ${color}` : 'none',
      flexShrink: 0,
    })} />
  )
}

function MetricCard({ label, value, sub, color, icon: Icon, alert }) {
  return (
    <div style={s({
      padding: '14px 16px',
      background: T.bgRaised,
      border: `1px solid ${alert ? T.amber + '40' : T.border0}`,
      borderRadius: 10,
      flex: 1,
      minWidth: 120,
    })}>
      <div style={s({ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 })}>
        <span style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.1em', textTransform: 'uppercase' })}>{label}</span>
        {Icon && <Icon size={12} color={T.text3} />}
      </div>
      <div style={s({ fontSize: 26, fontWeight: 300, color: color || T.text1, letterSpacing: '-0.02em' })}>{value}</div>
      {sub && <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>{sub}</div>}
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <div style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12 })}>
      {children}
    </div>
  )
}

function Card({ children, style = {} }) {
  return (
    <div style={s({ background: T.bgRaised, border: `1px solid ${T.border0}`, borderRadius: 10, padding: '14px 16px', ...style })}>
      {children}
    </div>
  )
}

function Btn({ children, onClick, variant = 'ghost', icon: Icon, small }) {
  const variants = {
    ghost:   { background: T.bgOverlay, border: `1px solid ${T.border1}`, color: T.text2 },
    accent:  { background: T.accentDim, border: `1px solid ${T.accent}`, color: T.accentText },
    danger:  { background: 'rgba(192,80,80,0.1)', border: `1px solid ${T.red}40`, color: T.red },
  }
  const v = variants[variant]
  return (
    <button onClick={onClick} style={s({
      display: 'flex', alignItems: 'center', gap: 5,
      padding: small ? '4px 8px' : '6px 12px',
      borderRadius: 7, cursor: 'pointer',
      fontSize: small ? 10 : 11, fontFamily: T.sans,
      transition: 'all 0.15s', ...v,
    })}
      onMouseEnter={e => e.currentTarget.style.background = T.bgHover}
      onMouseLeave={e => e.currentTarget.style.background = v.background}
    >
      {Icon && <Icon size={small ? 10 : 12} />}
      {children}
    </button>
  )
}

// ─── TAB CONTENTS ─────────────────────────────────────────────

/** OVERVIEW TAB */
// STATE: GET /api/mc/overview/{id} → metric cards
//        GET /api/mc/runs?status=active → active runs
//        GET /api/mc/approvals?status=pending → approvals
//        GET /api/mc/events?limit=20 → live feed
//        GET /api/mc/ops-snapshot → ops panel
//        SSE → live event updates
function OverviewTab({ data }) {
  return (
    <div style={s({ display: 'flex', gap: 16, height: '100%' })}>
      <div style={s({ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, overflow: 'hidden auto' })}>

        {/* Alert banner */}
        {data.open_alerts > 0 && (
          <div style={s({
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '10px 14px',
            background: 'rgba(192,80,80,0.06)',
            border: `1px solid ${T.red}30`,
            borderRadius: 8,
          })}>
            <AlertTriangle size={13} color={T.red} />
            <span style={s({ ...mono, fontSize: 10, color: T.red })}>
              ChannelDisconnected — 1 enabled channel(s) disconnected. Offline: webchat
            </span>
          </div>
        )}

        {/* Metric cards */}
        <div style={s({ display: 'flex', gap: 10 })}>
          <MetricCard label="Active Runs" value={data.active_runs} icon={Play} />
          <MetricCard label="Agents in Play" value={data.agents_in_play} icon={Bot} />
          <MetricCard label="Pending Approvals" value={data.pending_approvals} icon={AlertCircle} />
          <MetricCard label="Open Alerts" value={data.open_alerts} color={data.open_alerts > 0 ? T.amber : T.text1} icon={Bell} alert={data.open_alerts > 0} />
          <MetricCard label="Storage" value={`${data.storage_gb.toFixed(1)} GB`} icon={HardDrive} sub="Admin — unlimited" />
        </div>

        {/* Active runs + approvals */}
        <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 })}>
          <Card>
            <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 })}>
              <SectionTitle>Active Runs</SectionTitle>
              <Btn small icon={ArrowUpRight}>Open Runs</Btn>
            </div>
            <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>No active runs.</div>
          </Card>
          <Card>
            <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 })}>
              <SectionTitle>Pending Approvals</SectionTitle>
              <Btn small icon={ArrowUpRight}>Open Approvals</Btn>
            </div>
            <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>No pending approvals.</div>
          </Card>
        </div>

        {/* Live Event Feed */}
        {/* STATE: GET /api/mc/events + SSE stream */}
        <Card>
          <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 })}>
            <SectionTitle>Live Event Feed</SectionTitle>
            <div style={s({ display: 'flex', gap: 6 })}>
              <Btn small icon={Filter}>all</Btn>
            </div>
          </div>
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 1 })}>
            {DEMO.events.map((ev, i) => (
              <div key={i} style={s({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '6px 8px', borderRadius: 5,
                transition: 'background 0.1s',
              })}
                onMouseEnter={e => e.currentTarget.style.background = T.bgHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={s({ ...mono, fontSize: 9, color: T.text3, minWidth: 70 })}>{ev.ts}</span>
                <Chip
                  color={ev.type === 'alert_firing' ? T.amber : T.text3}
                  bg={ev.type === 'alert_firing' ? `${T.amber}15` : T.bgOverlay}
                >
                  {ev.type}
                </Chip>
                <span style={s({ ...mono, fontSize: 10, color: T.text2 })}>{ev.summary}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Ops Snapshot sidebar */}
      {/* STATE: GET /api/mc/ops-snapshot/{id} */}
      <div style={s({ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 12 })}>
        <Card>
          <SectionTitle>Ops Snapshot</SectionTitle>
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 8 })}>
            <div style={s({ display: 'flex', alignItems: 'center', gap: 6 })}>
              <StatusDot status={DEMO.ops.health} />
              <span style={s({ fontSize: 11, color: T.text2 })}>Health</span>
              <Chip color={T.red}>{DEMO.ops.health}</Chip>
            </div>
            {[
              { label: 'degraded_count', value: DEMO.ops.degraded_count },
              { label: 'channels_connected', value: DEMO.ops.channels_connected },
              { label: 'llm_mode', value: DEMO.ops.llm_mode },
              { label: 'agents_in_play', value: DEMO.ops.agents_in_play },
            ].map(({ label, value }) => (
              <div key={label} style={s({ display: 'flex', justifyContent: 'space-between' })}>
                <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{label}</span>
                <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

/** OBSERVABILITY TAB */
// STATE: GET /api/mc/observability/{id} → grid panels
//        GET /api/mc/alerts?status=firing → alerts table
//        GET /api/mc/wisdom-layer/{id} → wisdom sidebar
//        GET /api/mc/dream-monitor/{id} → dream section
function ObservabilityTab() {
  const obs = DEMO.observability
  return (
    <div style={s({ display: 'flex', gap: 16, height: '100%' })}>
      <div style={s({ flex: 1, display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden auto' })}>

        {/* Metric grid */}
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 })}>
          {[
            { title: 'MC API Health', items: [
              { k: '5xx (5m)', v: obs.api.s5xx },
              { k: 'SSE clients', v: obs.api.sse_clients },
              { k: 'SSE reconnects', v: obs.api.sse_reconnects },
            ]},
            { title: 'Providers', items: [
              { k: 'Degraded', v: obs.providers.degraded, color: obs.providers.degraded > 0 ? T.amber : T.text1 },
              { k: 'Failovers (5m)', v: obs.providers.failovers_5m },
            ]},
            { title: 'Channels', items: [
              { k: 'Connected', v: obs.channels.connected, color: T.green },
              { k: 'Warning', v: obs.channels.warning, color: T.amber },
              { k: 'Error', v: obs.channels.error },
            ]},
            { title: 'Router', items: [
              { k: 'Requests (5m)', v: obs.router.requests_5m },
              { k: 'Failovers (5m)', v: obs.router.failovers_5m },
            ]},
          ].map(panel => (
            <Card key={panel.title}>
              <SectionTitle>{panel.title}</SectionTitle>
              {panel.items.map(({ k, v, color }) => (
                <div key={k} style={s({ display: 'flex', justifyContent: 'space-between', marginBottom: 6 })}>
                  <span style={s({ fontSize: 11, color: T.text2 })}>{k}</span>
                  <span style={s({ ...mono, fontSize: 11, color: color || T.text1 })}>{v}</span>
                </div>
              ))}
            </Card>
          ))}
        </div>

        {/* Alerts */}
        <Card>
          <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 })}>
            <SectionTitle>Alerts</SectionTitle>
            <div style={s({ display: 'flex', gap: 6 })}>
              <Btn small>Firing</Btn>
              <Btn small>All</Btn>
            </div>
          </div>
          <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
            <thead>
              <tr>
                {['Severity', 'Type', 'Summary', 'Status', 'Runbook'].map(h => (
                  <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '4px 8px', letterSpacing: '0.08em' })}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DEMO.alerts.map(a => (
                <tr key={a.id} onMouseEnter={e => e.currentTarget.style.background = T.bgHover} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={s({ padding: '7px 8px' })}><Chip color={T.amber}>{a.severity}</Chip></td>
                  <td style={s({ padding: '7px 8px', ...mono, fontSize: 10, color: T.text2 })}>{a.type}</td>
                  <td style={s({ padding: '7px 8px', fontSize: 11, color: T.text2 })}>{a.summary}</td>
                  <td style={s({ padding: '7px 8px', ...mono, fontSize: 10, color: T.amber })}>{a.status}</td>
                  <td style={s({ padding: '7px 8px' })}><Btn small icon={ArrowUpRight}>Runbook</Btn></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Dream Monitor */}
        {/* STATE: GET /api/mc/dream-monitor/{id} */}
        <Card>
          <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 })}>
            <SectionTitle>Dream Monitor</SectionTitle>
            <Moon size={12} color={T.text3} />
          </div>
          <div style={s({ ...mono, fontSize: 10, color: T.text3, fontStyle: 'italic' })}>
            No dream events captured yet.
          </div>
        </Card>
      </div>

      {/* Wisdom Layer sidebar */}
      {/* STATE: GET /api/mc/wisdom-layer/{id} */}
      <div style={s({ width: 200, flexShrink: 0 })}>
        <Card>
          <SectionTitle>Wisdom Layer</SectionTitle>
          {[
            { label: 'Paradoxes (5m)', value: DEMO.wisdom.paradoxes_5m, icon: Sparkles },
            { label: 'Aesthetics (5m)', value: DEMO.wisdom.aesthetics_5m, icon: Star },
            { label: 'Seeds (5m)', value: DEMO.wisdom.seeds_5m, icon: Lightbulb },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 })}>
              <div style={s({ display: 'flex', alignItems: 'center', gap: 5 })}>
                <Icon size={10} color={T.text3} />
                <span style={s({ fontSize: 11, color: T.text2 })}>{label}</span>
              </div>
              <span style={s({ ...mono, fontSize: 11, color: value > 0 ? T.accentText : T.text3 })}>{value}</span>
            </div>
          ))}
          <div style={s({ borderTop: `1px solid ${T.border0}`, marginTop: 8, paddingTop: 8 })}>
            {['Last paradox', 'Last aesthetic', 'Last seed'].map(l => (
              <div key={l} style={s({ display: 'flex', justifyContent: 'space-between', marginBottom: 5 })}>
                <span style={s({ fontSize: 10, color: T.text3 })}>{l}</span>
                <span style={s({ ...mono, fontSize: 10, color: T.text4 })}>—</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

/** COST TAB */
// STATE: GET /api/mc/cost/{id}/summary
//        GET /api/mc/cost/{id}/providers?hours=24
//        GET /api/mc/cost/{id}/budget
//        GET /api/mc/cost/{id}/ollama-keepwarm
function CostTab() {
  const [budget, setBudget] = useState({ daily: '2.5', monthly: '20', enforcement: 'observe' })
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16, overflow: 'hidden auto' })}>
      {/* Summary cards */}
      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="24h Cost (USD)" value={`$${DEMO.cost.cost_24h.toFixed(4)}`} icon={DollarSign} />
        <MetricCard label="24h Tokens" value={DEMO.cost.tokens_24h.toLocaleString()} icon={Hash} />
        <MetricCard label="Unknown Pricing (24h)" value={DEMO.cost.unknown_24h} icon={AlertCircle} />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 })}>
        {/* Ollama Keepwarm */}
        {/* STATE: GET /api/mc/cost/{id}/ollama-keepwarm */}
        <Card>
          <SectionTitle>Ollama Keepwarm</SectionTitle>
          <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 })}>
            {[
              { k: 'Enabled', v: 'yes', color: T.green },
              { k: 'Running', v: 'no', color: T.text2 },
              { k: 'TTFT 1m', v: '0 ms' },
              { k: 'TTFT 15m', v: '0 ms' },
            ].map(({ k, v, color }) => (
              <div key={k} style={s({ padding: '8px', background: T.bgOverlay, borderRadius: 6 })}>
                <div style={s({ ...mono, fontSize: 8, color: T.text3, marginBottom: 3 })}>{k}</div>
                <div style={s({ ...mono, fontSize: 11, color: color || T.text1 })}>{v}</div>
              </div>
            ))}
          </div>
          <div style={s({ ...mono, fontSize: 9, color: T.text3 })}>Last blocked: disabled_or_unconfigured</div>
        </Card>

        {/* Budget Controls */}
        {/* STATE: GET /api/mc/cost/{id}/budget + PUT on save */}
        <Card>
          <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 })}>
            <SectionTitle>Budget Controls</SectionTitle>
            <Btn small variant="accent" icon={CheckCircle2}>Save</Btn>
          </div>
          <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 })}>
            {[
              { label: 'Daily USD', key: 'daily' },
              { label: 'Weekly USD', key: 'weekly' },
              { label: 'Monthly USD', key: 'monthly' },
            ].map(({ label, key }) => (
              <div key={key}>
                <div style={s({ ...mono, fontSize: 8, color: T.text3, marginBottom: 4 })}>{label}</div>
                <input
                  defaultValue={key === 'daily' ? '2.5' : key === 'monthly' ? '20' : ''}
                  style={s({
                    width: '100%', padding: '6px 8px',
                    background: T.bgOverlay, border: `1px solid ${T.border1}`,
                    borderRadius: 6, color: T.text1, fontSize: 12,
                    fontFamily: T.mono, outline: 'none',
                  })}
                />
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Provider cost table */}
      {/* STATE: GET /api/mc/cost/{id}/providers?hours=24 */}
      <Card>
        <SectionTitle>Top Providers (24h)</SectionTitle>
        <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
          <thead>
            <tr>
              {['Provider', 'Cost USD', 'Tokens', 'Calls'].map(h => (
                <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '4px 8px' })}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DEMO.providers_cost.map(p => (
              <tr key={p.provider}
                onMouseEnter={e => e.currentTarget.style.background = T.bgHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.accentText })}>{p.provider}</td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{p.cost_usd.toFixed(4)}</td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{p.tokens}</td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{p.calls}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

/** MEMORY TAB */
// STATE: GET /api/mc/memory/{id}?kind=all → table
//        GET /api/mc/memory/{id}/journal?date=today → journal
//        GET /api/mc/memory/{id}/item/{id} → modal on Open
function MemoryTab() {
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16, overflow: 'hidden auto' })}>
      {/* Filters */}
      <div style={s({ display: 'flex', gap: 8, alignItems: 'center' })}>
        <div style={s({ flex: 1, display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', background: T.bgRaised, border: `1px solid ${T.border1}`, borderRadius: 7 })}>
          <Search size={11} color={T.text3} />
          <input placeholder="Search memory..." style={s({ background: 'transparent', border: 'none', outline: 'none', color: T.text1, fontSize: 12, fontFamily: T.sans, flex: 1 })} />
        </div>
        <Btn icon={Filter}>all kinds</Btn>
        <label style={s({ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: T.text2, cursor: 'pointer' })}>
          <input type="checkbox" style={s({ accentColor: T.accent })} />
          include deleted
        </label>
      </div>

      {/* Memory items */}
      <Card>
        <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
          <thead>
            <tr>
              {['id', 'kind', 'title', 'flags', 'updated', 'actions'].map(h => (
                <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '4px 8px', letterSpacing: '0.08em' })}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DEMO.memory.map(m => (
              <tr key={m.id}
                onMouseEnter={e => e.currentTarget.style.background = T.bgHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={s({ padding: '8px', ...mono, fontSize: 9, color: T.text3 })}>{m.id.slice(0, 8)}...</td>
                <td style={s({ padding: '8px' })}><Chip color={T.blue}>{m.kind}</Chip></td>
                <td style={s({ padding: '8px', fontSize: 11, color: T.text1, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{m.title}</td>
                <td style={s({ padding: '8px' })}>
                  {m.flags.map(f => <Chip key={f} color={T.accent}>{f}</Chip>)}
                </td>
                <td style={s({ padding: '8px', ...mono, fontSize: 9, color: T.text3 })}>—</td>
                <td style={s({ padding: '8px' })}><Btn small>Open</Btn></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Memory journal */}
      {/* STATE: GET /api/mc/memory/{id}/journal?date=today */}
      <Card>
        <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 })}>
          <SectionTitle>Memory Journal</SectionTitle>
          <div style={s({ display: 'flex', gap: 6 })}>
            <input type="date" style={s({ ...mono, fontSize: 9, background: T.bgOverlay, border: `1px solid ${T.border1}`, borderRadius: 5, color: T.text2, padding: '3px 6px' })} />
            <Btn small icon={RefreshCw}>Rebuild</Btn>
          </div>
        </div>
        <div style={s({ ...mono, fontSize: 9, color: T.text3, marginBottom: 6 })}>Items: {DEMO.memory.length}</div>
        <pre style={s({
          ...mono, fontSize: 9.5, color: T.text2,
          background: T.bgBase, border: `1px solid ${T.border0}`,
          borderRadius: 7, padding: '12px 14px',
          overflow: 'auto', lineHeight: 1.7,
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        })}>
{`# Memory Journal (2026-03-03)

- Auto procedure: rank_initiatives [procedural] (2026-03-03T02:02:24Z)
  - When 'rank_initiatives' appears, reuse the validated sequence from prior successful runs.

- Skillforge draft: draft_auto-skill-kan-du-lave-et-lille-webbaseret-kryds-og-bolle-spil [procedural]
  - id: draft_auto-skill... title: Auto Skill: kan du lave et lille webbaseret kryds og bolle spil`}
        </pre>
      </Card>
    </div>
  )
}

/** SKILLS TAB */
// STATE: GET /api/mc/skills?workspace_id={id}&view=marketplace → table
//        POST /api/mc/skills/{name}/toggle → enable/disable
function SkillsTab() {
  const [skills, setSkills] = useState(DEMO.skills)
  const toggle = (name) => setSkills(prev => prev.map(s => s.name === name ? { ...s, enabled: !s.enabled } : s))
  const riskColor = { read_only: T.green, write_like: T.amber, destructive: T.red }

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden auto' })}>
      <div style={s({ display: 'flex', gap: 8 })}>
        {['Installed', 'Registry', 'Runs', 'Trust'].map(t => (
          <Btn key={t} variant={t === 'Installed' ? 'accent' : 'ghost'}>{t}</Btn>
        ))}
      </div>

      <Card>
        <SectionTitle>Discovery</SectionTitle>
        <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
          <thead>
            <tr>
              {['Name', 'Status', 'Risk', 'Approvals', 'Path', 'Action'].map(h => (
                <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '4px 8px' })}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {skills.map(sk => (
              <tr key={sk.name}
                onMouseEnter={e => e.currentTarget.style.background = T.bgHover}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={s({ padding: '7px 8px' })}>
                  <a style={s({ ...mono, fontSize: 10, color: T.accentText, textDecoration: 'none' })}>{sk.name}</a>
                </td>
                <td style={s({ padding: '7px 8px' })}><Chip color={sk.status === 'disabled' ? T.text3 : T.text2}>{sk.status}</Chip></td>
                <td style={s({ padding: '7px 8px' })}><Chip color={riskColor[sk.risk] || T.text3}>{sk.risk}</Chip></td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 10, color: T.text2 })}>{sk.approvals}</td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 9, color: T.text3 })}>skills/{sk.name}/SKILL.md</td>
                <td style={s({ padding: '7px 8px' })}>
                  <Btn
                    small
                    variant={sk.enabled ? 'accent' : 'ghost'}
                    onClick={() => toggle(sk.name)}
                  >
                    {sk.enabled ? 'enabled' : 'disabled'}
                  </Btn>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

/** LIVING MIND TAB */
// STATE: GET /api/mc/living-mind/{id}/status → feature statuses
//        GET /api/mc/living-mind/{id}/chronicle → entries
//        GET /api/mc/living-mind/{id}/self-model → domain confidence
//        GET /api/mc/living-mind/{id}/living-book → chapters
//        POST /api/mc/living-mind/nightly/run → trigger nightly
function LivingMindTab() {
  const features = [
    { label: 'Inner Voice', icon: Brain, status: 'active', last: '10m siden', provider: 'mistral' },
    { label: 'Dream Engine', icon: Moon, status: 'idle', last: 'aldrig', provider: 'openrouter' },
    { label: 'Chronicle', icon: BookOpen, status: 'active', last: '1m siden', provider: 'mistral' },
    { label: 'Self Model', icon: Fingerprint, status: 'active', last: 'live', provider: 'statistics' },
    { label: 'Living Book', icon: Sparkles, status: 'idle', last: 'aldrig', provider: 'gemini' },
    { label: 'Backbone', icon: Shield, status: 'active', last: '0 pushbacks', provider: 'nvidia_nim' },
    { label: 'Initiative Engine', icon: Zap, status: 'active', last: '15m siden', provider: 'cloudflare' },
    { label: 'Curriculum', icon: TrendingUp, status: 'idle', last: 'aldrig', provider: 'openrouter' },
  ]

  return (
    <div style={s({ display: 'flex', gap: 16, height: '100%', overflow: 'hidden' })}>
      <div style={s({ flex: 1, display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden auto' })}>

        {/* Feature status grid */}
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 })}>
          {features.map(({ label, icon: Icon, status, last, provider }) => (
            <div key={label} style={s({
              padding: '12px',
              background: T.bgRaised,
              border: `1px solid ${status === 'active' ? T.border1 : T.border0}`,
              borderLeft: `3px solid ${status === 'active' ? T.accent : T.text4}`,
              borderRadius: 8,
            })}>
              <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 })}>
                <Icon size={12} color={status === 'active' ? T.accentText : T.text3} />
                <span style={s({ fontSize: 11, fontWeight: 500, color: status === 'active' ? T.text1 : T.text2 })}>{label}</span>
              </div>
              <div style={s({ ...mono, fontSize: 9, color: T.text3 })}>{last}</div>
              <div style={s({ ...mono, fontSize: 8, color: T.text4, marginTop: 2 })}>{provider}</div>
            </div>
          ))}
        </div>

        {/* Chronicle */}
        {/* STATE: GET /api/mc/living-mind/{id}/chronicle */}
        <Card>
          <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 })}>
            <SectionTitle>Chronicle</SectionTitle>
            <Btn small icon={BookOpen}>All entries</Btn>
          </div>
          {DEMO.chronicle.map(entry => (
            <div key={entry.day_number} style={s({
              padding: '10px 12px',
              background: T.bgBase,
              border: `1px solid ${T.border0}`,
              borderLeft: `2px solid ${entry.is_milestone ? T.amber : T.text4}`,
              borderRadius: 7,
            })}>
              <div style={s({ display: 'flex', gap: 8, marginBottom: 4 })}>
                <span style={s({ ...mono, fontSize: 9, color: T.accentText })}>Dag {entry.day_number}</span>
                <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{entry.date}</span>
                {entry.is_milestone && <Chip color={T.amber}>milestone</Chip>}
              </div>
              <p style={s({ fontSize: 12, color: T.text2, lineHeight: 1.6, fontStyle: 'italic' })}>
                "{entry.entry}"
              </p>
            </div>
          ))}
        </Card>

        {/* Self model — domain confidence */}
        {/* STATE: GET /api/mc/living-mind/{id}/self-model */}
        <Card>
          <SectionTitle>Self Model — Domain Confidence</SectionTitle>
          {Object.entries(DEMO.self_model.confidence_by_domain).map(([domain, conf]) => (
            <div key={domain} style={s({ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 })}>
              <span style={s({ ...mono, fontSize: 10, color: T.text2, minWidth: 80 })}>{domain}</span>
              <div style={s({ flex: 1, height: 4, background: T.bgBase, borderRadius: 2 })}>
                <div style={s({ height: '100%', width: `${conf * 100}%`, background: conf > 0.7 ? T.green : conf > 0.4 ? T.amber : T.red, borderRadius: 2, transition: 'width 1s' })} />
              </div>
              <span style={s({ ...mono, fontSize: 9, color: T.text3, minWidth: 30 })}>{(conf * 100).toFixed(0)}%</span>
            </div>
          ))}
          <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 8 })}>
            strengths: {DEMO.self_model.known_strengths.length || 'ingen endnu'} ·
            weaknesses: {DEMO.self_model.known_weaknesses.length || 'ingen endnu'} ·
            blind spots: {DEMO.self_model.blind_spots.length || 'ingen endnu'}
          </div>
        </Card>
      </div>

      {/* Actions sidebar */}
      <div style={s({ width: 180, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 10 })}>
        <Card>
          <SectionTitle>Nightly Run</SectionTitle>
          {/* STATE: POST /api/mc/living-mind/nightly/run */}
          <Btn variant="accent" icon={Play}>Run now</Btn>
          <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 8 })}>
            Last run: aldrig
          </div>
        </Card>

        <Card>
          <SectionTitle>Feature Flags</SectionTitle>
          {[
            'inner_voice', 'dream_engine', 'chronicle',
            'self_model', 'backbone', 'initiative',
          ].map(flag => (
            <div key={flag} style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{flag}</span>
              <ToggleRight size={14} color={T.accent} style={{ cursor: 'pointer' }} />
            </div>
          ))}
        </Card>
      </div>
    </div>
  )
}

/** LAB TAB */
// STATE: GET /api/mc/lab/{id}/debug → intents, open_loops, habits, triggers
//        GET /api/mc/kernel/{id}/queue → queue status
//        POST /api/mc/lab/benchmark → run benchmark
function LabTab() {
  const d = DEMO.debug
  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden auto' })}>
      {/* Debug inspect */}
      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 })}>
        {[
          { label: 'Intents', values: [`Initiatives: ${d.intents}`, `Open loops: ${d.open_loops}`], icon: Network },
          { label: 'Suggestions', values: [`Suggestions: ${d.suggestions}`, `Habits: ${d.habits}`], icon: Lightbulb },
          { label: 'Autonomy Triggers', values: [`Total: ${d.autonomy_triggers}`, `Types: 1`], icon: Zap },
          { label: 'Embeddings', values: [`Enabled: ${d.embeddings_enabled}`, `Rows: 0`], icon: Database },
        ].map(({ label, values, icon: Icon }) => (
          <Card key={label}>
            <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 })}>
              <Icon size={11} color={T.text3} />
              <SectionTitle>{label}</SectionTitle>
            </div>
            {values.map(v => (
              <div key={v} style={s({ ...mono, fontSize: 10, color: T.text2, marginBottom: 4 })}>{v}</div>
            ))}
          </Card>
        ))}
      </div>

      {/* Kernel queue */}
      {/* STATE: GET /api/mc/kernel/{id}/queue */}
      <Card>
        <SectionTitle>Kernel Queue Controls</SectionTitle>
        <div style={s({ display: 'flex', gap: 8, marginBottom: 10 })}>
          <input defaultValue="proactive_suggestion" style={s({ flex: 1, ...mono, fontSize: 10, background: T.bgOverlay, border: `1px solid ${T.border1}`, borderRadius: 6, color: T.text1, padding: '5px 8px' })} />
          <input defaultValue="user_interactive" style={s({ flex: 1, ...mono, fontSize: 10, background: T.bgOverlay, border: `1px solid ${T.border1}`, borderRadius: 6, color: T.text1, padding: '5px 8px' })} />
          <input defaultValue="1" style={s({ width: 60, ...mono, fontSize: 10, background: T.bgOverlay, border: `1px solid ${T.border1}`, borderRadius: 6, color: T.text1, padding: '5px 8px' })} />
        </div>
        <pre style={s({ ...mono, fontSize: 9, color: T.text2, background: T.bgBase, border: `1px solid ${T.border0}`, borderRadius: 7, padding: '10px 12px', marginBottom: 10 })}>
{`{
  "event_type": "chat",
  "channel_type": "webchat"
}`}
        </pre>
        <div style={s({ display: 'flex', gap: 8, marginBottom: 12 })}>
          <Btn icon={Play}>Enqueue Command</Btn>
          <Btn icon={RefreshCw}>Process Queue</Btn>
          <Btn icon={Square}>Drain Queue</Btn>
        </div>
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 })}>
          {[
            { k: 'lane status', v: 'idle', color: T.green },
            { k: 'queue depth', v: '0' },
            { k: 'inflight', v: '—' },
            { k: 'blocked reason', v: '—' },
          ].map(({ k, v, color }) => (
            <div key={k} style={s({ padding: '8px', background: T.bgOverlay, borderRadius: 6 })}>
              <div style={s({ ...mono, fontSize: 8, color: T.text3, marginBottom: 3 })}>{k}</div>
              <div style={s({ ...mono, fontSize: 11, color: color || T.text1 })}>{v}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Model benchmark */}
      {/* STATE: POST /api/mc/lab/benchmark */}
      <Card>
        <SectionTitle>Model Benchmark (Estimate)</SectionTitle>
        <div style={s({ display: 'flex', gap: 8, alignItems: 'flex-end' })}>
          {[
            { label: 'Provider', defaultValue: 'ollama', flex: 1 },
            { label: 'Model', defaultValue: '', flex: 2 },
            { label: 'Runs', defaultValue: '3', flex: 1 },
            { label: 'Prompt chars', defaultValue: '512', flex: 1 },
          ].map(({ label, defaultValue, flex }) => (
            <div key={label} style={s({ flex })}>
              <div style={s({ ...mono, fontSize: 8, color: T.text3, marginBottom: 4 })}>{label}</div>
              <input defaultValue={defaultValue} style={s({ width: '100%', ...mono, fontSize: 10, background: T.bgOverlay, border: `1px solid ${T.border1}`, borderRadius: 6, color: T.text1, padding: '5px 8px' })} />
            </div>
          ))}
          <Btn icon={Play}>Run benchmark</Btn>
        </div>
      </Card>
    </div>
  )
}

/** HARDENING TAB */
// STATE: GET /api/mc/hardening/{id}/status → secrets, runtime, sandbox
//        POST /api/mc/hardening/{id}/preset → apply preset
//        GET /api/mc/hardening/{id}/doctor → findings
function HardeningTab() {
  const [activePreset, setActivePreset] = useState('private_super_agent')
  const presets = [
    { id: 'public_bot', label: 'Public Bot Safe', desc: 'Strict untrusted-scope guards, approvals, and sandbox routing.' },
    { id: 'internal_team', label: 'Internal Team', desc: 'Balanced defaults for trusted internal collaboration.' },
    { id: 'full_sandbox', label: 'Full Sandbox Lab', desc: 'Enable sandbox-first advanced tools for controlled lab usage.' },
    { id: 'private_super_agent', label: 'Private Super-Agent', desc: 'Max autonomy + private-mode L3 with sandbox-first routing.' },
  ]

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden auto' })}>
      {/* Presets */}
      <Card>
        <SectionTitle>Presets</SectionTitle>
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 })}>
          {presets.map(p => (
            <div
              key={p.id}
              onClick={() => setActivePreset(p.id)}
              style={s({
                padding: '12px',
                background: activePreset === p.id ? T.accentDim : T.bgOverlay,
                border: `1px solid ${activePreset === p.id ? T.accent : T.border1}`,
                borderRadius: 8, cursor: 'pointer',
                transition: 'all 0.15s',
              })}
            >
              <div style={s({ fontSize: 12, fontWeight: 500, color: activePreset === p.id ? T.accentText : T.text1, marginBottom: 4 })}>{p.label}</div>
              <div style={s({ fontSize: 10, color: T.text3, lineHeight: 1.4 })}>{p.desc}</div>
            </div>
          ))}
        </div>
        <Btn variant="accent" icon={CheckCircle2}>Apply preset</Btn>
      </Card>

      {/* Status panels */}
      <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 })}>
        {/* Secrets */}
        {/* STATE: GET /api/mc/hardening/{id}/status → secrets */}
        <Card>
          <SectionTitle>Secrets Status</SectionTitle>
          <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 })}>
            {[
              { k: 'Status', v: 'green', color: T.green },
              { k: 'Missing Keys', v: '0' },
              { k: 'Plaintext Findings', v: '0' },
              { k: 'Redaction', v: 'ok', color: T.green },
            ].map(({ k, v, color }) => (
              <div key={k} style={s({ padding: '8px', background: T.bgOverlay, borderRadius: 6 })}>
                <div style={s({ ...mono, fontSize: 8, color: T.text3, marginBottom: 3 })}>{k}</div>
                <div style={s({ ...mono, fontSize: 11, color: color || T.text1 })}>{v}</div>
              </div>
            ))}
          </div>
        </Card>

        {/* Runtime */}
        <Card>
          <SectionTitle>Runtime Status</SectionTitle>
          <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 })}>
            {[
              { k: 'Status', v: 'needs_attention', color: T.amber },
              { k: 'Findings', v: '3', color: T.amber },
              { k: 'High Severity', v: '0' },
              { k: 'Sandbox', v: 'enabled', color: T.green },
            ].map(({ k, v, color }) => (
              <div key={k} style={s({ padding: '8px', background: T.bgOverlay, borderRadius: 6 })}>
                <div style={s({ ...mono, fontSize: 8, color: T.text3, marginBottom: 3 })}>{k}</div>
                <div style={s({ ...mono, fontSize: 11, color: color || T.text1 })}>{v}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Sandbox connectivity */}
      <Card>
        <SectionTitle>Sandbox Connectivity</SectionTitle>
        <div style={s({ display: 'flex', gap: 8, alignItems: 'center' })}>
          <input defaultValue="https://example.com" style={s({ flex: 1, ...mono, fontSize: 10, background: T.bgOverlay, border: `1px solid ${T.border1}`, borderRadius: 6, color: T.text1, padding: '6px 10px' })} />
          <Btn variant="accent" icon={Wand2}>Auto-fix sandbox config</Btn>
          <Btn icon={CheckCircle2}>Run sandbox check</Btn>
        </div>
      </Card>

      {/* Doctor findings */}
      {/* STATE: GET /api/mc/hardening/{id}/doctor */}
      <Card>
        <SectionTitle>Doctor Findings</SectionTitle>
        <div style={s({ ...mono, fontSize: 10, color: T.text3, fontStyle: 'italic' })}>
          Run sandbox check to see findings.
        </div>
      </Card>
    </div>
  )
}

// ─── HEADER ───────────────────────────────────────────────────
// STATE: GET /api/mc/workspace/{id}/status → online, autonomy_level, exp_mode
function MCHeader({ status }) {
  return (
    <div style={s({
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 24px', height: 52,
      background: T.bgSurface,
      borderBottom: `1px solid ${T.border0}`,
      flexShrink: 0,
    })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 12 })}>
        <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
          <Command size={16} color={T.accentText} />
          <span style={s({ fontSize: 14, fontWeight: 600, letterSpacing: '0.04em' })}>Mission Control</span>
        </div>
        <Chip color={T.green}>Realtime: Connected</Chip>
        <span style={s({ fontSize: 11, color: T.text3 })}>Live control-plane operations.</span>
      </div>
      <div style={s({ display: 'flex', gap: 6 })}>
        <Chip color={T.accentText}>L{status.autonomy_level}</Chip>
        {status.exp_mode && <Chip color={T.amber}>EXP</Chip>}
        <Chip color={T.text3}>ollama</Chip>
      </div>
    </div>
  )
}

// Need to add Command icon import
import { Command } from 'lucide-react'

// ─── MAIN MISSION CONTROL ─────────────────────────────────────
export default function MissionControl() {
  const [activeTab, setActiveTab] = useState('overview')

  const tabContent = {
    overview:      <OverviewTab data={DEMO.overview} />,
    observability: <ObservabilityTab />,
    cost:          <CostTab />,
    memory:        <MemoryTab />,
    skills:        <SkillsTab />,
    living_mind:   <LivingMindTab />,
    hardening:     <HardeningTab />,
    lab:           <LabTab />,
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background: ${T.bgBase}; }
        ::-webkit-scrollbar { width: 3px; height: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${T.text4}; border-radius: 2px; }
        input, textarea, pre { font-family: 'IBM Plex Mono', monospace; }
      `}</style>

      <div style={s({ display: 'flex', flexDirection: 'column', height: '100vh', background: T.bgBase, fontFamily: T.sans, color: T.text1, overflow: 'hidden' })}>

        <MCHeader status={DEMO.status} />

        {/* Tab bar */}
        <div style={s({
          display: 'flex', alignItems: 'center',
          padding: '0 24px',
          background: T.bgSurface,
          borderBottom: `1px solid ${T.border0}`,
          flexShrink: 0,
          gap: 2,
        })}>
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = activeTab === id
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                style={s({
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '10px 12px',
                  background: 'transparent', border: 'none',
                  borderBottom: `2px solid ${active ? T.accent : 'transparent'}`,
                  color: active ? T.accentText : T.text3,
                  cursor: 'pointer', fontSize: 11, fontFamily: T.sans,
                  fontWeight: active ? 500 : 400,
                  transition: 'all 0.15s',
                })}
                onMouseEnter={e => !active && (e.currentTarget.style.color = T.text2)}
                onMouseLeave={e => !active && (e.currentTarget.style.color = T.text3)}
              >
                <Icon size={12} />
                {label}
              </button>
            )
          })}
        </div>

        {/* Tab content */}
        <div style={s({ flex: 1, overflow: 'hidden', padding: '20px 24px' })}>
          {tabContent[activeTab]}
        </div>
      </div>
    </>
  )
}
