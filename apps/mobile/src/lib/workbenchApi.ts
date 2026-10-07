import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

/** Operator-kanalen på telefonen (6/9-2026).
 *
 *  Mens kanalen er åben kører `bash` på Bjørns egen maskine UDEN godkendelse
 *  pr. kald, i op til fire timer. På desk kan han se det; væk fra skrivebordet
 *  kunne han ikke. Telefonen er præcis dér man opdager at man glemte at lukke
 *  den — så den hører hjemme i Arbejde-rummet ved siden af godkendelserne.
 *
 *  Status kræver ikke owner. At åbne og lukke gør.
 */
export type OperatorChannel = {
  open: boolean
  udloeber_om_s?: number
}

export async function fetchOperatorChannel(
  config: ApiConfig,
  sessionId?: string,
): Promise<OperatorChannel> {
  const q = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return apiFetch<OperatorChannel>(config, `/workbench/operator-channel${q}`)
}

export async function lukOperatorChannel(
  config: ApiConfig,
  sessionId?: string,
): Promise<OperatorChannel> {
  // Session-id'et SKAL med (målt 7/10-2026): kanalen er pr. session, og et kald
  // uden id ramte nøglen `_default` — mens bash bruger `chat-<session>`. Uden
  // det viste telefonen «Luk» om en kanal den aldrig rørte. Serveren afviser
  // nu et kald uden id med 400 frem for at skrive en nøgle ingen bruger.
  return apiFetch<OperatorChannel>(config, '/workbench/operator-channel/close', {
    method: 'POST',
    body: sessionId ? { session_id: sessionId } : {},
  })
}

/** Timer tilbage, afrundet — «om 3 t» er nok, minuttet betyder intet her. */
export function timerTilbage(kanal: OperatorChannel | null): number {
  const s = kanal?.udloeber_om_s ?? 0
  return s > 0 ? Math.max(1, Math.round(s / 3600)) : 0
}
