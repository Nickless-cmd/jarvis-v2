/**
 * Vækningen taget imod — broen åbnes, kaldet udføres, forbindelsen lukkes.
 *
 * Serveren sender en tavs data-push (`kind: 'bro_vaekning'`, ingen title eller
 * preview, så Android viser ingenting) når den vil bruge et telefon-værktøj og
 * broen ikke er der. Her åbnes den så.
 *
 * **Vinduet er Androids, ikke vores.** En FCM-vækket baggrunds-handler får
 * nogle få tiendedele af et minut, før systemet lukker den ned igen. Derfor
 * holdes forbindelsen åben i et bundet vindue og lukkes så — at lade den stå
 * ville ikke give mere tid, kun en forbindelse der dør uden at sige det.
 *
 * Vinduet forlænges når der faktisk kommer et kald: kommer der ét, er der
 * sandsynligvis flere i samme tur, og det ville være dumt at lukke midt i.
 */

import { opretBro, type Bro } from './broKlient'
import { KAN_UDFOERE, udfoerVaerktoej } from './telefonHandlere'
import { klientId } from './broOpstart'
import type { ApiConfig } from './types'

/** Hvor længe vi holder åbent uden aktivitet. Androids vindue er kortere end
 *  man tror; sætter man den højere, venter man bare på at blive lukket ned. */
export const TOMGANG_MS = 12000

/** Hårdt loft. Selv med kald på kald skal en vækning ikke blive til en
 *  permanent forbindelse — dét er en foreground-service, og det er en anden
 *  beslutning med et notifikations-ikon Bjørn skal sige ja til. */
export const LOFT_MS = 45000

export const VAEKNING_KIND = 'bro_vaekning'

export function erVaekning(data: { kind?: string } | null | undefined): boolean {
  return String(data?.kind ?? '') === VAEKNING_KIND
}

export interface VaekningsOpsaetning {
  /** Injicerbar til test. */
  lavBro?: (config: ApiConfig, id: string, paaAktivitet: () => void) => Bro
  naa?: () => number
  vent?: (ms: number) => Promise<void>
}

/**
 * Åbn broen og hold den åben mens der er noget at lave.
 *
 * Returnerer når vinduet er brugt op — baggrunds-handleren skal AWAITE den,
 * ellers lukker Android JS-konteksten ned i det sekund handleren returnerer,
 * og broen dør før serveren når at sende sit kald.
 */
export async function haandterVaekning(
  config: ApiConfig, opsaetning: VaekningsOpsaetning = {}
): Promise<{ kald: number }> {
  const naa = opsaetning.naa ?? (() => Date.now())
  const vent = opsaetning.vent ?? ((ms) => new Promise((r) => setTimeout(r, ms)))

  let kald = 0
  let sidsteAktivitet = naa()
  const paaAktivitet = () => { kald += 1; sidsteAktivitet = naa() }

  const id = await klientId()
  const lavBro = opsaetning.lavBro ?? ((c, klient, paa) => opretBro({
    apiBaseUrl: c.apiBaseUrl,
    authToken: c.authToken,
    capabilities: KAN_UDFOERE,
    clientId: klient,
    udfoer: async (vaerktoej, args) => {
      paa()
      return udfoerVaerktoej(vaerktoej, args)
    }
  }))

  const bro = lavBro(config, id, paaAktivitet)
  bro.start()

  const start = naa()
  try {
    for (;;) {
      await vent(500)
      const nu = naa()
      if (nu - sidsteAktivitet >= TOMGANG_MS) break
      if (nu - start >= LOFT_MS) break
    }
  } finally {
    bro.stop()
  }
  return { kald }
}
