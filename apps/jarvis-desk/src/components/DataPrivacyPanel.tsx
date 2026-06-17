import { useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { exportMyData, downloadJson } from '../lib/accountApi'

/** Data & privatliv-oplysning (GDPR-transparens + Googles "prominent disclosure").
 *  Navngiver præcist hvilke data appen rører + en data-eksport-knap (Art. 20). */
export function DataPrivacyPanel({ config }: { config?: ApiConfig }) {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const onExport = async () => {
    if (!config || busy) return
    setBusy(true)
    setMsg(null)
    try {
      const data = await exportMyData(config)
      downloadJson(data, 'jarvis-mine-data.json')
      setMsg('Dine data blev downloadet ✓')
    } catch {
      setMsg('Kunne ikke hente data — prøv igen.')
    } finally {
      setBusy(false)
      setTimeout(() => setMsg(null), 4000)
    }
  }

  return (
    <section className="data-privacy">
      <h3>Data &amp; privatliv</h3>
      <p className="data-privacy-intro">
        Jarvis er bygget lokal-først. Her er præcist hvad der behandles, og hvor.
      </p>

      <table className="data-privacy-table">
        <thead>
          <tr><th>Data</th><th>Hvor</th><th>Cloud?</th></tr>
        </thead>
        <tbody>
          <tr><td>Chat-historik</td><td>Din server (jarvis.db)</td><td>Nej</td></tr>
          <tr><td>Hukommelse/noter</td><td>Din server, per-bruger</td><td>Nej</td></tr>
          <tr><td>Model-prompts</td><td>Sendes til valgt model</td><td>Kun ved cloud-model</td></tr>
          <tr><td>API-nøgler/tokens</td><td>Server-config (0600) + app-keychain</td><td>Nej</td></tr>
        </tbody>
      </table>

      <h4>Forbundne apps (connectors)</h4>
      <p>
        Når du forbinder en app, gemmes adgangen <strong>krypteret pr. bruger</strong> og
        bruges kun til de funktioner du ser i appen. Vi bruger aldrig dine data til
        modeltræning, og adgangen kan til enhver tid afbrydes i Marketplace (token slettes).
      </p>
      <ul className="data-privacy-scopes">
        <li><strong>Google (Gmail/Kalender/Drive/Docs/Sheets/Slides):</strong> læseadgang +
          afsendelse/oprettelse kun efter din godkendelse pr. handling.</li>
        <li><strong>GitHub:</strong> dine egne issues/PRs.</li>
        <li><strong>Hugging Face:</strong> offentlig modelsøgning.</li>
      </ul>

      <h4>Dine rettigheder (GDPR)</h4>
      <ul className="data-privacy-rights">
        <li>Indsigt og dataportabilitet — hent dine data som JSON nedenfor.</li>
        <li>Sletning — afbryd en connector for at fjerne dens token; kontakt admin for fuld sletning.</li>
        <li>Tilbagekald — du godkender hver handling der sender eller ændrer noget.</li>
      </ul>
      {config && (
        <div className="data-privacy-export">
          <button type="button" onClick={() => void onExport()} disabled={busy}>
            {busy ? 'Henter…' : 'Download mine data (JSON)'}
          </button>
          {msg && <span className="data-privacy-export-msg">{msg}</span>}
        </div>
      )}
      <p className="data-privacy-note">
        Du taler med en AI. Svar kan indeholde fejl — vurdér selv vigtige beslutninger.
      </p>
    </section>
  )
}
