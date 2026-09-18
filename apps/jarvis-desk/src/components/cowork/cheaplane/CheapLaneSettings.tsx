/**
 * Opbevaringstider — med den ene regel der ikke kan forhandles.
 *
 * Redigerede payloads må ikke ligge længere end metadata. En prompt er det
 * mest private i systemet, og en indstilling der lod den overleve sin egen
 * metadata ville betyde at den blev liggende uden at nogen kunne se hvilket
 * kald den hørte til, hvornår det skete, eller hvorfor den blev gemt.
 *
 * Derfor afvises den kombination HER — ikke først på serveren. En fejl der
 * kommer efter at man troede man havde gemt, er en fejl man ikke opdager.
 */
import { useState } from 'react'
import type { Udfoer } from './CheapLaneControls'

export function CheapLaneSettings({
  metadataDage, payloadDage, udfoer,
}: {
  metadataDage: number
  payloadDage: number
  udfoer: Udfoer
}) {
  const [meta, setMeta] = useState(String(metadataDage))
  const [payload, setPayload] = useState(String(payloadDage))
  const [fejl, setFejl] = useState('')
  const [kvittering, setKvittering] = useState('')

  async function gem() {
    const m = Number(meta)
    const p = Number(payload)
    setKvittering('')
    if (!Number.isFinite(m) || !Number.isFinite(p) || m < 1 || p < 1) {
      setFejl('Begge tider skal være hele dage over 0.')
      return
    }
    if (p > m) {
      setFejl('Payloads må ikke ligge længere end metadata — ellers står en '
        + 'prompt tilbage uden det kald den hørte til.')
      return
    }
    setFejl('')
    try {
      await udfoer({
        action: 'retention.set', target: 'cheap-lane',
        reason: 'opbevaring ændret fra desk',
        parameters: { metadata_days: m, payload_days: p },
      })
      setKvittering('Gemt.')
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'kunne ikke gemme')
    }
  }

  return (
    <div className="cl-indstillinger">
      <label>
        Metadata (dage)
        <input value={meta} onChange={(e) => setMeta(e.target.value)} inputMode="numeric" />
      </label>
      <label>
        Payload (dage)
        <input value={payload} onChange={(e) => setPayload(e.target.value)} inputMode="numeric" />
      </label>
      {fejl ? <p className="cl-handling-fejl" role="alert">{fejl}</p> : null}
      {kvittering ? <p className="cl-kvittering">{kvittering}</p> : null}
      <button type="button" className="cl-handling" onClick={() => void gem()}>Gem</button>
    </div>
  )
}
