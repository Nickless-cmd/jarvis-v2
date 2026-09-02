import { useEffect, useRef, useState } from 'react'
import NetInfo from '@react-native-community/netinfo'
import { whoami } from './apiClient'
import type { ApiConfig } from './types'

export type Connectivity = 'connected' | 'offline' | 'reconnecting'

/**
 * Vedvarende forbindelses-status til mobilen: forbundet / offline / genopretter.
 * - Netværk væk (NetInfo) → offline med det samme.
 * - Netværk til stede men Jarvis-API uden svar → reconnecting (vi pinger whoami).
 * - whoami svarer → connected.
 * Pinger periodisk + når netværket kommer tilbage, så "mistet/genopret" er synligt.
 */
export function useConnectivity(config: ApiConfig | null): Connectivity {
  const [state, setState] = useState<Connectivity>('connected')
  const hasNet = useRef(true)

  useEffect(() => {
    if (!config) return
    let alive = true
    let timer: ReturnType<typeof setTimeout> | null = null

    const ping = async () => {
      if (!alive) return
      if (!hasNet.current) { setState('offline'); return }
      try {
        await whoami(config)
        if (alive) setState('connected')
      } catch {
        if (alive) setState('reconnecting')
      } finally {
        if (alive) timer = setTimeout(ping, 15000)
      }
    }

    const unsub = NetInfo.addEventListener((s) => {
      const online = !!s.isConnected && s.isInternetReachable !== false
      hasNet.current = online
      if (!online) setState('offline')
      else { setState((cur) => (cur === 'offline' ? 'reconnecting' : cur)); void ping() }
    })

    void ping()
    return () => { alive = false; if (timer) clearTimeout(timer); unsub() }
  }, [config?.apiBaseUrl, config?.authToken])

  return state
}
