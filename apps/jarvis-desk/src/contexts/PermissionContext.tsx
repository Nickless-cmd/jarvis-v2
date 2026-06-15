import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { PERM_KEY } from '../lib/composerPrefs'

export type Permission = 'ask' | 'trust'

export interface PermissionContextValue {
  permission: Permission
  setPermission: (p: Permission) => void
}

export const PermissionContext = createContext<PermissionContextValue | null>(null)

/** Løfter permission ud af Composer så et godkendelseskort kan sætte 'trust'
 *  udefra. localStorage-bagudkompatibel (samme PERM_KEY som før). */
export function PermissionProvider({ children }: { children: ReactNode }) {
  const [permission, setPermissionState] = useState<Permission>(() => {
    try { return localStorage.getItem(PERM_KEY) === 'trust' ? 'trust' : 'ask' } catch { return 'ask' }
  })
  useEffect(() => {
    try { localStorage.setItem(PERM_KEY, permission) } catch { /* ignore */ }
  }, [permission])
  const setPermission = useCallback((p: Permission) => setPermissionState(p), [])
  const value = useMemo(() => ({ permission, setPermission }), [permission, setPermission])
  return <PermissionContext.Provider value={value}>{children}</PermissionContext.Provider>
}
