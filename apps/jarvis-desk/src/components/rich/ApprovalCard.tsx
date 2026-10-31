import { useEffect, useState } from 'react'

/** Interaktivt approval-kort. Approve/Deny er ÆGTE UI-knapper (ikke renderet fra
 *  model/tool-tekst). Action-teksten vises inert via <pre> så fjendtligt indhold
 *  ikke kan spoofe en klikbar approve-knap. Rolle-gate: kun owner (canApprove)
 *  ser knapperne — serveren håndhæver den reelle grænse.
 *
 * 31/10-2026 — FORMEN ER ÆNDRET, ADGANGSGRÆNSEN ER IKKE.
 *
 * Bjørns symptom, gentaget: «skubber chatview op» og «aldrig samme størrelse».
 * Kortet voksede fra ~60 px til 360 px fordi `action` stod i en `<pre>` med
 * `max-height: min(40vh, 360px)` — og kortet lå i FLOW oven over composeren,
 * så hver px det voksede, blev taget fra transcriptet.
 *
 * Nu er kortet ÉN linje på fast højde, og kommandoen ligger bag et klik. Det
 * er dét der gør højden forudsigelig: den kollapsede linje ændrer sig ikke,
 * uanset om kommandoen er 20 eller 2000 tegn.
 *
 * FOLDEN: `grid-template-rows: 0fr → 1fr` på en wrapper med `overflow: hidden`.
 * Ikke `hidden`/`display:none` — det giver ingen animerbar højde, og teksten
 * ville forsvinde ud af DOM'en for tests og skærmlæsere. Ikke `interpolate-size:
 * allow-keywords` + `height: 0 → auto` heller: det virker i Chromium 129+, men
 * desk-PWA'en kører også på Safari og Firefox, og dér ville folden springe.
 * Grid-teknikken animerer den faktiske højde uden at gætte px og uden en
 * browser-afhængig egenskab.
 *
 * `inert` på det skjulte indhold: uden den kan man TABBE til noget man ikke
 * kan se. Det var en reel tilgængelighedsfejl i den gamle form (målt mod
 * Codex-appens tilsvarende komponent, som har det).
 */
export function ApprovalCard({
  approvalId,
  tool,
  action,
  risk,
  canApprove,
  onApprove,
  onDeny,
  expiresAt,
}: {
  approvalId: string
  tool: string
  action: string
  risk: string
  canApprove: boolean
  onApprove: (id: string) => void
  onDeny: (id: string) => void
  /** Serverens frist (ISO-tid). Se `PendingApproval.expiresAt` for hvorfor
   *  den findes: uden den kunne kortet hænge for evigt. */
  expiresAt?: string
}) {
  const [nu, setNu] = useState(() => Date.now())
  const [aaben, setAaben] = useState(false)
  const harFrist = Boolean(expiresAt)

  // Kun en tikker når der FAKTISK er en frist. Et kort uden frist skal ikke
  // starte et ur der aldrig viser noget — det ville være en usynlig byrde pr.
  // kort, og der kan ligge flere.
  useEffect(() => {
    if (!harFrist) return
    const id = window.setInterval(() => setNu(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [harFrist, expiresAt])

  const slut = expiresAt ? Date.parse(expiresAt) : NaN
  const msTilbage = Number.isFinite(slut) ? slut - nu : NaN
  const udloebet = Number.isFinite(msTilbage) && msTilbage <= 0

  return (
    <div className={`approvalcard risk-${risk}${udloebet ? ' approvalcard-udloebet' : ''}`}>
      {/* Linjen: fast højde, knapperne bor HER så de er synlige uden at folde ud. */}
      <div className="approvallinje">
        <button
          type="button"
          className="approvallinje-aabn"
          aria-expanded={aaben}
          onClick={() => setAaben((v) => !v)}
          title={aaben ? 'Skjul kommandoen' : 'Vis kommandoen'}
        >
          <span className="approvallinje-pil" aria-hidden="true">{aaben ? '▾' : '▸'}</span>
          <span className="approvallinje-tool">{tool}</span>
          <span className="approvallinje-resume">{resume(action)}</span>
        </button>

        {udloebet ? (
          <span className="approvalcard-frist">Fristen løb ud</span>
        ) : Number.isFinite(msTilbage) ? (
          <span className="approvalcard-frist">{nedtaelling(msTilbage)}</span>
        ) : null}

        {udloebet ? null : canApprove ? (
          <span className="approvalcard-actions">
            <button type="button" onClick={() => onApprove(approvalId)}>Godkend</button>
            <button type="button" onClick={() => onDeny(approvalId)}>Afvis</button>
          </span>
        ) : (
          <span className="approvalcard-readonly">Kun owner kan godkende</span>
        )}
      </div>

      {/* Kroppen: foldet ud bag klik. `inert` når den er lukket, så TAB ikke
          lander i noget usynligt. */}
      <div className="approvallinje-krop" data-aaben={aaben ? 'true' : 'false'}>
        <div className="approvallinje-indre">
          <pre className="approvalcard-action" inert={!aaben}>{action}</pre>
        </div>
      </div>

      {udloebet ? (
        // Kortet svarer ikke længere: serveren har fejet posten, og både
        // «Godkend» og «Afvis» ville fejle. At vise knapperne alligevel var
        // netop fejlen — de så brugbare ud og var det ikke. Runnet har selv
        // afsluttet, og beskeden er sendt ad notifikations-vejen.
        <div className="approvalcard-readonly">
          Ingen godkendelse kom i tide. Runnet er afsluttet og venter på næste træk.
        </div>
      ) : null}
    </div>
  )
}

/** Første meningsfulde linje af kommandoen, kortet ned.
 *
 *  Linjen skal kunne læses på et blik uden at folde ud — det er hele pointen
 *  med den faste højde. Derfor første ikke-tomme linje, ikke en sammentrækning
 *  af alle: en kommando med `cd x && ...` ville blive volapyk.
 */
function resume(tekst: string): string {
  const første = String(tekst || '')
    .split('\n')
    .map((l) => l.trim())
    .find((l) => l.length > 0) || ''
  if (!første) return ''
  return første.length > 72 ? `${første.slice(0, 71)}…` : første
}

/** «4:32 tilbage» — eller «under 1 min» når det haster. */
function nedtaelling(ms: number): string {
  const sek = Math.max(0, Math.floor(ms / 1000))
  if (sek < 60) return `${sek}s tilbage`
  const min = Math.floor(sek / 60)
  const rest = sek % 60
  return `${min}:${String(rest).padStart(2, '0')} tilbage`
}
