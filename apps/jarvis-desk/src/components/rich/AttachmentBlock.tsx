import { useEffect, useState } from 'react'
import { AlertCircle, AppWindow, Download, ExternalLink, FileText, Loader2 } from 'lucide-react'
import { useSettings } from '../../hooks/useSettings'
import { absolutApiUrl, downloadBlob, fetchBlobWithAuth, hentSigneretFilLink, type ApiConfig } from '../../lib/api'
import { KlikbartBillede } from './BilledLightbox'
import { prepareExternalWindow } from '../../lib/host'

/**
 * En fil Jarvis har lagt ud — eller et gemt billede.
 *
 * ## Hvorfor den findes
 *
 * Blokken bærer kun en REFERENCE. Både `/files/{navn}` og `/attachments/...`
 * kræver godkendelse (målt 12/9-2026: 401 uden `Authorization`), så et
 * almindeligt link eller et `<img src>` ville give «unauthorized» på en fil der
 * findes og er ens egen. Vi henter den derfor selv med token og gemmer den
 * under dens rigtige navn.
 *
 * ## De to slags referencer
 *
 *   - `url`          — en fil Jarvis selv udgav med `publish_file` (`/files/…`)
 *   - `attachment_id` — en upload eller et genereret billede (`/attachments/…`)
 *
 * En udgivet fil har ALDRIG et attachment_id. Det er præcis derfor
 * `foldToolResults` tidligere droppede den: typen fandtes ikke i kæden, og
 * filen nåede aldrig skærmen (målt 15/9-2026 på et regneark der skulle leveres
 * i chatten). Spejler mobilens `MessageAttachments` — samme kontrakt.
 *
 * ## De tre handlinger (Bjørn 4/10-2026)
 *
 * «man bør kunne vælge at åbne i desk browser eller i egen browser eller
 * download fil.» De tre har tre forskellige veje, og det er ikke tre knapper
 * til samme ting:
 *
 *   - **Jarvis' browser** får den absolutte adresse. Electron-main injicerer
 *     `Authorization` på API'ets oprindelse (`jarvisBrowser.saetApiAuth`), så
 *     webvisningen henter som en autentificeret klient.
 *   - **Egen browser** kan ikke bære en header. Den får et kortlivet signeret
 *     link fra `POST /files/link` — 60 sekunder, bundet til netop det filnavn.
 *   - **Download** henter med token og gemmer. Den vej er uændret; den var
 *     bare den eneste der fandtes.
 *
 * De to første gælder KUN en udgivet fil (`/files/…`). En vedhæftning ligger
 * på `/attachments/…`, hvor signeringen ikke rækker — den beholder derfor
 * download alene frem for at få to knapper der giver 401.
 *
 * ## Formen
 *
 * En flad række, ikke en chip. `raekkevisning.css` siger det selv: «INGEN
 * baggrund, ingen ramme … i hele samtalen findes kun to malede flader: siden
 * og brugerens boble.» Chippen stammede fra `.paste-ref-chip`, som er ældre
 * end rækkevisningen og aldrig blev flyttet med — den var husets tredje
 * malede flade.
 */

/** Den slags blokke denne komponent kan vise. */
export interface VedhaefningsBlok {
  type: 'image' | 'file' | 'video'
  filename?: string
  url?: string
  attachment_id?: string
  mime_type?: string
  size_bytes?: number
}

/** Hvilken adresse hører blokken til? Spejler mobilens `blokUrl`. */
export function filAdresse(block: VedhaefningsBlok): string {
  const direkte = String(block.url || '').trim()
  if (direkte) return direkte
  const id = String(block.attachment_id || '').trim()
  if (!id) return ''
  // `/attachments/{id}` kender KUN denne sessions registry og duer derfor
  // ikke til noget der skal overleve reload. `/image/` og `/media/` slaar op i
  // DB'en og er user-scopede; `/media/` er samme kode under et aerligt navn,
  // saa en video ikke skal hentes fra en adresse der hedder «image».
  if (block.type === 'image') return `/attachments/image/${encodeURIComponent(id)}`
  if (block.type === 'video') return `/attachments/media/${encodeURIComponent(id)}`
  return `/attachments/${encodeURIComponent(id)}`
}

/** 1536 → «1,5 kB». Dansk komma — samme regel som mobilen. */
export function formatSize(bytes?: number): string {
  if (typeof bytes !== 'number' || !(bytes > 0)) return ''
  if (bytes < 1024) return `${bytes} B`
  const units = ['kB', 'MB', 'GB']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i++
  }
  const rounded = Math.round(value * 10) / 10
  const text = Number.isInteger(rounded) ? String(rounded) : String(rounded).replace('.', ',')
  return `${text} ${units[i]}`
}

