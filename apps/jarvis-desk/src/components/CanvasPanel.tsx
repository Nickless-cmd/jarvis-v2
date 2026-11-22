import { useContext, useEffect, useState } from 'react'
import { Link2, Save, Send, Sparkles } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import { SessionContext } from '../contexts/SessionContext'
import type { CanvasReference } from '../lib/inspectorTargets'
import { sendCanvas } from '../lib/canvasBus'
import {
  foreslaaFortsaettelse, listDokumenter, opdaterDokument, opretDokument, udgivDokument,
} from '../lib/dokumentApi'

/** Redigérbart dokument i sidepanelet.
 *
 *  Fire ting, og de er forskellige:
 *  - **Send til samtalen** lægger den rettede tekst ind som en besked (canvasBus).
 *  - **Gem** gør den varig i backend. Uden den levede canvas kun i panelet, og
 *    lukkede man det, var rettelserne væk (målt 22/11-2026: CanvasPanel havde
 *    nul API-kald).
 *  - **Udgiv** skriver den til brugerens filmappe og giver et kortlivet link —
 *    det er den delbare artefakt, ikke bare teksten i tråden.
 *  - **Foreslå** henter et tilbud på den næste sætning.
 *
 *  ## Hvorfor forslaget er en knap og ikke grå tekst
 *
 *  Bjørn 17/9-2026: «det kommer dumpende mens jeg skriver, det er virkelig
 *  træls». Et forslag der konkurrerer med hans egne ord er en afbrydelse; et
 *  forslag der venter på at blive spurgt er et tilbud. Derfor hentes det kun
 *  når han klikker, det står i sin egen boks under teksten, og det bliver
 *  først til tekst når han trykker Indsæt. Der findes ingen automatisk
 *  hentning under tastning.
 *
 *  Versionen følger med: to faner der redigerer samme dokument må ikke kunne
 *  overskrive hinanden i tavshed.
 */
