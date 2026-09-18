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
import { CheapLaneTabel, Status } from './CheapLaneTabel'

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
  // Bias er BUNDET i serveren (-0,9 til 2,0). Fladen tilbyder de tre trin der
  // betyder noget — «vælg oftere», «neutral», «vælg sjældnere» — frem for et
  // frit tal ingen kan kalibrere i hovedet.
  const bias: { etiket: string; vaerdi: number }[] = [
    { etiket: 'Vælg oftere', vaerdi: 0.5 },
    { etiket: 'Neutral', vaerdi: 0 },
    { etiket: 'Vælg sjældnere', vaerdi: -0.5 },
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

      <p className="cl-forklaring-overskrift">Routing-vægt</p>
      <div className="cl-handlinger">
        {bias.map((b) => (
          <Handling key={b.etiket} etiket={b.etiket} udfoer={udfoer}
                    kommando={{ action: 'routing-bias.set',
                                target: `${slot.provider}/${slot.model}`,
                                parameters: { routing_bias: b.vaerdi } }} />
        ))}
      </div>
      <p className="cl-dæmpet cl-lille">
        Vægten flytter slottet inden for sin egen gruppe. En anonym proxy
        bliver ikke valgt før en udbyder med legitimation, uanset vægt.
      </p>
    </section>
  )
}

export function CheapLaneBalancer({
  slots, udfoer, simuler, genopbyg,
}: {
  slots: BalancerSlot[]
  udfoer: Udfoer
  simuler: Simuler
  /** Bygger puljen op igen fra registret. Egen knap, fordi den rammer HELE
   *  puljen og ikke ét slot. */
  genopbyg?: () => Promise<unknown>
}) {
  const [status, setStatus] = useState('')
  const [udbyder, setUdbyder] = useState('')
  const [profil, setProfil] = useState('')
  const [egress, setEgress] = useState('')
  const [helbred, setHelbred] = useState('')
  const [valgt, setValgt] = useState<string>('')
  const [sim, setSim] = useState<Awaited<ReturnType<Simuler>> | null>(null)
  const [simKører, setSimKører] = useState(false)
  const [revision, setRevision] = useState('')

  const værdier = (nøgle: keyof BalancerSlot) =>
    [...new Set(slots.map((s) => String(s[nøgle] ?? '')).filter(Boolean))].sort()

  const synlige = useMemo(() => slots.filter((s) => {
    if (status && (s.status ?? '') !== status) return false
    if (udbyder && (s.provider ?? '') !== udbyder) return false
    if (profil && (s.auth_profile ?? '') !== profil) return false
    if (egress && (s.egress ?? '') !== egress) return false
    // «Helbred» er ikke det samme som status: et slot kan staa som healthy og
    // stadig have en aaben breaker eller nul vaegt. Det er DET spoergsmaal man
    // stiller naar man leder efter noget der ikke virker.
    if (helbred === 'i-spil' && (haardeGrunde(s).length > 0 || (s.weight ?? 0) <= 0)) return false
    if (helbred === 'blokeret' && haardeGrunde(s).length === 0) return false
    return true
  }), [slots, status, udbyder, profil, egress, helbred])

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
            {værdier('status').map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
        <label>
          Udbyder
          <select value={udbyder} onChange={(e) => setUdbyder(e.target.value)}>
            <option value="">alle</option>
            {værdier('provider').map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
        <label>
          Profil
          <select value={profil} onChange={(e) => setProfil(e.target.value)}>
            <option value="">alle</option>
            {værdier('auth_profile').map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
        <label>
          Egress
          <select value={egress} onChange={(e) => setEgress(e.target.value)}>
            <option value="">alle</option>
            {værdier('egress').map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
        <label>
          Helbred
          <select value={helbred} onChange={(e) => setHelbred(e.target.value)}>
            <option value="">alle</option>
            <option value="i-spil">kan vælges nu</option>
            <option value="blokeret">blokeret</option>
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
        {genopbyg ? (
          <button type="button" className="cl-handling" onClick={() => void genopbyg()}>
            Genopbyg puljen
          </button>
        ) : null}
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
        <CheapLaneTabel
          raekker={synlige}
          noegle={(s) => s.slot_id}
          tom="Ingen slots matcher."
          kolonner={[
            { id: 'slot', navn: 'Slot', vaerdi: (s) => `${s.provider} ${s.model}`,
              celle: (s) => (
                <button type="button" className="cl-linkknap" onClick={() => setValgt(s.slot_id)}>
                  {s.provider} / {s.model}
                </button>) },
            { id: 'status', navn: 'Status', vaerdi: (s) => s.status,
              celle: (s) => <Status status={s.status} /> },
            { id: 'vaegt', navn: 'Vægt', vaerdi: (s) => s.weight ?? 0,
              celle: (s) => s.weight ?? 0 },
            { id: 'succes', navn: 'Succes', vaerdi: (s) => s.success_rate ?? undefined,
              celle: (s) => pct(s.success_rate) },
            { id: 'hovedrum', navn: 'Hovedrum', vaerdi: (s) => s.headroom_pct ?? undefined,
              celle: (s) => pct(s.headroom_pct) },
          ]}
        />

        {valgtSlot ? <Forklaring slot={valgtSlot} udfoer={medRevision} /> : null}
      </div>
    </div>
  )
}