export function AttachmentBlock({ block, onImageSelect, imageClassName }: {
  block: VedhaefningsBlok
  onImageSelect?: () => void
  imageClassName?: string
}) {
  const { settings } = useSettings()
  const config: ApiConfig | null = settings
    ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    : null

  const adresse = filAdresse(block)
  const navn = String(block.filename || (block.type === 'image' ? 'billede' : 'fil'))

  // Billeder: hentes til en object-URL og vises som flade. Filer: hentes ved
  // klik og gemmes. To spor, fordi man SER et billede og GEMMER en fil.
  const [billedeUrl, setBilledeUrl] = useState<string | null>(null)
  const [henter, setHenter] = useState(false)
  const [fejl, setFejl] = useState(false)

  useEffect(() => {
    if (block.type !== 'image' || !config || !adresse) return
    let afbrudt = false
    let lavet: string | null = null
    setHenter(true)
    setFejl(false)
    fetchBlobWithAuth(config, adresse)
      .then((blob) => {
        if (afbrudt) return
        lavet = URL.createObjectURL(blob)
        setBilledeUrl(lavet)
      })
      .catch(() => { if (!afbrudt) setFejl(true) })
      .finally(() => { if (!afbrudt) setHenter(false) })
    return () => {
      afbrudt = true
      if (lavet) URL.revokeObjectURL(lavet)
    }
    // `adresse` og `config` er de eneste indgange der ændrer hvad der hentes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adresse, block.type, settings])

  if (block.type === 'image') {
    if (fejl) return <span className="attachment-fejl"><AlertCircle size={14} /> {navn} kunne ikke hentes</span>
    if (!billedeUrl) return <span className="attachment-fejl">{henter ? <Loader2 size={14} className="spin" /> : null} {navn}</span>
    // Klik åbner fuld størrelse (Bjørn 20/9-2026). Formen kommer fra
    // `.attachment-image` — men uden `object-fit: cover`, som KLIPPEDE
    // kanterne af ens eget billede.
    return <KlikbartBillede className={imageClassName || 'attachment-image'} src={billedeUrl} alt={navn} onSelect={onImageSelect} />
  }

  const stoerrelse = formatSize(block.size_bytes)

  // Kun en UDGIVET fil kan åbnes. En vedhæftning ligger på `/attachments/…`,
  // og hverken browser-injektionen eller signeringen dækker den adresse —
  // to knapper der gav 401 ville være værre end ingen.
  const udgivetNavn = adresse.startsWith('/files/')
    ? decodeURIComponent(adresse.slice('/files/'.length).split('?')[0] || '')
    : ''
  const kanAabnes = Boolean(config && udgivetNavn)
  const kanAabneIJarvisBrowser = Boolean((window as unknown as {
    jarvisDesk?: { browser?: { aabn?: unknown } }
  }).jarvisDesk?.browser?.aabn)

  const hent = () => {
    if (!config || !adresse || henter) return
    setHenter(true)
    setFejl(false)
    fetchBlobWithAuth(config, adresse)
      .then((blob) => downloadBlob(blob, navn))
      .catch(() => setFejl(true))
      .finally(() => setHenter(false))
  }

  const aabnIJarvisBrowser = () => {
    if (!config || !kanAabnes) return
    const url = absolutApiUrl(config, adresse)
    const bro = (window as unknown as {
      jarvisDesk?: { browser?: { aabn?: (u: string) => unknown } }
    }).jarvisDesk?.browser
    if (!url || !bro?.aabn) { setFejl(true); return }
    setFejl(false)
    void bro.aabn(url)
  }

  const aabnIEgenBrowser = () => {
    if (!config || !kanAabnes || henter) return
    const openBrowser = prepareExternalWindow()
    setHenter(true)
    setFejl(false)
    // Linket hentes ved KLIK, ikke når rækken tegnes. Et link pr. visning
    // ville udstede en signatur for hver fil i tråden ved hver render — og
    // de ville være udløbet længe før nogen klikkede.
    hentSigneretFilLink(config, udgivetNavn)
      .then((url) => { if (!openBrowser(url)) setFejl(true) })
      .catch(() => { openBrowser(null); setFejl(true) })
      .finally(() => setHenter(false))
  }

  const Ikon = henter ? Loader2 : fejl ? AlertCircle : FileText

  return (
    <div className="fil-raekke">
      <span className="fil-raekke-ikon">
        <Ikon size={13} className={henter ? 'spin' : undefined} />
      </span>
      {/* Navnet er selv download-handlingen. Den var knappen før, og den
          skal blive ved med at virke for den der bare klikker på filen. */}
      <button type="button" className="fil-raekke-navn" onClick={hent}
              disabled={!config || !adresse || henter}
              title={adresse ? `Hent ${navn}` : 'Filen har ingen adresse'}>
        {navn}
      </button>
      {stoerrelse ? <span className="fil-raekke-prik" aria-hidden="true" /> : null}
      {stoerrelse ? <span className="fil-raekke-stoerrelse">{stoerrelse}</span> : null}
      {fejl ? <span className="fil-raekke-prik" aria-hidden="true" /> : null}
      {fejl ? <span className="fil-raekke-stoerrelse">kunne ikke hentes</span> : null}
      <span className="fil-raekke-handlinger">
        {kanAabnes && kanAabneIJarvisBrowser ? (
          <button type="button" onClick={aabnIJarvisBrowser} disabled={henter}
                  title="Åbn i Jarvis' browser" aria-label="Åbn i Jarvis' browser">
            <AppWindow size={14} />
          </button>
        ) : null}
        {kanAabnes ? (
          <button type="button" onClick={aabnIEgenBrowser} disabled={henter}
                  title="Åbn i din egen browser" aria-label="Åbn i din egen browser">
            <ExternalLink size={14} />
          </button>
        ) : null}
        <button type="button" onClick={hent} disabled={!config || !adresse || henter}
                title={`Hent ${navn}`} aria-label={`Hent ${navn}`}>
          <Download size={14} />
        </button>
      </span>
    </div>
  )
}