export function CanvasPanel({
  canvas, config,
}: {
  canvas: CanvasReference
  config?: ApiConfig
}) {
  const sessionCtx = useContext(SessionContext)
  const sessionId = sessionCtx?.activeId ?? null

  const [tekst, setTekst] = useState(canvas.tekst)
  const [status, setStatus] = useState<'' | 'sendt' | 'ingen-samtale'>('')
  const [dokumentId, setDokumentId] = useState<string | null>(null)
  const [version, setVersion] = useState(0)
  const [gemmer, setGemmer] = useState(false)
  const [gemt, setGemt] = useState<'' | 'ok' | 'fejl'>('')
  const [udgivelse, setUdgivelse] = useState<string>('')
  const [forslag, setForslag] = useState('')
  const [henterForslag, setHenterForslag] = useState(false)
  const [forslagFejl, setForslagFejl] = useState(false)

  // Find et dokument med samme titel i samtalen, så panelet genåbner det man
  // redigerede i stedet for at lave en ny kopi hver gang.
  useEffect(() => {
    let afbrudt = false
    if (!config || !sessionId) return
    listDokumenter(config, sessionId)
      .then((alle) => {
        if (afbrudt) return
        const fundet = alle.find((d) => d.titel === canvas.titel)
        if (fundet) {
          setDokumentId(fundet.id)
          setVersion(fundet.version)
          setTekst(fundet.tekst)
        }
      })
      .catch(() => { /* panelet virker stadig uden backend; Gem viser fejlen */ })
    return () => { afbrudt = true }
  }, [config, sessionId, canvas.titel])

  const aendret = tekst !== canvas.tekst
  const kanGemme = !!config && !!sessionId && tekst.trim() !== '' && !gemmer

  const send = () => {
    setStatus(sendCanvas({ titel: canvas.titel, tekst }) ? 'sendt' : 'ingen-samtale')
  }

  const gem = async () => {
    if (!config || !sessionId) return
    setGemmer(true)
    setGemt('')
    try {
      if (dokumentId) {
        const opdateret = await opdaterDokument(config, dokumentId, tekst, version)
        setVersion(opdateret.version)
      } else {
        const nyt = await opretDokument(config, sessionId, canvas.titel, tekst)
        setDokumentId(nyt.id)
        setVersion(nyt.version)
      }
      setGemt('ok')
    } catch {
      // En version-konflikt eller et netværksfejl skal SES. En tavs «gemt»
      // ville betyde at brugeren lukker panelet på en ændring der ikke findes.
      setGemt('fejl')
    } finally {
      setGemmer(false)
    }
  }

  const udgiv = async () => {
    if (!config || !dokumentId) return
    try {
      const u = await udgivDokument(config, dokumentId)
      setUdgivelse(u.url)
    } catch {
      setGemt('fejl')
    }
  }

  const foreslaa = async () => {
    if (!config || !dokumentId) return
    setHenterForslag(true)
    setForslagFejl(false)
    try {
      const f = await foreslaaFortsaettelse(config, dokumentId)
      setForslag(f)
      // Et tomt svar er et gyldigt svar (intet at fortsætte endnu), men det
      // skal ikke se ud som om knappen ikke virkede.
      if (!f) setForslagFejl(true)
    } catch {
      setForslagFejl(true)
    } finally {
      setHenterForslag(false)
    }
  }

  const indsaetForslag = () => {
    if (!forslag) return
    const skilletegn = tekst === '' || /[\s\n]$/.test(tekst) ? '' : ' '
    setTekst(`${tekst}${skilletegn}${forslag}`)
    setForslag('')
    setGemt('')
  }

  return (
    <div className="artifact-body canvas-flade">
      <textarea
        className="canvas-tekst"
        aria-label={`Canvas: ${canvas.titel}`}
        value={tekst}
        spellCheck={false}
        onChange={(e) => { setTekst(e.target.value); setStatus(''); setGemt('') }}
      />
      {forslag && (
        <div className="canvas-forslag" data-testid="canvas-forslag">
          <span className="canvas-forslag-tekst">{forslag}</span>
          <button type="button" className="canvas-send" onClick={indsaetForslag}>
            Indsæt
          </button>
          <button type="button" className="canvas-send" onClick={() => setForslag('')}>
            Luk
          </button>
        </div>
      )}
      {forslagFejl && !forslag && (
        <div className="canvas-status canvas-fejl" role="status">
          Intet forslag endnu — skriv lidt mere, eller prøv igen.
        </div>
      )}
      <div className="canvas-bund">
        <button type="button" className="canvas-send" disabled={tekst.trim() === ''} onClick={send}>
          <Send size={13} /> Send til samtalen
        </button>
        <button type="button" className="canvas-send" disabled={!kanGemme} onClick={gem}>
          <Save size={13} /> {gemmer ? 'Gemmer…' : 'Gem'}
        </button>
        <button
          type="button"
          className="canvas-send"
          disabled={!config || !dokumentId || henterForslag}
          title={dokumentId ? 'Hent et tilbud på den næste sætning' : 'Gem først'}
          onClick={foreslaa}
        >
          <Sparkles size={13} /> {henterForslag ? 'Tænker…' : 'Foreslå'}
        </button>
        <button
          type="button"
          className="canvas-send"
          disabled={!config || !dokumentId}
          title={dokumentId ? 'Udgiv med et delbart link' : 'Gem først'}
          onClick={udgiv}
        >
          <Link2 size={13} /> Udgiv
        </button>
        {status === 'sendt' && <span className="canvas-status">Sendt{aendret ? ' (med dine rettelser)' : ''}.</span>}
        {status === 'ingen-samtale' && (
          <span className="canvas-status canvas-fejl" role="alert">Åbn en chat-samtale for at sende — intet blev sendt.</span>
        )}
        {gemt === 'ok' && <span className="canvas-status">Gemt (v{version}).</span>}
        {gemt === 'fejl' && (
          <span className="canvas-status canvas-fejl" role="alert">
            Ikke gemt — hent dokumentet igen og prøv på ny.
          </span>
        )}
        {udgivelse && (
          <span className="canvas-status">
            Udgivet: <code>{udgivelse}</code>
          </span>
        )}
      </div>
    </div>
  )
}
