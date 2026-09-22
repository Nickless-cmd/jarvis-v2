import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { hentNotifikationsValg, saetNotifikationsValg } from '../../lib/notifikationerApi'
import { SettingsState, SettingsActionError } from './SettingsState'

/** Brugerens ord for hver slags — ikke systemets. */
const NAVN: Record<string, string> = {
  approval: 'Godkendelser',
  question: 'Spørgsmål fra Jarvis',
  run_failed: 'Når noget går galt',
  run_done: 'Når et svar er klar',
  briefing: 'Morgenbriefing',
  reminder: 'Påmindelser',
  reach_out: 'Når Jarvis selv tager kontakt',
  initiative: 'Initiativer',
  wakeup: 'Planlagte opfølgninger',
  release: 'Ny app-version',
  incident: 'Hændelser i systemet',
  quota: 'Kvote opbrugt',
}

const KANALER: [string, string][] = [
  ['auto', 'Automatisk'],
  ['push', 'Altid på telefonen'],
  ['desktop', 'Kun på computeren'],
  ['ingen', 'Kun i feeden'],
]

export function NotifikationsValg({ config }: { config: ApiConfig | undefined }) {
  const [valg, setValg] = useState<Record<string, string> | null>(null)
  const [fejl, setFejl] = useState(false)
  const [gemFejl, setGemFejl] = useState('')

  const hent = () => {
    if (!config) return
    void hentNotifikationsValg(config)
      .then((d) => { setValg(d.valg); setFejl(false) })
      .catch(() => setFejl(true))
  }
  useEffect(hent, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  const skift = async (slags: string, kanal: string) => {
    if (!config || !valg) return
    const foer = valg[slags] ?? 'auto'
    setValg({ ...valg, [slags]: kanal })   // optimistisk
    setGemFejl('')
    try {
      const svar = await saetNotifikationsValg(config, slags, kanal)
      if (!svar.ok) {
        // Rul tilbage. Ellers stod der et valg der ikke var gemt, og man ville
        // tro telefonen var slaaet til.
        setValg((v) => (v ? { ...v, [slags]: foer } : v))
        setGemFejl(svar.fejl || 'Valget kunne ikke gemmes.')
      }
    } catch {
      setValg((v) => (v ? { ...v, [slags]: foer } : v))
      setGemFejl('Valget kunne ikke gemmes. Prøv igen.')
    }
  }

  if (fejl) {
    // Ikke SettingsState her: dens faste tekst er "Kunne ikke hente
    // ${label}." (aktiv). Denne flades egen ordlyd er passiv — "kunne ikke
    // hentes" — saa den ikke drukner i alle de andre "kunne ikke hente
    // X"-meldinger naar man har flere sektioner aabne paa samme side.
    return (
      <div className="settings-feedback error" role="alert">
        <p>Notifikations-valgene kunne ikke hentes.</p>
        <button type="button" onClick={hent}>Prøv igen</button>
      </div>
    )
  }
  if (!valg) return <SettingsState status="loading" label="notifikations-valgene" onRetry={() => {}} />

  return (
    <div className="settings-section">
      <h3>Hvad må afbryde dig</h3>
      <p className="settings-hint">
        Alt står i feeden under klokken. Her bestemmer du kun hvad der også når telefonen.
      </p>
      <SettingsActionError message={gemFejl} />
      {Object.keys(NAVN).filter((s) => s in valg).map((slags) => (
        <label key={slags} className="settings-row">
          <span>{NAVN[slags]}</span>
          <select aria-label={NAVN[slags]} value={valg[slags]}
                  onChange={(e) => void skift(slags, e.target.value)}>
            {KANALER.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
          </select>
        </label>
      ))}
    </div>
  )
}
