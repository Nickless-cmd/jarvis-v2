import { useCallback, useEffect, useState } from 'react'
import {
  ListChecks,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
} from 'lucide-react'

interface PlanProposal {
  plan_id: string
  session_id?: string
  title: string
  why?: string
  steps: string[]
  status: string
  proposed_at?: string
  resolved_at?: string
}

interface Props {
  apiBaseUrl: string
  sessionId: string | null
  isOwner: boolean
}

/**
 * Pending plan proposals — Claude-Code's plan-mode made interactive.
 *
 * When Jarvis is in plan-mode he calls propose_plan instead of executing,
 * and the proposal sits in plan_proposals as awaiting_approval. v1 of
 * JarvisX showed nothing for this — the user had to either look in the
 * prompt where "pending plans" was injected, or type approval into chat.
 *
 * This strip surfaces them properly: each pending plan renders as an
 * expandable card with:
 *   - Title + "why" rationale
 *   - Numbered steps (clearly readable, copy-able)
 *   - Approve / Dismiss buttons (owner-only)
 *
 * Member sees the strip read-only — they can see what Jarvis is proposing
 * but the decision rests with owner. (The chat-channel mediation pattern
 * we use elsewhere: write-actions on shared identity flow through the
 * owner.)
 */
export function PendingPlansStrip({ apiBaseUrl, sessionId, isOwner }: Props) {
  const [plans, setPlans] = useState<PlanProposal[]>([])
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set())
  const baseUrl = apiBaseUrl.replace(/\/$/, '')

  const refresh = useCallback(async () => {
    if (!sessionId) {
      setPlans([])
      return
    }
    try {
      const res = await fetch(
        `${baseUrl}/api/plans?session_id=${encodeURIComponent(sessionId)}`,
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const j = await res.json()
      setPlans(j?.plans || [])
    } catch {
      // Silent — strip just stays empty if unreachable
      setPlans([])
    }
  }, [baseUrl, sessionId])

  useEffect(() => {
    void refresh()
    const id = window.setInterval(refresh, 4000)
    return () => window.clearInterval(id)
  }, [refresh])

  const resolve = async (planId: string, decision: 'approve' | 'dismiss') => {
    setBusyId(planId)
    setError(null)
    try {
      const res = await fetch(
        `${baseUrl}/api/plans/${encodeURIComponent(planId)}/${decision}`,
        { method: 'POST' },
      )
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || `HTTP ${res.status}`)
      }
      void refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyId(null)
    }
  }

  const toggleCollapse = (planId: string) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev)
      if (next.has(planId)) next.delete(planId)
      else next.add(planId)
      return next
    })
  }

  if (plans.length === 0) return null

  return (
    <div className="flex flex-shrink-0 flex-col border-b border-accent/30 bg-accent/5">
      <div className="flex items-center gap-2 px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-accent">
        <ListChecks size={11} />
        <span>
          {plans.length} pending plan{plans.length === 1 ? '' : 's'}
        </span>
        {!isOwner && (
          <span className="rounded bg-bg2 px-1.5 py-0.5 font-mono text-[9px] tracking-normal text-fg3">
            view only
          </span>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 border-t border-warn/20 bg-danger/10 px-4 py-1.5">
          <AlertCircle size={11} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="font-mono text-[10px] text-danger">{error}</span>
        </div>
      )}

      <div className="flex max-h-[40vh] flex-col gap-2 overflow-y-auto px-4 pb-3 pt-1">
        {plans.map((plan) => {
          const collapsed = collapsedIds.has(plan.plan_id)
          const busy = busyId === plan.plan_id
          return (
            <article
              key={plan.plan_id}
              className="rounded-md border border-accent/30 bg-bg1 shadow-sm"
            >
              <header
                onClick={() => toggleCollapse(plan.plan_id)}
                className="flex cursor-pointer items-center gap-2 border-b border-line/40 px-3 py-2 hover:bg-bg2/40"
              >
                {collapsed ? (
                  <ChevronDown size={12} className="flex-shrink-0 text-fg3" />
                ) : (
                  <ChevronUp size={12} className="flex-shrink-0 text-fg3" />
                )}
                <h3 className="flex-1 truncate text-[13px] font-semibold text-fg">
                  {plan.title}
                </h3>
                <span className="flex-shrink-0 font-mono text-[10px] text-fg3">
                  {plan.steps.length} step{plan.steps.length === 1 ? '' : 's'}
                </span>
              </header>

              {!collapsed && (
                <div className="flex flex-col gap-3 px-3 py-3">
                  {plan.why && (
                    <div className="text-[11px] italic leading-relaxed text-fg2">
                      {plan.why}
                    </div>
                  )}
                  <ol className="flex flex-col gap-1.5 pl-1">
                    {plan.steps.map((step, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-[12px] leading-relaxed text-fg"
                      >
                        <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-accent/15 font-mono text-[9px] font-semibold text-accent">
                          {i + 1}
                        </span>
                        <span className="flex-1 whitespace-pre-wrap break-words">
                          {step}
                        </span>
                      </li>
                    ))}
                  </ol>
                  {isOwner && (
                    <div className="flex items-center justify-end gap-2 border-t border-line/30 pt-2">
                      <button
                        onClick={() => resolve(plan.plan_id, 'dismiss')}
                        disabled={busy}
                        className="flex items-center gap-1 rounded border border-line2 bg-bg2 px-2.5 py-1 text-[11px] text-fg2 hover:border-danger/40 hover:text-danger disabled:opacity-50"
                      >
                        {busy ? <Loader2 size={10} className="animate-spin" /> : <X size={10} />}
                        Dismiss
                      </button>
                      <button
                        onClick={() => resolve(plan.plan_id, 'approve')}
                        disabled={busy}
                        className="flex items-center gap-1 rounded bg-accent px-3 py-1 text-[11px] font-semibold text-bg0 hover:bg-accent/90 disabled:opacity-50"
                      >
                        {busy ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />}
                        Approve
                      </button>
                    </div>
                  )}
                  {!isOwner && (
                    <div className="border-t border-line/30 pt-2 text-[10px] italic text-fg3">
                      Owner skal godkende eller afvise denne plan.
                    </div>
                  )}
                </div>
              )}
            </article>
          )
        })}
      </div>
    </div>
  )
}
