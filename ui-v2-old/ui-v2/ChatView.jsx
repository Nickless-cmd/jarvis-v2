/**
 * ChatView.jsx — Jarvis AI Chat Interface
 * Stack: React + Lucide Icons + CSS Modules (inline styles)
 * Palette: Cool slate/grey, muted teal accent
 *
 * ═══════════════════════════════════════════════════════════════
 * STATE MAP — endpoints + SSE events
 * ═══════════════════════════════════════════════════════════════
 *
 * ON MOUNT:
 *   GET /api/mc/workspace/{workspaceId}/status
 *     → { online: bool, autonomy_level: 1|2|3, exp_mode: bool,
 *          uptime_seconds: int, llm_mode: string }
 *     Used by: <TopBar> status badge, autonomy indicator
 *
 *   GET /api/mc/sessions?workspace_id={id}&limit=20
 *     → [{ id, title, created_at, message_count, last_message }]
 *     Used by: <Sidebar> recent chats list
 *
 *   GET /api/mc/system/health
 *     → { cpu_pct, ram_pct, disk_mb, gpu_temps: [float] }
 *     Used by: <Sidebar> system stats (poll every 10s)
 *
 *   GET /api/mc/emotional-state/{workspaceId}
 *     → { confidence: float, curiosity: float,
 *          frustration: float, fatigue: float }
 *     Used by: <RightPanel> emotional state bars
 *
 *   GET /api/mc/skills?workspace_id={id}&status=active
 *     → [{ name, uses: int, risk: string, status: string }]
 *     Used by: <RightPanel> skill list + <ComposerBar> pills
 *
 *   GET /api/mc/memory/{workspaceId}/summary
 *     → { procedures: int, habits: int, open_loops: int,
 *          dreams: int, chronicle_days: int }
 *     Used by: <RightPanel> memory summary
 *
 *   GET /api/mc/providers/status
 *     → [{ name, status, tokens_24h, calls_24h, cost_usd }]
 *     Used by: <TopBar> active provider chip
 *
 * ON SESSION OPEN:
 *   GET /api/chat/sessions/{sessionId}/messages?limit=50
 *     → [{ id, role: 'user'|'assistant', content, ts,
 *          tool_calls: [{ skill, args, result, status }] }]
 *     Used by: <MessageList> renders full history
 *
 * ON SEND MESSAGE:
 *   POST /api/chat/message
 *     body: { workspace_id, session_id, content }
 *     → { run_id, message_id }
 *     Used by: <ComposerBar> send handler
 *
 * SSE STREAM (mounted on session open):
 *   SSE /api/chat/stream/{workspaceId}
 *
 *   event: "agent_working"
 *     data: { action: string, detail: string, step: int }
 *     Used by: <WorkingIndicator> live step display
 *
 *   event: "tool_call"
 *     data: { skill: string, args: obj, status: 'running'|'done'|'error' }
 *     Used by: <ToolCallBubble> inline tool display
 *
 *   event: "message_chunk"
 *     data: { delta: string, run_id: string }
 *     Used by: <MessageList> streaming append to last message
 *
 *   event: "run_done"
 *     data: { run_id, outcome: string, tokens: int, provider: string }
 *     Used by: clears WorkingIndicator, updates token meter
 *
 *   event: "emotional_update"
 *     data: { confidence, curiosity, frustration, fatigue }
 *     Used by: <RightPanel> real-time emotional state update
 *
 *   event: "inner_voice_thought"
 *     data: { preview: string, triggered_initiative: bool }
 *     Used by: <InnerVoiceToast> subtle bottom-left notification
 *
 *   event: "initiative_proposed"
 *     data: { text: string, score: float }
 *     Used by: <InitiativeBar> above composer when score > 0.55
 *
 *   event: "dream_hypothesis"
 *     data: { preview: string, confidence: float }
 *     Used by: <SessionStartBanner> shown at session start if pending
 *
 * PERIODIC (every 10s):
 *   GET /api/mc/system/health → update sidebar cpu/ram/disk
 *   GET /api/mc/providers/tokens-per-min → update <TopBar> token meter
 * ═══════════════════════════════════════════════════════════════
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Bot, User, Send, Square, Mic, Paperclip,
  Search, Settings, ChevronRight, Circle,
  Cpu, HardDrive, Activity, Zap, Brain,
  MessageSquare, Layers, MemoryStick, Command,
  MoreHorizontal, Plus, Hash, Clock, Loader2,
  CheckCircle2, AlertCircle, Terminal, Eye,
  Smile, Frown, Lightbulb, Battery, Sparkles,
  ArrowUpRight, X
} from 'lucide-react'

// ─── DESIGN TOKENS ────────────────────────────────────────────
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
  mono:       "'IBM Plex Mono', monospace",
  sans:       "'DM Sans', sans-serif",
}

// ─── DEMO STATE (replace with real API calls) ──────────────────
const DEMO = {
  status: { online: true, autonomy_level: 3, exp_mode: true, uptime_seconds: 210, llm_mode: 'groq' },
  health: { cpu_pct: 28, ram_pct: 34, disk_mb: 399 },
  emotional: { confidence: 0.71, curiosity: 0.84, frustration: 0.12, fatigue: 0.06 },
  skills: [
    { name: 'agent_self', uses: 2, status: 'active' },
    { name: 'docker_ops', uses: 1, status: 'active' },
    { name: 'google_search', uses: 0, status: 'idle' },
    { name: 'home_assistant', uses: 0, status: 'idle' },
    { name: 'browser_screenshot', uses: 0, status: 'idle' },
  ],
  memory: { procedures: 2, habits: 41, open_loops: 41, dreams: 0, chronicle_days: 1 },
  sessions: [
    { id: '1', title: 'Kryds og bolle spil', message_count: 4, last_message: '2m siden' },
    { id: '2', title: 'Workspace scan', message_count: 6, last_message: '18m siden' },
    { id: '3', title: 'Plan review', message_count: 12, last_message: '1t siden' },
  ],
  messages: [
    {
      id: 'm1', role: 'assistant',
      content: 'Hej. Jeg er online og klar. Jeg har scannet dit workspace og fundet 47 filer og 3 aktive projekter.\n\nHvad vil du have mig til at gøre?',
      ts: '12:19', tool_calls: []
    },
    {
      id: 'm2', role: 'user',
      content: 'scan workspace og vis mig strukturen',
      ts: '12:21', tool_calls: []
    },
  ],
  workingSteps: [
    { action: 'scanning', detail: 'workspace mappestruktur', icon: Search },
    { action: 'reading', detail: '47 Python filer fundet', icon: Eye },
    { action: 'executing', detail: 'find . -name "*.py"', icon: Terminal },
    { action: 'analyzing', detail: 'identificerer moduler', icon: Brain },
    { action: 'writing', detail: 'formulerer svar...', icon: Sparkles },
  ],
}

// ─── HELPERS ──────────────────────────────────────────────────
const s = (styles) => styles  // passthrough for inline style objects
const mono = { fontFamily: T.mono }
const fmt = (n) => (n * 100).toFixed(0) + '%'

// ─── SUB COMPONENTS ───────────────────────────────────────────

/** Sidebar — recent sessions + system stats */
function Sidebar({ sessions, health, onNewChat, onSelectSession, activeSession }) {
  return (
    <aside style={s({
      width: 208, minWidth: 208,
      background: T.bgSurface,
      borderRight: `1px solid ${T.border0}`,
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    })}>
      {/* Logo */}
      <div style={s({ padding: '18px 16px 14px', borderBottom: `1px solid ${T.border0}` })}>
        <div style={s({ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 })}>
          <div style={s({
            width: 26, height: 26,
            background: T.accent,
            borderRadius: 7,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: `0 0 14px ${T.accentGlow}`,
          })}>
            <Bot size={14} color="white" strokeWidth={2} />
          </div>
          <span style={s({ fontSize: 13, fontWeight: 600, letterSpacing: '0.06em', color: T.text1 })}>
            JARVIS
          </span>
          {/* STATE: status.online → green/red dot */}
          <div style={s({
            marginLeft: 'auto', width: 6, height: 6,
            borderRadius: '50%', background: T.green,
            boxShadow: `0 0 6px ${T.green}`,
            animation: 'breathe 2.5s ease-in-out infinite',
          })} />
        </div>

        {/* New chat button */}
        <button
          onClick={onNewChat}
          style={s({
            width: '100%', padding: '7px 10px',
            background: T.accentDim,
            border: `1px solid ${T.border1}`,
            borderRadius: 8, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
            color: T.accentText, fontSize: 11,
            fontFamily: T.sans, fontWeight: 500,
            transition: 'all 0.15s',
          })}
          onMouseEnter={e => e.currentTarget.style.background = T.accentMid}
          onMouseLeave={e => e.currentTarget.style.background = T.accentDim}
        >
          <Plus size={12} />
          Ny chat
        </button>
      </div>

      {/* Navigation */}
      <div style={s({ padding: '10px 8px', borderBottom: `1px solid ${T.border0}` })}>
        {[
          { icon: MessageSquare, label: 'Chat', active: true },
          { icon: Brain, label: 'Memory' },
          { icon: Layers, label: 'Skills' },
          { icon: Command, label: 'Mission Control' },
        ].map(({ icon: Icon, label, active }) => (
          <div
            key={label}
            style={s({
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '7px 8px', borderRadius: 6,
              background: active ? T.accentDim : 'transparent',
              borderLeft: active ? `2px solid ${T.accent}` : '2px solid transparent',
              color: active ? T.accentText : T.text2,
              cursor: 'pointer', marginBottom: 1,
              fontSize: 12, fontWeight: active ? 500 : 400,
              transition: 'all 0.15s',
            })}
            onMouseEnter={e => !active && (e.currentTarget.style.background = T.bgHover)}
            onMouseLeave={e => !active && (e.currentTarget.style.background = 'transparent')}
          >
            <Icon size={13} />
            {label}
          </div>
        ))}
      </div>

      {/* Recent sessions */}
      {/* STATE: GET /api/mc/sessions → sessions list */}
      <div style={s({ flex: 1, overflow: 'hidden auto', padding: '10px 8px' })}>
        <div style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.12em', padding: '0 8px 6px', textTransform: 'uppercase' })}>
          Seneste
        </div>
        {sessions.map(sess => (
          <div
            key={sess.id}
            onClick={() => onSelectSession(sess.id)}
            style={s({
              padding: '7px 8px', borderRadius: 6,
              cursor: 'pointer', marginBottom: 1,
              background: activeSession === sess.id ? T.bgOverlay : 'transparent',
              transition: 'all 0.15s',
            })}
            onMouseEnter={e => e.currentTarget.style.background = T.bgHover}
            onMouseLeave={e => e.currentTarget.style.background = activeSession === sess.id ? T.bgOverlay : 'transparent'}
          >
            <div style={s({ fontSize: 11, color: T.text1, marginBottom: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' })}>
              {sess.title}
            </div>
            <div style={s({ ...mono, fontSize: 9, color: T.text3 })}>
              {sess.last_message}
            </div>
          </div>
        ))}
      </div>

      {/* System stats */}
      {/* STATE: GET /api/mc/system/health (poll 10s) → cpu_pct, ram_pct, disk_mb */}
      <div style={s({ padding: '12px 16px', borderTop: `1px solid ${T.border0}` })}>
        {[
          { label: 'CPU', value: health.cpu_pct, max: 100, unit: '%' },
          { label: 'RAM', value: health.ram_pct, max: 100, unit: '%' },
        ].map(({ label, value, max, unit }) => (
          <div key={label} style={s({ marginBottom: 8 })}>
            <div style={s({ display: 'flex', justifyContent: 'space-between', marginBottom: 3 })}>
              <span style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.1em' })}>{label}</span>
              <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{value}{unit}</span>
            </div>
            <div style={s({ height: 2, background: T.bgOverlay, borderRadius: 1 })}>
              <div style={s({ height: '100%', width: `${(value / max) * 100}%`, background: T.accent, borderRadius: 1, transition: 'width 1s' })} />
            </div>
          </div>
        ))}
        <div style={s({ display: 'flex', justifyContent: 'space-between', marginTop: 4 })}>
          <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>DISK</span>
          <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{health.disk_mb} MB</span>
        </div>
      </div>
    </aside>
  )
}

/** TopBar — workspace info, provider, token meter */
// STATE: GET /api/mc/workspace/{id}/status → online, autonomy_level, exp_mode
// STATE: GET /api/mc/providers/status → active provider name
// STATE: SSE run_done → token rate (poll /api/mc/providers/tokens-per-min every 10s)
function TopBar({ status, tokenRate, provider, isWorking }) {
  const autonomyColors = { 1: T.amber, 2: T.blue, 3: T.accent }
  return (
    <div style={s({
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 20px',
      height: 48,
      background: T.bgSurface,
      borderBottom: `1px solid ${T.border0}`,
      flexShrink: 0,
    })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <span style={s({ fontSize: 12, fontWeight: 500, color: T.text1 })}>Ny chat</span>
        <div style={s({ display: 'flex', gap: 4 })}>
          {/* autonomy level badge */}
          <Chip color={autonomyColors[status.autonomy_level]}>
            L{status.autonomy_level}
          </Chip>
          {status.exp_mode && <Chip color={T.amber}>EXP</Chip>}
          <Chip color={T.text3}>{provider}</Chip>
        </div>
      </div>

      <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
        {/* Token meter — STATE: poll /api/mc/providers/tokens-per-min */}
        <div style={s({
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '4px 10px',
          background: isWorking ? T.accentDim : T.bgRaised,
          border: `1px solid ${isWorking ? T.accent : T.border1}`,
          borderRadius: 20,
          transition: 'all 0.3s',
        })}>
          <Activity size={9} color={isWorking ? T.accentText : T.text3} />
          <span style={s({ ...mono, fontSize: 9, color: isWorking ? T.accentText : T.text3 })}>
            {tokenRate} tok/min
          </span>
        </div>

        <IconBtn icon={Search} />
        <IconBtn icon={Settings} />
      </div>
    </div>
  )
}

/** WorkingIndicator — shows during agent runs */
// STATE: SSE "agent_working" → { action, detail }
//        SSE "tool_call" → { skill, status }
//        SSE "run_done" → clears indicator
function WorkingIndicator({ step, doneSteps }) {
  if (!step) return null
  const Icon = step.icon || Loader2
  return (
    <div style={s({
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '9px 14px',
      background: T.bgRaised,
      border: `1px solid ${T.border1}`,
      borderLeft: `2px solid ${T.accent}`,
      borderRadius: 10,
      maxWidth: 380,
      marginLeft: 36,
      animation: 'slideUp 0.2s ease both',
    })}>
      {/* Spinner */}
      <div style={s({ marginTop: 1, animation: 'spin 1s linear infinite', color: T.accentText })}>
        <Loader2 size={13} />
      </div>

      <div style={s({ flex: 1 })}>
        {/* Completed steps */}
        {doneSteps.map((ds, i) => (
          <div key={i} style={s({ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 2 })}>
            <CheckCircle2 size={9} color={T.green} />
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{ds.action}</span>
          </div>
        ))}
        {/* Current step */}
        <div style={s({ display: 'flex', alignItems: 'center', gap: 6 })}>
          <Icon size={11} color={T.accentText} />
          <span style={s({ ...mono, fontSize: 10, color: T.accentText })}>{step.action}</span>
        </div>
        <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 2 })}>{step.detail}</div>
      </div>
    </div>
  )
}

/** Single message bubble */
// STATE: GET /api/chat/sessions/{id}/messages → messages[]
//        SSE "message_chunk" → streaming append
function MessageBubble({ msg, isStreaming }) {
  const isUser = msg.role === 'user'
  return (
    <div style={s({
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 10,
      animation: 'msgIn 0.25s cubic-bezier(0.16,1,0.3,1) both',
    })}>
      {/* Avatar */}
      <div style={s({
        width: 26, height: 26, borderRadius: 8,
        flexShrink: 0, marginTop: 2,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: isUser ? T.bgOverlay : T.accent,
        border: `1px solid ${isUser ? T.border1 : 'transparent'}`,
        boxShadow: isUser ? 'none' : `0 0 10px ${T.accentGlow}`,
      })}>
        {isUser
          ? <User size={12} color={T.text2} />
          : <Bot size={12} color="white" strokeWidth={2} />
        }
      </div>

      {/* Content */}
      <div style={s({ maxWidth: '70%', display: 'flex', flexDirection: 'column', gap: 3, alignItems: isUser ? 'flex-end' : 'flex-start' })}>
        <div style={s({ ...mono, fontSize: 9, color: T.text3, padding: '0 4px', letterSpacing: '0.08em' })}>
          {isUser ? 'BJØRN' : 'JARVIS'} · {msg.ts}
        </div>

        {/* Tool calls inline */}
        {msg.tool_calls?.map((tc, i) => (
          <div key={i} style={s({
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '5px 10px',
            background: T.bgOverlay,
            border: `1px solid ${T.border1}`,
            borderRadius: 6,
            marginBottom: 4,
          })}>
            <Terminal size={10} color={T.text3} />
            <span style={s({ ...mono, fontSize: 9, color: T.text2 })}>{tc.skill}</span>
            <CheckCircle2 size={9} color={T.green} />
          </div>
        ))}

        {/* Bubble */}
        <div style={s({
          padding: '10px 14px',
          background: isUser ? T.accentDim : T.bgRaised,
          border: `1px solid ${isUser ? T.accentMid : T.border1}`,
          borderRadius: isUser
            ? `${T.r_lg} ${T.r_sm} ${T.r_lg} ${T.r_lg}`
            : `${T.r_sm} ${T.r_lg} ${T.r_lg} ${T.r_lg}`,
          fontSize: 13,
          lineHeight: 1.65,
          color: T.text1,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        })}>
          {msg.content}
          {isStreaming && (
            <span style={s({
              display: 'inline-block', width: 2, height: 13,
              background: T.accentText, marginLeft: 3,
              verticalAlign: 'middle',
              animation: 'blink 1s step-end infinite',
            })} />
          )}
        </div>
      </div>
    </div>
  )
}

/** InitiativeBanner — shows when Jarvis has a proactive suggestion */
// STATE: SSE "initiative_proposed" → { text, score }
//        score >= 0.55 = show, score >= 0.80 = auto-acted
function InitiativeBanner({ initiative, onAccept, onDismiss }) {
  if (!initiative) return null
  return (
    <div style={s({
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 14px',
      background: T.bgOverlay,
      border: `1px solid ${T.border1}`,
      borderTop: `1px solid ${T.border0}`,
    })}>
      <Lightbulb size={13} color={T.amber} />
      <span style={s({ flex: 1, fontSize: 12, color: T.text2 })}>{initiative.text}</span>
      <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>score {initiative.score.toFixed(2)}</span>
      <button onClick={onAccept} style={s({ ...mono, fontSize: 9, padding: '3px 8px', background: T.accentDim, border: `1px solid ${T.accent}`, borderRadius: 4, color: T.accentText, cursor: 'pointer' })}>
        Gør det
      </button>
      <button onClick={onDismiss} style={s({ background: 'none', border: 'none', cursor: 'pointer', color: T.text3 })}>
        <X size={12} />
      </button>
    </div>
  )
}

/** Composer bar */
// STATE: POST /api/chat/message → triggers run
//        SSE "run_done" → re-enable send
function ComposerBar({ onSend, isWorking, onStop, skills }) {
  const [value, setValue] = useState('')
  const [focused, setFocused] = useState(false)
  const ref = useRef()

  const handleSend = () => {
    if (!value.trim() || isWorking) return
    onSend(value.trim())
    setValue('')
    ref.current.style.height = 'auto'
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const activeSkills = skills.filter(s => s.status === 'active').slice(0, 3)

  const borderColor = isWorking
    ? T.accent
    : focused
    ? T.border2
    : T.border1

  return (
    <div style={s({ padding: '12px 20px 16px', flexShrink: 0 })}>
      {/* Outer border glow */}
      <div style={s({
        borderRadius: 14,
        padding: '1.5px',
        background: isWorking
          ? `linear-gradient(135deg, ${T.accent}, #2a6e5e)`
          : borderColor,
        transition: 'all 0.25s',
        boxShadow: isWorking ? `0 0 18px ${T.accentGlow}` : 'none',
      })}>
        <div style={s({
          background: T.bgSurface,
          borderRadius: 'calc(14px - 1.5px)',
          padding: '10px 12px',
          display: 'flex', alignItems: 'flex-end', gap: 8,
        })}>
          {/* Textarea */}
          <textarea
            ref={ref}
            value={value}
            onChange={e => {
              setValue(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
            onKeyDown={handleKey}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={isWorking ? 'Jarvis arbejder...' : 'Spørg Jarvis om hvad som helst...'}
            rows={1}
            style={s({
              flex: 1, background: 'transparent',
              border: 'none', outline: 'none',
              color: T.text1, fontSize: 13, lineHeight: 1.5,
              fontFamily: T.sans, resize: 'none',
              minHeight: 22, maxHeight: 120,
            })}
          />

          {/* Actions */}
          <div style={s({ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 })}>
            <IconBtn icon={Paperclip} size={13} />
            <IconBtn icon={Mic} size={13} />
            {isWorking
              ? (
                <button onClick={onStop} style={s({
                  width: 32, height: 32, borderRadius: 10,
                  background: T.red, border: 'none',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', boxShadow: `0 0 12px rgba(192,80,80,0.4)`,
                  animation: 'stopPulse 1.5s ease-in-out infinite',
                })}>
                  <Square size={12} color="white" fill="white" />
                </button>
              )
              : (
                <button onClick={handleSend} disabled={!value.trim()} style={s({
                  width: 32, height: 32, borderRadius: 10,
                  background: value.trim() ? T.accent : T.bgOverlay,
                  border: 'none',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: value.trim() ? 'pointer' : 'default',
                  boxShadow: value.trim() ? `0 0 12px ${T.accentGlow}` : 'none',
                  transition: 'all 0.2s',
                })}>
                  <Send size={13} color={value.trim() ? 'white' : T.text3} />
                </button>
              )
            }
          </div>
        </div>
      </div>

      {/* Meta row */}
      <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 2px 0' })}>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
          <span style={s({ color: T.text2 })}>Enter</span> send ·{' '}
          <span style={s({ color: T.text2 })}>Shift+Enter</span> ny linje
        </span>
        <div style={s({ display: 'flex', gap: 4 })}>
          {activeSkills.map(sk => (
            <div key={sk.name} style={s({
              ...mono, fontSize: 8,
              padding: '2px 7px', borderRadius: 10,
              background: T.bgRaised, border: `1px solid ${T.border1}`,
              color: T.text3, cursor: 'pointer',
              transition: 'all 0.15s',
            })}>
              {sk.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/** Right panel — emotional state, skills, memory */
function RightPanel({ emotional, skills, memory }) {
  return (
    <aside style={s({
      width: 224, minWidth: 224,
      background: T.bgSurface,
      borderLeft: `1px solid ${T.border0}`,
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden auto',
    })}>

      {/* Emotional state */}
      {/* STATE: GET /api/mc/emotional-state/{workspaceId}
                SSE "emotional_update" → live update */}
      <PanelSection title="Emotional State">
        <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 })}>
          {[
            { label: 'CONF', value: emotional.confidence, color: T.green, icon: Smile },
            { label: 'CURIO', value: emotional.curiosity, color: T.amber, icon: Lightbulb },
            { label: 'FRUS', value: emotional.frustration, color: T.red, icon: Frown },
            { label: 'FATIGUE', value: emotional.fatigue, color: T.blue, icon: Battery },
          ].map(({ label, value, color, icon: Icon }) => (
            <div key={label} style={s({
              padding: '8px', background: T.bgRaised,
              border: `1px solid ${T.border0}`,
              borderRadius: 8,
            })}>
              <div style={s({ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 })}>
                <Icon size={9} color={color} />
                <span style={s({ ...mono, fontSize: 8, color: T.text3, letterSpacing: '0.08em' })}>{label}</span>
              </div>
              <div style={s({ ...mono, fontSize: 14, color: T.text1, marginBottom: 4 })}>
                {value.toFixed(2)}
              </div>
              <div style={s({ height: 2, background: T.bgBase, borderRadius: 1 })}>
                <div style={s({ height: '100%', width: `${value * 100}%`, background: color, borderRadius: 1, transition: 'width 0.8s' })} />
              </div>
            </div>
          ))}
        </div>
      </PanelSection>

      {/* Active skills */}
      {/* STATE: GET /api/mc/skills?workspace_id={id}&status=active
                SSE "tool_call" → increment uses */}
      <PanelSection title="Skills">
        {skills.map(sk => (
          <div key={sk.name} style={s({
            display: 'flex', alignItems: 'center',
            padding: '5px 6px', borderRadius: 5,
            cursor: 'pointer', marginBottom: 1,
            transition: 'background 0.15s',
          })}
            onMouseEnter={e => e.currentTarget.style.background = T.bgHover}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <div style={s({
              width: 5, height: 5, borderRadius: '50%',
              background: sk.status === 'active' ? T.green : T.text4,
              boxShadow: sk.status === 'active' ? `0 0 5px ${T.green}` : 'none',
              marginRight: 7, flexShrink: 0,
            })} />
            <span style={s({ ...mono, fontSize: 10, color: T.text2, flex: 1 })}>{sk.name}</span>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{sk.uses}</span>
          </div>
        ))}
      </PanelSection>

      {/* Memory summary */}
      {/* STATE: GET /api/mc/memory/{workspaceId}/summary */}
      <PanelSection title="Memory">
        {[
          { label: 'Procedures', value: memory.procedures, color: T.accentText },
          { label: 'Open loops', value: memory.open_loops, color: T.amber },
          { label: 'Habits', value: memory.habits, color: T.text1 },
          { label: 'Dreams', value: memory.dreams, color: T.text3 },
          { label: 'Chronicle', value: `dag ${memory.chronicle_days}`, color: T.text3 },
        ].map(({ label, value, color }) => (
          <div key={label} style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 })}>
            <span style={s({ fontSize: 11, color: T.text2 })}>{label}</span>
            <span style={s({ ...mono, fontSize: 10, color })}>{value}</span>
          </div>
        ))}
      </PanelSection>

      {/* Inner voice */}
      {/* STATE: SSE "inner_voice_thought" → preview */}
      <PanelSection title="Inner Voice">
        <div style={s({
          padding: '8px 10px',
          background: T.bgRaised,
          border: `1px solid ${T.border0}`,
          borderRadius: 7,
          borderLeft: `2px solid ${T.text4}`,
        })}>
          <span style={s({ fontSize: 11, color: T.text3, fontStyle: 'italic', lineHeight: 1.5 })}>
            ingen tanker endnu — Jarvis er kun lige startet...
          </span>
        </div>
      </PanelSection>
    </aside>
  )
}

// ─── SMALL SHARED COMPONENTS ──────────────────────────────────

function PanelSection({ title, children }) {
  return (
    <div style={s({ padding: '14px 14px', borderBottom: `1px solid ${T.border0}` })}>
      <div style={s({ ...mono, fontSize: 9, color: T.text3, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 10 })}>
        {title}
      </div>
      {children}
    </div>
  )
}

function Chip({ children, color }) {
  return (
    <div style={s({
      ...mono, fontSize: 8,
      padding: '2px 7px', borderRadius: 10,
      background: `${color}18`,
      border: `1px solid ${color}35`,
      color: color, letterSpacing: '0.08em',
    })}>
      {children}
    </div>
  )
}

function IconBtn({ icon: Icon, size = 14, onClick }) {
  return (
    <button onClick={onClick} style={s({
      width: 28, height: 28, borderRadius: 7,
      background: 'transparent',
      border: `1px solid ${T.border1}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      cursor: 'pointer', color: T.text2,
      transition: 'all 0.15s',
    })}
      onMouseEnter={e => {
        e.currentTarget.style.background = T.bgHover
        e.currentTarget.style.color = T.text1
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'transparent'
        e.currentTarget.style.color = T.text2
      }}
    >
      <Icon size={size} />
    </button>
  )
}

// ─── MAIN COMPONENT ───────────────────────────────────────────
export default function ChatView() {
  const [messages, setMessages]         = useState(DEMO.messages)
  const [isWorking, setIsWorking]       = useState(true)
  const [workStep, setWorkStep]         = useState(DEMO.workingSteps[0])
  const [doneSteps, setDoneSteps]       = useState([])
  const [tokenRate, setTokenRate]       = useState(67)
  const [initiative, setInitiative]     = useState({ text: 'Jeg har 41 åbne loops — vil du at jeg prioriterer dem?', score: 0.61 })
  const [emotional, setEmotional]       = useState(DEMO.emotional)
  const [activeSession, setActiveSession] = useState('1')
  const messagesEndRef = useRef()

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isWorking])

  // Demo: cycle working steps then stream response
  useEffect(() => {
    let stepIdx = 0
    const interval = setInterval(() => {
      stepIdx++
      if (stepIdx < DEMO.workingSteps.length) {
        setDoneSteps(prev => [...prev, DEMO.workingSteps[stepIdx - 1]])
        setWorkStep(DEMO.workingSteps[stepIdx])
      } else {
        clearInterval(interval)
        setIsWorking(false)
        setWorkStep(null)
        setDoneSteps([])

        // Stream response
        const full = 'Her er hvad jeg fandt:\n\nworkspace/\n├── agent/          # 47 filer\n│   ├── cognition/   # inner voice, self model\n│   ├── orchestration/\n│   └── jobs/        # initiative, curriculum\n├── skills/          # 41 skills\n└── tests/           # 89 tests · grønne\n\nVil du at jeg dykker ned i et specifikt modul?'
        const streamMsg = { id: 'm3', role: 'assistant', content: '', ts: '12:21', tool_calls: [{ skill: 'agent_self', status: 'done' }] }
        setMessages(prev => [...prev, streamMsg])

        let i = 0
        const stream = setInterval(() => {
          i += 3
          setMessages(prev => prev.map(m => m.id === 'm3' ? { ...m, content: full.slice(0, i) } : m))
          if (i >= full.length) clearInterval(stream)
        }, 20)
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [])

  // Token rate jitter
  useEffect(() => {
    const iv = setInterval(() => setTokenRate(67 + Math.floor(Math.random() * 20) - 10), 3000)
    return () => clearInterval(iv)
  }, [])

  const handleSend = useCallback((text) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content: text, ts: new Date().toLocaleTimeString('da', { hour: '2-digit', minute: '2-digit' }), tool_calls: [] }])
  }, [])

  const streamingId = isWorking ? null : messages[messages.length - 1]?.id

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background: ${T.bgBase}; }
        @keyframes breathe { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.5);opacity:0.6} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes slideUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        @keyframes msgIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes stopPulse { 0%,100%{box-shadow:0 0 12px rgba(192,80,80,0.4)} 50%{box-shadow:0 0 22px rgba(192,80,80,0.7)} }
        ::-webkit-scrollbar { width: 3px; height: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${T.text4}; border-radius: 2px; }
        textarea { font-family: 'DM Sans', sans-serif; }
      `}</style>

      <div style={s({ display:'flex', height:'100vh', background: T.bgBase, fontFamily: T.sans, color: T.text1, overflow:'hidden' })}>

        {/* Sidebar */}
        <Sidebar
          sessions={DEMO.sessions}
          health={DEMO.health}
          onNewChat={() => {}}
          onSelectSession={setActiveSession}
          activeSession={activeSession}
        />

        {/* Main */}
        <div style={s({ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' })}>
          <TopBar
            status={DEMO.status}
            tokenRate={tokenRate}
            provider="groq · llama-3.3-70b"
            isWorking={isWorking}
          />

          {/* Messages */}
          <div style={s({
            flex:1, overflow:'hidden auto',
            padding: '28px 24px',
            display:'flex', flexDirection:'column', gap:20,
          })}>
            {messages.map((msg, i) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                isStreaming={!isWorking && i === messages.length - 1 && msg.role === 'assistant' && msg.content.length < 200}
              />
            ))}

            {/* Working indicator */}
            {isWorking && (
              <WorkingIndicator step={workStep} doneSteps={doneSteps} />
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Initiative banner */}
          <InitiativeBanner
            initiative={initiative}
            onAccept={() => setInitiative(null)}
            onDismiss={() => setInitiative(null)}
          />

          {/* Composer */}
          <ComposerBar
            onSend={handleSend}
            isWorking={isWorking}
            onStop={() => setIsWorking(false)}
            skills={DEMO.skills}
          />
        </div>

        {/* Right panel */}
        <RightPanel
          emotional={emotional}
          skills={DEMO.skills}
          memory={DEMO.memory}
        />
      </div>
    </>
  )
}
