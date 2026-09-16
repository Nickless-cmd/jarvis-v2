import { useEffect, useMemo, useState } from 'react'
import { getSessionMilestones } from './api'
import { bygRailAnkre, type RailAnker } from './railAnkre'

type Cfg = { apiBaseUrl: string; authToken: string | null } | null

/**
 * Saved rails ankre for en session — ét sted for både Chat og Code.
 *
 * Kapitlerne hentes ved sessionsskift og hver gang en tur slutter (`tur`
 * skifter til idle). Serveren cacher dem og regenererer først efter tre nye
 * ture, så et kald pr. tur koster ingen LLM-kald.
 */
export function useRailAnkre(
  cfg: Cfg,
  sessionId: string | null,
  beskeder: { id: string; role: string; content: unknown; created_at?: string }[],
  turErSlut: boolean,
): RailAnker[] {
  const [kapitler, setKapitler] = useState<{ anchor_id: string; title: string }[]>([])
  const base = cfg?.apiBaseUrl
  const token = cfg?.authToken
  useEffect(() => {
    setKapitler([])
    if (!base || !sessionId) return
    let levende = true
    getSessionMilestones({ apiBaseUrl: base, authToken: token ?? null }, sessionId)
      .then((r) => { if (levende) setKapitler(r.milestones || []) })
      .catch(() => { /* ingen kapitler — komprimeringerne står stadig */ })
    return () => { levende = false }
    // Nulstil KUN ved sessionsskift; en ny tur beholder de gamle til de nye kommer.
  }, [base, token, sessionId])
  useEffect(() => {
    if (!base || !sessionId || !turErSlut) return
    let levende = true
    getSessionMilestones({ apiBaseUrl: base, authToken: token ?? null }, sessionId)
      .then((r) => { if (levende && r.milestones?.length) setKapitler(r.milestones) })
      .catch(() => {})
    return () => { levende = false }
  }, [turErSlut])  // eslint-disable-line react-hooks/exhaustive-deps
  return useMemo(() => bygRailAnkre(beskeder, kapitler), [beskeder, kapitler])
}
