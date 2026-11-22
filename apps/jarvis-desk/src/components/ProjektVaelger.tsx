import { useCallback, useEffect, useState } from 'react'
import { FolderOpen } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import {
  bindSessionProjekt, hentSessionProjekt, listProjekter, type Projekt,
} from '../lib/projektApi'

/** Binder den aktuelle session til et projekt (varig kontekst) og viser
 *  projektets materiale. Alle tilstande er synlige: indlæser, fejl og tom liste
 *  er forskellige ting, og en fejl må aldrig se ud som «ingen projekter». */
export function ProjektVaelger({
  config, sessionId, getSessionId, onChange,
}: {
  config: ApiConfig
  /** Sessionen der VISES. Null = ingen endnu; den oprettes først ved et valg. */
  sessionId: string | null
  getSessionId: () => Promise<string>
  onChange: (projectId: string | null) => void
}) {
  const [aaben, setAaben] = useState(false)
  const [projekter, setProjekter] = useState<Projekt[] | null>(null)
  const [valgt, setValgt] = useState<string | null>(null)
  const [fejl, setFejl] = useState('')
  const [optaget, setOptaget] = useState(false)

  // Den eksisterende binding for sessionen. Fejl vises — en tavs null ville
  // påstå «intet projekt» om en session der måske HAR et.
  useEffect(() => {
    let levende = true
    setValgt(null)
    onChange(null)
    if (!sessionId) return
    hentSessionProjekt(config, sessionId)
      .then((id) => { if (levende) { setValgt(id); onChange(id) } })
      .catch((e: unknown) => { if (levende) setFejl(`Kunne ikke hente projekt: ${e instanceof Error ? e.message : String(e)}`) })
    return () => { levende = false }
  }, [config, sessionId, onChange])

  const aabn = useCallback(() => {
    const ny = !aaben
    setAaben(ny)
    if (!ny || projekter) return
    setFejl('')
    listProjekter(config)
      .then(setProjekter)
      .catch((e: unknown) => setFejl(`Kunne ikke hente projekter: ${e instanceof Error ? e.message : String(e)}`))
  }, [aaben, projekter, config])

  const vaelg = useCallback(async (id: string | null) => {
    setOptaget(true)
    setFejl('')
    try {
      const sid = await getSessionId()
      await bindSessionProjekt(config, sid, id)
      setValgt(id)
      onChange(id)
    } catch (e) {
      // Bindingen er IKKE gemt — vis det i stedet for at lade chippen skifte.
      setFejl(`Kunne ikke binde projekt: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setOptaget(false)
    }
  }, [config, getSessionId, onChange])

  const aktivt = projekter?.find((p) => p.id === valgt)
  return (
    <div className="projekt-vaelger">
      <button type="button" className={`projekt-chip${valgt ? ' bundet' : ''}`}
              aria-expanded={aaben} aria-haspopup="listbox" onClick={aabn}>
        <FolderOpen size={13} />
        <span>{valgt ? (aktivt?.navn ?? valgt) : 'Projekt'}</span>
      </button>
      {aaben && (
        <div className="projekt-menu" role="listbox" aria-label="Projekter">
          {fejl && <div className="projekt-fejl" role="alert">{fejl}</div>}
          {!projekter && !fejl && <div className="projekt-tom">Henter projekter…</div>}
          {projekter && projekter.length === 0 && <div className="projekt-tom">Ingen projekter endnu.</div>}
          {projekter && (
            <>
              <button type="button" role="option" aria-selected={valgt === null} disabled={optaget}
                      className={`projekt-rk${valgt === null ? ' valgt' : ''}`}
                      onClick={() => { void vaelg(null) }}>Intet projekt</button>
              {projekter.map((p) => (
                <button key={p.id} type="button" role="option" aria-selected={p.id === valgt} disabled={optaget}
                        className={`projekt-rk${p.id === valgt ? ' valgt' : ''}`}
                        onClick={() => { void vaelg(p.id) }}>
                  <span className="projekt-navn">{p.navn}</span>
                  {p.beskrivelse && <span className="projekt-besk">{p.beskrivelse}</span>}
                </button>
              ))}
            </>
          )}
          {aktivt && (
            <div className="projekt-materiale">
              <div className="projekt-materiale-hoved">Materiale</div>
              {aktivt.materiale.length === 0
                ? <div className="projekt-tom">Projektet har intet materiale.</div>
                : aktivt.materiale.map((m) => <div key={m.navn} className="projekt-fil">{m.navn}</div>)}
            </div>
          )}
        </div>
      )}
      {!aaben && fejl && <span className="projekt-fejl" role="alert">{fejl}</span>}
    </div>
  )
}
