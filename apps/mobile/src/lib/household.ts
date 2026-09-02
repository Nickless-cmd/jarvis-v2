import type { WhoAmI } from './types'

/**
 * Bor denne bruger i hjemmet?
 *
 * Bruges KUN til at skjule en indgang. Den ægte grænse ligger på serveren:
 * /companion/senses afviser alle andre roller med 403 i auth-laget. Bygger
 * nogen en anden klient — eller en desktop-flade — holder døren stadig.
 *
 * Derfor er denne funktion bevidst simpel og har ingen fallback: kan vi ikke
 * afgøre rollen, skjuler vi indgangen. At gætte forkert her ville kun betyde en
 * synlig knap der giver 403; at gætte forkert den anden vej ville betyde en
 * knap Michelle ikke kan finde.
 */
export function livesInHousehold(me: Pick<WhoAmI, 'role'> | null | undefined): boolean {
  const role = String(me?.role ?? '').trim().toLowerCase()
  return role === 'owner' || role === 'partner'
}
