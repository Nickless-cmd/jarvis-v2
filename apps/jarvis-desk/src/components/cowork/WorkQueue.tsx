import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock, Eye, Loader2 } from 'lucide-react'
import { PromptSammensaetning } from './PromptSammensaetning'
import type { ApiConfig } from '../../lib/api'
import { useWorkQueue } from '../../hooks/useWorkQueue'
import type { KoeIndslag } from '../../hooks/useWorkQueue'
import type { KoeSpand } from '../../lib/coworkApi'

/** Rækkefølgen er prioritet: det der venter på dig står øverst, historik nederst. */
const SPANDE: { key: KoeSpand; titel: string; ikon: typeof Clock }[] = [
  { key: 'venter_paa_mig', titel: 'Venter på dig', ikon: Clock },
  { key: 'aktiv', titel: 'Kører nu', ikon: Loader2 },
  { key: 'til_gennemsyn', titel: 'Til gennemsyn', ikon: Eye },
  { key: 'fejlet', titel: 'Fejlet', ikon: AlertTriangle },
  { key: 'faerdig', titel: 'Færdig', ikon: CheckCircle2 },
]

/**
 * Work Queue — ét sted for alt der venter, kører eller er faldet.
 *
 * Codex' punkt 2: approvals, runs og tasks lå spredt i flere paneler, så man
 * skulle vide HVOR man skulle kigge for at vide hvad der foregik.
 *
 * Spandene er sorteret efter hvad man kan GØRE, ikke efter hvor tingene kommer
 * fra. «Venter på dig» øverst, fordi det er det eneste der blokerer noget.
 * «Færdig» er foldet sammen som udgangspunkt — historik skal kunne nås, ikke
 * fylde.
 */
export function WorkQueue({ config }: { config: ApiConfig | undefined }) {
  const { spande, henter, delvis, venter } = useWorkQueue(config)
  const [foldetUd, setFoldetUd] = useState<Record<string, boolean>>({ faerdig: false })

  if (henter) return <div className="wq-tom">Henter…</div>

  const alt = SPANDE.reduce((n, s) => n + spande[s.key].length, 0)

  return (
    <div className="work-queue">
      <div className="wq-head">
        <h3>Arbejde</h3>
        {venter > 0 && <span className="wq-badge">{venter} venter</span>}
      </div>

      {/* En delvis fejl skjuler ikke resten: står den ene kilde af, vises den
          anden stadig. En tom kø ville ligne at intet foregik. */}
      {delvis && <div className="wq-delvis">{delvis} — resten vises</div>}

      {alt === 0 && <div className="wq-tom">Intet i kø. Ingenting venter på dig.</div>}

      {SPANDE.map(({ key, titel, ikon: Ikon }) => {
        const rows = spande[key]
        if (rows.length === 0) return null
        const åben = foldetUd[key] ?? true
        return (
          <section key={key} className={`wq-spand wq-${key}`}>
            <button
              type="button"
              className="wq-spand-head"
              aria-expanded={åben}
              onClick={() => setFoldetUd((f) => ({ ...f, [key]: !åben }))}
            >
              <Ikon size={13} className={key === 'aktiv' ? 'wq-spin' : undefined} />
              <span>{titel}</span>
              <span className="wq-antal">{rows.length}</span>
            </button>
            {åben && (
              <ul className="wq-liste">
                {rows.slice(0, 12).map((r) => <Raekke key={r.id} indslag={r} config={config} />)}
                {rows.length > 12 && (
                  <li className="wq-flere">+{rows.length - 12} mere</li>
                )}
              </ul>
            )}
          </section>
        )
      })}
    </div>
  )
}

function Raekke({ indslag, config }: { indslag: KoeIndslag; config?: ApiConfig }) {
  const [aaben, setAaben] = useState(false)
  // Kun kørsler har en prompt-sammensætning; godkendelser har ingen tur bag sig.
  const runId = indslag.kilde === 'run'
    ? String((indslag.raa as { run_id?: string }).run_id ?? '')
    : ''

  return (
    <li className="wq-raekke">
      {runId ? (
        <button
          type="button"
          className="wq-titel wq-titel-knap"
          title="Hvad byggede han svaret på?"
          aria-expanded={aaben}
          onClick={() => setAaben((v) => !v)}
        >
          {indslag.titel}
        </button>
      ) : (
        <span className="wq-titel" title={indslag.titel}>{indslag.titel}</span>
      )}
      {indslag.detalje && <span className="wq-detalje">{indslag.detalje}</span>}
      {aaben && runId && (
        <div className="wq-udfoldet">
          <PromptSammensaetning config={config} runId={runId} />
        </div>
      )}
    </li>
  )
}
