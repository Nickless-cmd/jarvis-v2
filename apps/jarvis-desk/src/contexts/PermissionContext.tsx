import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { PERM_KEY } from '../lib/composerPrefs'
import { getSessionPermission, setSessionPermission } from '../lib/api'
import { SessionContext } from '../contexts/SessionContext'
import type { ApiConfig } from '../lib/api'

export type Permission = 'ask' | 'trust'

export interface PermissionContextValue {
  permission: Permission
  setPermission: (p: Permission) => void
}

export const PermissionContext = createContext<PermissionContextValue | null>(null)

/** Løfter permission ud af Composer så et godkendelseskort kan sætte 'trust'
 *  udefra.
 *
 *  SERVEREN ER KILDEN (Bjørn 20/9-2026). Valget lå før kun i localStorage, og
 *  telefonen havde sit eget i SecureStore — så to klienter kunne vise hver sin
 *  sandhed, mens runnet kørte med den ene. Nu læses samtalens niveau fra
 *  serveren når samtalen skifter, og skrives dertil når brugeren skifter.
 *  localStorage bevares som offline-fallback (samme PERM_KEY som før), så en
 *  frisk/afbrudt klient stadig har et valg indtil serveren svarer.
 *
 *  `config` og sessionen er VALGFRIE: uden dem (fx i en komponent-test, eller
 *  før nogen samtale er valgt) er valget rent lokalt — præcis som før. Uden en
 *  server at tale med er der ingen at arve fra, og det skal ikke kaste. */
export function PermissionProvider({ config, children }: { config?: ApiConfig; children: ReactNode }) {
  const sessionCtx = useContext(SessionContext)
  const activeId = sessionCtx?.activeId ?? null
  const [permission, setPermissionState] = useState<Permission>(() => {
    try { return localStorage.getItem(PERM_KEY) === 'trust' ? 'trust' : 'ask' } catch { return 'ask' }
  })

  // Samtalen skifter → læs dens niveau fra serveren. Fejler kaldet (offline),
  // beholder vi det lokale valg frem for at nulstille til 'ask' i utide.
  useEffect(() => {
    if (!activeId || !config) return
    let afbrudt = false
    void getSessionPermission(config, activeId)
      .then((m) => { if (!afbrudt) setPermissionState(m) })
      .catch(() => { /* offline: behold det lokale valg */ })
    return () => { afbrudt = true }
  }, [activeId, config])

  useEffect(() => {
    try { localStorage.setItem(PERM_KEY, permission) } catch { /* ignore */ }
  }, [permission])

  const setPermission = useCallback((p: Permission) => {
    setPermissionState(p)
    // Skriv til serveren så den ANDEN klient arver valget. Fejler det, står
    // valget stadig lokalt — næste samtale-åbning forsøger igen.
    if (activeId && config) {
      void setSessionPermission(config, activeId, p).catch(() => { /* ignore */ })
    }
  }, [activeId, config])

  const value = useMemo(() => ({ permission, setPermission }), [permission, setPermission])
  return <PermissionContext.Provider value={value}>{children}</PermissionContext.Provider>
}
