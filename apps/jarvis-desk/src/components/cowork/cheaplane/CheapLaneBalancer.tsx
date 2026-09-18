/**
 * Balanceren — og hvorfor et slot ikke bliver valgt.
 *
 * Bjørn 16/9-2026: «jeg ander intet om hvordan cheap lane eller
 * load_balanceren klarer sig». En vægt på 0 uden en grund er netop den slags
 * tal han ikke kan bruge: en oplysning om at noget er galt, uden at sige hvad.
 *
 * ## Hvorfor hårde afvisninger står først
 *
 * Et slot i køling har vægt 0 uanset hvor god dets succesrate er. Står de to
 * ligeværdigt på skærmen, inviterer fladen til at rette på det forkerte — man
 * kigger på en succesrate på 20 % og glemmer at slottet slet ikke er i spil.
 * Derfor: hårde gates (køling, slået fra, breaker) først, og de bløde faktorer
 * bagefter, som forklaring på HVOR STOR vægten er, ikke på om der er nogen.
 *
 * ## Hvorfor simuleringen siger hvad den er
 *
 * Knappen står ved siden af knapper der pauser og nulstiller. «Simulér» alene
 * kan ikke bære tvivlen om hvorvidt der bliver sendt et rigtigt kald, så
 * fladen siger det ligeud.
 */
import { useMemo, useState } from 'react'
import type { BalancerSlot } from '../../../lib/cheapLaneApi'
import { Handling, type Kommando, type Udfoer } from './CheapLaneControls'

type Simuler = (taskKind: string, skip: string[]) => Promise<{
  candidates?: { provider?: string; model?: string; slot_id?: string; weight?: number;
    eligible?: boolean; reason?: string }[]
  chosen?: string | null
}>

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '–'
  return `${Math.round(v * 100)} %`
}

/** Hårde afvisninger — de afgør OM slottet er i spil. */
function haardeGrunde(s: BalancerSlot): string[] {
  const ud: string[] = []
  if (s.manually_disabled) ud.push('Slået fra manuelt')
  if (s.status === 'cooldown' || s.cooldown_until) {
    ud.push(`Køling aktiv${s.cooldown_reason ? ` — ${s.cooldown_reason}` : ''}`)
  }
  if ((s.breaker_level ?? 0) > 0) ud.push(`Breaker på niveau ${s.breaker_level}`)
  if (s.status === 'disabled') ud.push('Slået fra i registret')
  if (s.status === 'stale') ud.push('Slottet er forældet i puljen')
  return ud
}

/** Bløde faktorer — de afgør HVOR STOR vægten er. */
function bloedeFaktorer(s: BalancerSlot): { navn: string; vaerdi: string }[] {
  return [
    { navn: 'Succesrate', vaerdi: pct(s.success_rate) },
    { navn: 'Hovedrum', vaerdi: pct(s.headroom_pct) },
    { navn: 'Kald i minuttet', vaerdi: `${s.rpm_used ?? 0} / ${s.rpm_limit ?? '–'}` },
    { navn: 'Fejl i træk', vaerdi: String(s.consecutive_failures ?? 0) },
  ]
}

function Forklaring({ slot, udfoer }: { slot: BalancerSlot; udfoer: Udfoer }) {
  const haarde = haardeGrunde(slot)
  const handlinger: { etiket: string; kommando: Kommando }[] = [
    { etiket: 'Frigiv køling', kommando: { action: 'slot.release-cooldown', target: slot.slot_id } },
    { etiket: 'Nulstil breaker', kommando: { action: 'slot.reset-breaker', target: slot.slot_id } },
    { etiket: 'Pause slot', kommando: { action: 'slot.pause', target: slot.slot_id } },
    { etiket: 'Dræn slot', kommando: { action: 'slot.drain', target: slot.slot_id } },
  ]

  return (
    <section className="cl-forklaring" role="region"
             aria-label={`Forklaring for ${slot.provider} / ${slot.model}`}>
      <h4>{slot.provider} / {slot.model}</h4>
      <p className="cl-vaegt">Vægt {slot.weight ?? 0} · {slot.auth_profile || '–'} · {slot.egress || '–'}</p>

      {haarde.length ? (
        <>
          <p className="cl-forklaring-overskrift">Hård afvisning</p>
          <ul className="cl-haarde">{haarde.map((g) => <li key={g}>{g}</li>)}</ul>
          <p className="cl-dæmpet cl-lille">
            Så længe en hård afvisning står, er vægten 0 uanset tallene nedenfor.
          </p>
        </>
      ) : (
        <p className="cl-forklaring-overskrift">Ingen hård afvisning</p>
      )}

      <dl className="cl-faktorer">
        {bloedeFaktorer(slot).map((f) => (
          <div key={f.navn}><dt>{f.navn}</dt><dd>{f.vaerdi}</dd></div>
        ))}
      </dl>

      <div className="cl-handlinger">
        {handlinger.map((h) => (
          <Handling key={h.etiket} etiket={h.etiket} kommando={h.kommando} udfoer={udfoer} />
        ))}
      </div>
    </section>
  )
}

