/** Presence-dot (Jarvis' ønske): rolig liveness-indikator i chat-headeren.
 *  KUN forbindelses/liveness-status fra StreamContext — INGEN affektiv data-
 *  polling (det forbliver i Mission Control). Grøn=klar, gul=arbejder,
 *  rød=fejl/afbrudt. */
export function PresenceDot({ status }: { status: string }) {
  const color =
    status === 'working' ? 'yellow' : status === 'error' || status === 'interrupted' ? 'red' : 'green'
  return <span className={`presence-dot ${color}`} title="Jarvis" />
}
