import { useCallback, useEffect, useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import {
  getTidsserie, refreshPool, type TidsserieSpand,
} from '../../../lib/cheapLaneApi'
import { useCheapLaneStore } from '../../../lib/cheapLaneStore'
import { CheapLaneOverview } from './CheapLaneOverview'
import { CheapLaneCapacity } from './CheapLaneCapacity'
import { CheapLaneProviders } from './CheapLaneProviders'
import { CheapLaneInspector } from './CheapLaneInspector'
import { CheapLaneBalancer } from './CheapLaneBalancer'
import { CheapLaneLogs } from './CheapLaneLogs'
import { CheapLaneDiagnostics } from './CheapLaneDiagnostics'
import { CheapLaneSettings } from './CheapLaneSettings'
import { CheapLaneTilfoej } from './CheapLaneTilfoej'
import {
  udfoerKontrol, simulerRute, getLogs, getLogDetalje, getRevisioner,
  type Revision,
} from '../../../lib/cheapLaneApi'

/**
 * Cheap Lane — hele lanen på én flade.
 *
 * Bjørn 16/9-2026: «cheap lane er især vigtigt for jeg ander intet om hvordan
 * cheap lane eller load_balanceren klarer sig».
 *
 * De to kilder svarer på hvert sit spørgsmål, og det er derfor de har hver sin
 * fane frem for at blive blandet til ét tal:
 *
 *   Puljen     NU — hvilke slots kan vælges i dette øjeblik, hvem er i køling
 *   Historik   FORLØBET — 90.000 kald med udfald, latens og pris
 *
 * Handlingerne rammer også to forskellige steder, og forskellen står på
 * knapperne: et slot «pauses» i balancerens egen tilstand, mens en model
 * slås fra i registret og derfor bliver væk efter en genstart.
 */
type Fane = 'oversigt' | 'kapacitet' | 'pulje' | 'udbydere' | 'logs' | 'diagnose'

const FANER: { id: Fane; label: string }[] = [
  { id: 'oversigt', label: 'Oversigt' },
  { id: 'kapacitet', label: 'Kapacitet' },
  { id: 'pulje', label: 'Puljen nu' },
  { id: 'udbydere', label: 'Udbydere' },
  { id: 'logs', label: 'Kald' },
  { id: 'diagnose', label: 'Diagnose' },
]

const VINDUER = [1, 6, 24, 72, 168]



export function CheapLanePanel({ config }: { config?: ApiConfig }) {
  const [fane, setFane] = useState<Fane>('oversigt')
  const [timer, setTimer] = useState(24)
  const [serie, setSerie] = useState<TidsserieSpand[]>([])
  const [henter, setHenter] = useState(false)
  // Oversigt og kapacitet kommer fra ÉT snapshot med Centrals strøm som puls.
  // De øvrige faner henter stadig hver for sig indtil opgave 11-12 flytter dem.
  const butik = useCheapLaneStore(config, timer)
  // Inspektøren er DELT: to åbne detaljer ville lade brugeren se to ting og
  // tro det var den samme. `åbnetFra` bærer rækken fokus skal tilbage til.
  const [valgt, setValgt] = useState<{ provider: string; model: string } | null>(null)
  const [åbnetFra, setÅbnetFra] = useState<HTMLElement | null>(null)
  const [revisioner, setRevisioner] = useState<Revision[]>([])
  const [visIndstillinger, setVisIndstillinger] = useState(false)
  // Tidsseriens fejl hoerer til GRAFEN, ikke til panelets banner: samme
  // besked to steder er stoej, og banneret er til det der rammer hele fladen.
  const [serieFejl, setSerieFejl] = useState('')


  // Kun tidsserien hentes ved siden af snapshotet: dashboardet baerer summer
  // (kald, tokens, fejl), ikke FORLOEBET, og grafen skal vise et forloeb.
  // Alt andet — balancer, udbydere, kapacitet, diagnose — kommer fra det ene
  // snapshot, saa fladen ikke igen viser fire kilder fra fire tidspunkter.
  const hent = useCallback(async () => {
    if (!config) return
    setHenter(true)
    try {
      const t = await getTidsserie(config, timer, timer <= 6 ? 15 : 60)
      setSerie(t.spand ?? [])
      setSerieFejl('')
    } catch {
      setSerieFejl('tidsserien kunne ikke hentes')
    } finally {
      setHenter(false)
    }
  }, [config, timer])

  useEffect(() => { void hent() }, [hent])
  useEffect(() => {
    if (fane !== 'diagnose' || !config) return
    getRevisioner(config, 100).then((r) => setRevisioner(r.items ?? [])).catch(() => setRevisioner([]))
  }, [fane, config])

  // Hver kontrol-handling er en skrivning med revisionsspor. Efter den skal
  // billedet hentes igen — ellers viser skærmen tilstanden FØR handlingen.
  const kontrol = useCallback(async (k: { action: string; target: string; reason?: string;
    expected_revision?: string; parameters?: Record<string, unknown> }) => {
    if (!config) throw new Error('ingen forbindelse')
    const svar = await udfoerKontrol(config, k)
    butik.refresh()
    void hent()
    return svar
  }, [config, butik, hent])


  if (!config) return <div className="mc-tom">Ingen forbindelse til serveren.</div>


  return (
    <div className="mc cheaplane">
      <div className="mc-top">
        <h2>Cheap Lane</h2>
        <div className="mc-top-right">
          <select value={timer} onChange={(e) => setTimer(Number(e.target.value))}
                  aria-label="Tidsvindue">
            {VINDUER.map((v) => (
              <option key={v} value={v}>{v < 24 ? `${v} t` : `${v / 24} døgn`}</option>
            ))}
          </select>
          <span className={`cl-live cl-live-${butik.liveState}`} title={`Datastrøm: ${butik.liveState}`}>
            {butik.liveState === 'live' ? 'live' : butik.liveState === 'polling' ? 'poller' : butik.liveState}
          </span>
          <button type="button" onClick={() => { void hent(); butik.refresh() }} disabled={henter}>
            {henter ? 'Henter…' : 'Opdatér'}
          </button>
        </div>
      </div>

      <div className="mc-tabs">
        {FANER.map((f) => (
          <button key={f.id} type="button"
                  className={f.id === fane ? 'aktiv' : ''}
                  aria-pressed={f.id === fane}
                  onClick={() => setFane(f.id)}>
            {f.label}
          </button>
        ))}
      </div>

      {fane === 'oversigt' && (
        butik.snapshot
          ? <CheapLaneOverview snapshot={butik.snapshot} serie={serie.map((x) => ({
              start: x.tid, kald: x.kald, fejl: x.fejl, tokens: 0,
            }))}
              serieHenter={henter && !serie.length}
              serieFejl={serieFejl} />
          : <p className="cl-tom">{butik.error || 'Henter overblik…'}</p>
      )}

      {fane === 'kapacitet' && (
        <CheapLaneCapacity vinduer={butik.snapshot?.sections?.capacity?.data?.windows ?? []} />
      )}

      {fane === 'pulje' && (
        <>
          <p className="cl-note">
            Puljen er balancerens EGEN tilstand: en pause her er væk ved næste
            opbygning. Klik på et slot for at se hvorfor det får den vægt det får.
          </p>
          <CheapLaneBalancer
            slots={butik.snapshot?.sections?.balancer?.data?.slots ?? []}
            udfoer={kontrol}
            simuler={async (taskKind, skip) => {
              if (!config) throw new Error('ingen forbindelse')
              return simulerRute(config, taskKind, skip)
            }}
            genopbyg={async () => {
              if (!config) throw new Error('ingen forbindelse')
              const svar = await refreshPool(config)
              butik.refresh()
              return svar
            }}
          />
        </>
      )}

      {fane === 'udbydere' && (
        <div className="cl-med-inspektor">
          <div>
            <p className="cl-note">
              Her ændres <strong>registret</strong>. «Pause» er balancerens egen tilstand og
              er væk ved næste opbygning; «Deaktivér» overlever en genstart; «Fjern» kan ikke
              fortrydes. Hver ændring skrives i revisionssporet.
            </p>
            <CheapLaneTilfoej udfoer={kontrol} />
            <CheapLaneProviders
              registret={butik.snapshot?.sections?.providers?.data ?? null}
              udfoer={kontrol}
              onInspicer={(provider, model) => {
                setÅbnetFra(document.activeElement as HTMLElement | null)
                setValgt({ provider, model })
              }}
            />
          </div>
          {valgt && (
            <CheapLaneInspector
              titel={valgt.provider}
              undertitel={valgt.model}
              tilbageTil={åbnetFra}
              onLuk={() => setValgt(null)}
              felter={[
                { navn: 'Lane', vaerdi: 'cheap', maerkat: true },
                { navn: 'Status', vaerdi: (butik.snapshot?.sections?.providers?.data?.modeller ?? []).find(
                    (m) => m.provider === valgt.provider && m.model === valgt.model)?.enabled
                    ? 'aktiv' : 'slået fra' },
                { navn: 'Slots i puljen', vaerdi: String((butik.snapshot?.sections?.balancer?.data?.slots ?? []).filter(
                    (x) => x.provider === valgt.provider && x.model === valgt.model).length) },
              ]}
            />
          )}
        </div>
      )}

      {fane === 'logs' && config && (
        <CheapLaneLogs
          timer={timer}
          hentLogs={(f) => getLogs(config, f)}
          hentDetalje={(id) => getLogDetalje(config, id)}
          eksportUrl={(format) =>
            `${config.apiBaseUrl}/mc/cheap-lane/logs/export?format=${format}&hours=${timer}`}
        />
      )}

      {fane === 'diagnose' && (
        <>
          <CheapLaneDiagnostics
            diagnose={butik.snapshot?.sections?.diagnostics?.data ?? null}
            revisioner={revisioner}
            central={butik.snapshot?.sections?.central?.data ?? []}
            pakkeUrl={config
              ? `${config.apiBaseUrl}/mc/cheap-lane/diagnostics/export?hours=${timer}`
              : undefined}
          />
          <button type="button" className="cl-handling"
                  onClick={() => setVisIndstillinger((v) => !v)}>
            {visIndstillinger ? 'Skjul opbevaring' : 'Opbevaring'}
          </button>
          {visIndstillinger && (
            <CheapLaneSettings metadataDage={60} payloadDage={7} udfoer={kontrol} />
          )}
        </>
      )}

    </div>
  )
}