export function CheapLaneBalancer({
  slots, udfoer, simuler,
}: {
  slots: BalancerSlot[]
  udfoer: Udfoer
  simuler: Simuler
}) {
  const [status, setStatus] = useState('')
  const [valgt, setValgt] = useState<string>('')
  const [sim, setSim] = useState<Awaited<ReturnType<Simuler>> | null>(null)
  const [simKører, setSimKører] = useState(false)
  const [revision, setRevision] = useState('')

  const synlige = useMemo(
    () => (status ? slots.filter((s) => (s.status ?? '') === status) : slots),
    [slots, status])

  const valgtSlot = slots.find((s) => s.slot_id === valgt) ?? null

  // Revisionen kommer fra serveren og vises ved handlingen: uden den kan man
  // ikke bagefter finde sin egen ændring i sporet.
  const medRevision: Udfoer = async (k) => {
    const svar = await udfoer(k) as { revision?: string } | undefined
    if (svar?.revision) setRevision(svar.revision)
    return svar
  }

  return (
    <div className="cl-balancer">
      <div className="cl-soeg-raekke">
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">alle</option>
            <option value="healthy">healthy</option>
            <option value="cooldown">cooldown</option>
            <option value="disabled">disabled</option>
            <option value="stale">stale</option>
          </select>
        </label>
        <button type="button" className="cl-handling" disabled={simKører}
                onClick={async () => {
                  setSimKører(true)
                  try { setSim(await simuler('default', [])) } finally { setSimKører(false) }
                }}>
          {simKører ? 'Simulerer…' : 'Simulér routing'}
        </button>
        <span className="cl-dæmpet cl-lille">
          Simuleringen er en læsning: der sendes intet provider-kald.
        </span>
      </div>

      {revision ? (
        <p className="cl-kvittering">Udført. Revision <code>{revision}</code> i sporet.</p>
      ) : null}

      {sim ? (
        <div className="cl-simulering">
          <p>
            Ville vælge:{' '}
            <strong>
              {sim.candidates?.find((c) => c.slot_id === sim.chosen)
                ? `${sim.candidates.find((c) => c.slot_id === sim.chosen)?.provider} / ${sim.candidates.find((c) => c.slot_id === sim.chosen)?.model}`
                : sim.chosen || 'ingen'}
            </strong>
          </p>
          <ul className="cl-lille">
            {(sim.candidates ?? []).map((c) => (
              <li key={c.slot_id}>
                {c.provider} / {c.model} — vægt {c.weight ?? 0}
                {c.eligible === false ? ` · afvist${c.reason ? `: ${c.reason}` : ''}` : ''}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="cl-med-inspektor">
        <div className="cl-tabel-holder">
          <table className="cl-tabel">
            <thead>
              <tr>
                <th scope="col">Slot</th><th scope="col">Status</th>
                <th scope="col">Vægt</th><th scope="col">Succes</th><th scope="col">Hovedrum</th>
              </tr>
            </thead>
            <tbody>
              {synlige.map((s) => (
                <tr key={s.slot_id}>
                  <th scope="row">
                    <button type="button" className="cl-linkknap" onClick={() => setValgt(s.slot_id)}>
                      {s.provider} / {s.model}
                    </button>
                  </th>
                  <td>{s.status ?? '–'}</td>
                  <td>{s.weight ?? 0}</td>
                  <td>{pct(s.success_rate)}</td>
                  <td>{pct(s.headroom_pct)}</td>
                </tr>
              ))}
              {!synlige.length && <tr><td colSpan={5}>Ingen slots matcher.</td></tr>}
            </tbody>
          </table>
        </div>

        {valgtSlot ? <Forklaring slot={valgtSlot} udfoer={medRevision} /> : null}
      </div>
    </div>
  )
}
