/** Bærer rækken den godkendelse der venter LIGE NU?
 *
 *  31/10-2026. DEL 3 flyttede godkendelses-kortet ind i transcriptet som en
 *  `approval_request`-række. Men rækken er ikke garanteret til stede:
 *
 *  * den hentes af `refreshMessages` (op til 1,5 s forsinkelse), og
 *  * godkendelser der ikke går gennem `_publicer_approval_requested` bliver
 *    slet ikke persisteret.
 *
 *  MÅLT 31/10: Bjørn så INTET kort i PWA'en efter 0.6.294 og måtte godkende i
 *  APK'en, som kørte den gamle bundle. Spørgsmålet forsvandt — det er den
 *  værste fejlform, fordi den er tavs.
 *
 *  Derfor to flader med ÉN betingelse: rækken vinder når den findes, ellers
 *  bærer det flydende kort svaret. Denne funktion er betingelsen — og den kan
 *  testes, hvilket en inline-IIFE i et view ikke kunne.
 *
 *  Match på `approval_id`, aldrig på tekst: to godkendelser kan have samme
 *  kommando, og et tekst-match ville give knapper på den forkerte række.
 */
export function findesGodkendelseIRækken(
  raekker: ReadonlyArray<{ role: string; content_json?: unknown }>,
  approvalId: string | null | undefined,
): boolean {
  if (!approvalId) return false
  return raekker.some((m) => {
    if (m.role !== 'approval_request') return false
    const liste = Array.isArray(m.content_json) ? m.content_json : []
    const blok = liste[0] as { approval_id?: unknown } | undefined
    return String(blok?.approval_id ?? '') === approvalId
  })
}
