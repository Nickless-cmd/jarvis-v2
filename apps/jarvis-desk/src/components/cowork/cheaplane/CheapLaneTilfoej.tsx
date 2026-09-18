/**
 * Tilføj en udbyder eller en model — altid i cheap lane.
 *
 * Der er med vilje INGEN lane-vælger. Speccen siger det ligeud: «Adding a
 * provider creates its model directly in the cheap lane». En vælger her ville
 * være en måde at komme til at oprette noget i den synlige lane fra et panel
 * der hedder «cheap» — og den synlige lane er Bjørns egen.
 *
 * ## Nøglen
 *
 * Feltet er et password-felt og ryddes i samme øjeblik formen er sendt. Den
 * gemmes i auth-profilen, kommer aldrig tilbage i et svar, og må derfor heller
 * ikke ligge i en React-state længere end den ene indsendelse. Feltet er
 * valgfrit: en model kan tilføjes til en udbyder der allerede har sin nøgle.
 */
import { useState } from 'react'
import type { Udfoer } from './CheapLaneControls'

export function CheapLaneTilfoej({ udfoer }: { udfoer: Udfoer }) {
  const [åben, setÅben] = useState(false)
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [profil, setProfil] = useState('')
  const [noegle, setNoegle] = useState('')
  const [fejl, setFejl] = useState('')
  const [kvittering, setKvittering] = useState('')
  const [kører, setKører] = useState(false)

  async function send() {
    if (!provider.trim() || !model.trim()) {
      setFejl('Både udbyder og model skal udfyldes.')
      return
    }
    setFejl(''); setKvittering(''); setKører(true)
    try {
      await udfoer({
        action: 'provider.add',
        target: provider.trim(),
        reason: 'tilføjet fra kontrolcentret',
        parameters: {
          provider: provider.trim(),
          model: model.trim(),
          lane: 'cheap',           // ALTID cheap — se modulets docstring
          auth_mode: 'api_key',
          auth_profile: profil.trim() || provider.trim(),
          base_url: baseUrl.trim(),
          api_key: noegle,
        },
      })
      setKvittering(`${provider.trim()} / ${model.trim()} er tilføjet i cheap lane.`)
      setProvider(''); setModel(''); setBaseUrl(''); setProfil('')
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'kunne ikke tilføje')
    } finally {
      // Nøglen ryddes UANSET udfald: den må ikke blive liggende i en state
      // efter at formen er sendt, heller ikke når noget gik galt.
      setNoegle('')
      setKører(false)
    }
  }

  if (!åben) {
    return (
      <button type="button" className="cl-handling" onClick={() => setÅben(true)}>
        Tilføj udbyder
      </button>
    )
  }

  return (
    <div className="cl-tilfoej">
      <p className="cl-forklaring-overskrift">Ny udbyder eller model — oprettes i cheap lane</p>
      <div className="cl-tilfoej-felter">
        <label>Udbyder
          <input value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="fx groq" />
        </label>
        <label>Model
          <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="fx llama-3.3-70b" />
        </label>
        <label>Base-URL
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://…/v1" />
        </label>
        <label>Auth-profil
          <input value={profil} onChange={(e) => setProfil(e.target.value)} placeholder="samme som udbyder" />
        </label>
        <label>API-nøgle (valgfri)
          <input type="password" value={noegle} onChange={(e) => setNoegle(e.target.value)}
                 autoComplete="new-password"
                 placeholder="tom = rør ikke den nøgle der allerede er" />
        </label>
      </div>
      {fejl ? <p className="cl-handling-fejl" role="alert">{fejl}</p> : null}
      {kvittering ? <p className="cl-kvittering">{kvittering}</p> : null}
      <div className="cl-dialog-knapper">
        <button type="button" onClick={() => { setÅben(false); setNoegle('') }}>Luk</button>
        <button type="button" className="cl-primaer" disabled={kører} onClick={() => void send()}>
          {kører ? 'Tilføjer…' : 'Tilføj'}
        </button>
      </div>
    </div>
  )
}
