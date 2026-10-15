import type { WhoAmI } from './api'

/** Hvad App skal vise, givet login-tilstanden alene. */
export type AppGate = 'offline' | 'loading' | 'app'

/**
 * Beslut hvilken skal App viser — FØR nogen komponent læser `auth`.
 *
 * ## Hvorfor denne findes (15/10-2026)
 *
 * `ChatFlowProvider` blev født med `identity={auth!}`. `!` er en
 * TypeScript-assertion, ikke et værn: den siger «stol på mig» til compileren
 * og gør intet ved runtime. I Electron er `browser=false`, og SettingsContext
 * eksponerer derfor `authStatus` som `undefined` — så hverken
 * `=== 'checking'` eller `=== 'ready' && !auth` matchede, grenen faldt
 * igennem med `auth === null`, og `identity.user_id` kastede:
 *
 *     Cannot read properties of null (reading 'user_id')
 *
 * Hele visningen faldt, i AppImage'en og ingen andre steder — for i web
 * fanger `'checking'`-guarden det i samme øjeblik.
 *
 * Læren er ikke «husk `authStatus === 'idle'`». Den er at beslutningen om at
 * en identity FINDES skal træffes ét sted, ud fra `auth` selv, og ikke
 * udledes af en status-streng der har fire værdier og et femte, fraværende
 * tilfælde. `authStatus` har `'checking' | 'ready' | 'offline' | 'idle'` —
 * plus `undefined` i Electron.
 *
 * Rækkefølgen er valgt, ikke tilfældig: `offline` tjekkes FØRST, for en
 * forbindelsesfejl skal kunne forklares også når vi aldrig fik en identity.
 */
export function appGate(
  authStatus: 'checking' | 'ready' | 'offline' | 'idle' | undefined,
  auth: WhoAmI | null,
): AppGate {
  if (authStatus === 'offline') return 'offline'
  // Uden en identity er der intet at vise — uanset hvad status-strengen siger.
  // Dækker 'checking', 'idle' og Electrons `undefined`.
  if (!auth || authStatus === 'checking') return 'loading'
  return 'app'
}
