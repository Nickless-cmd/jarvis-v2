import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Download, FileText, Loader2 } from 'lucide-react'
import { fetchBlobWithAuth, type ApiConfig } from '../../lib/api'
import type { FilReference } from '../../lib/inspectorTargets'
import { filAdresse, formatSize } from '../rich/AttachmentBlock'

/**
 * En fil Bjørn kan SE — ikke kun hente.
 *
 * ## Hvorfor den findes
 *
 * Målt 27/10-2026 (Bjørn): «mangler vi visningsflader i desk for de fleste af
 * disse ting?» Indtil da var enhver fil et download-kort. En PDF Jarvis selv
 * havde lavet kunne hentes, men ikke læses i appen — og et regneark kunne man
 * ikke engang se formen på.
 *
 * ## Hvad der kan vises, og hvad der ikke kan
 *
 * Chromium kan selv rendere billeder, video, PDF og tekst. Det er ikke et
 * spørgsmål om at bygge en renderer — det er et spørgsmål om at give den en
 * blob-URL. Office-formaterne (docx/xlsx/pptx) har ingen indbygget renderer i
 * nogen browser; dem viser vi derfor som metadata plus download, med en
 * ÆRLIG linje om hvorfor. En tom hvid rude ville se ud som en fejl i filen.
 *
 * ## Hvorfor blob og ikke et direkte src
 *
 * `/files/…` kræver `Authorization` (målt 12/9-2026: 401 uden token). En
 * `<iframe src="/files/x">` kan ikke bære en header, så PDF'en ville give
 * «unauthorized» på en fil der findes og er ens egen. Vi henter den derfor
 * selv med token og giver browseren en blob-URL i stedet.
 */
export function FilPreview({ fil, config }: { fil: FilReference; config?: ApiConfig }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [tekst, setTekst] = useState<string | null>(null)
  const [fejl, setFejl] = useState('')
  const [henter, setHenter] = useState(true)
  const [hentetMime, setHentetMime] = useState('')
  const [hentetStoerrelse, setHentetStoerrelse] = useState(0)
  const urls = useRef<string[]>([])

  const adresse = filAdresse({
    type: 'file',
    filename: fil.navn,
    url: fil.url,
    attachment_id: fil.attachment_id,
    mime_type: fil.mime_type,
  })
  const mime = String(fil.mime_type || '').toLowerCase()

  useEffect(() => {
    if (!config || !adresse) {
      setHenter(false)
      if (!adresse) setFejl('Filen har ingen adresse')
      return
    }
    let afbrudt = false
    setHenter(true)
    setFejl('')
    setBlobUrl(null)
    setTekst(null)

    fetchBlobWithAuth(config, adresse)
      .then(async (blob) => {
        if (afbrudt) return
        const type = blob.type || mime
        setHentetMime(type)
        setHentetStoerrelse(blob.size)
        // Tekst læses som tekst: en `<pre>` med indhold er mere brugbar end en
        // blob-URL der åbner en ny fane uden for panelet.
        //
        // ⚠️ IKKE `type.includes('xml')`: en .docx har typen
        // `…openxmlformats-officedocument.wordprocessingml.document`, så et
        // substring-tjek læste et Word-dokument som tekst og viste
        // «[object Blob]». Målt 27/10-2026 — den første udgave af denne fil
        // gjorde præcis det, og kun en test der kiggede på den RIGTIGE gren
        // fangede det.
        const erTekst = type.startsWith('text/')
          || type === 'application/json'
          || type.endsWith('+json')
          || type.endsWith('+xml')
        if (erTekst) {
          // `Blob.text()` findes i Chromium men ikke i ældre miljøer (jsdom
          // har den ikke — målt 27/10-2026: testen fik «blob.text is not a
          // function»). FileReader er reservevejen, ikke en anden adfærd.
          const laesTekst = async (b: Blob): Promise<string> => {
            if (typeof b.text === 'function') return b.text()
            return new Promise<string>((res, rej) => {
              const fr = new FileReader()
              fr.onload = () => res(String(fr.result ?? ''))
              fr.onerror = () => rej(fr.error)
              fr.readAsText(b)
            })
          }
          const t = await laesTekst(blob)
          if (!afbrudt) setTekst(t.length > 200_000 ? `${t.slice(0, 200_000)}\n\n… (afkortet)` : t)
          return
        }
        const url = URL.createObjectURL(blob)
        urls.current.push(url)
        if (!afbrudt) setBlobUrl(url)
        else URL.revokeObjectURL(url)
      })
      .catch((e) => { if (!afbrudt) setFejl(e instanceof Error ? e.message : 'kunne ikke hentes') })
      .finally(() => { if (!afbrudt) setHenter(false) })

    return () => {
      afbrudt = true
      for (const u of urls.current) URL.revokeObjectURL(u)
      urls.current = []
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adresse, config?.apiBaseUrl, config?.authToken])

  const effektivMime = hentetMime || mime
  const stoerrelse = formatSize(hentetStoerrelse || fil.size_bytes)

  const hent = () => {
    if (!blobUrl) return
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = fil.navn
    a.click()
  }

  if (henter) {
    return (
      <div className="artifact-body artifact-empty">
        <Loader2 size={16} className="spin" /> Henter {fil.navn} …
      </div>
    )
  }

  if (fejl) {
    return (
      <div className="artifact-body artifact-empty">
        <AlertCircle size={16} /> {fil.navn}: {fejl}
      </div>
    )
  }

  if (tekst !== null) {
    return (
      <div className="artifact-body fil-preview-tekst">
        <pre>{tekst}</pre>
      </div>
    )
  }

  if (blobUrl && effektivMime.startsWith('image/')) {
    return (
      <div className="artifact-body fil-preview-flade">
        <img src={blobUrl} alt={fil.navn} className="fil-preview-billede" />
      </div>
    )
  }

  if (blobUrl && effektivMime.startsWith('video/')) {
    return (
      <div className="artifact-body fil-preview-flade">
        <video src={blobUrl} controls className="fil-preview-video" />
      </div>
    )
  }

  if (blobUrl && effektivMime === 'application/pdf') {
    return (
      <div className="artifact-body fil-preview-flade fil-preview-pdf">
        <iframe src={blobUrl} title={fil.navn} />
      </div>
    )
  }

  // Office- og andre formater: Chromium har ingen renderer for dem. Vi siger
  // det højt i stedet for at vise en tom rude der ligner en ødelagt fil.
  return (
    <div className="artifact-body fil-preview-meta">
      <FileText size={28} />
      <div className="fil-preview-navn">{fil.navn}</div>
      <div className="fil-preview-linje">
        {effektivMime || 'ukendt type'}{stoerrelse ? ` · ${stoerrelse}` : ''}
      </div>
      <div className="fil-preview-linje fil-preview-note">
        Dette format kan ikke vises i panelet — kun hentes.
      </div>
      {blobUrl ? (
        <button type="button" className="fil-preview-hent" onClick={hent}>
          <Download size={14} /> Hent filen
        </button>
      ) : null}
    </div>
  )
}
