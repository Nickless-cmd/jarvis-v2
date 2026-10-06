import { useEffect, useRef, useState } from 'react'
import { fetchBlobWithAuth, type ApiConfig } from '../../lib/api'

/**
 * En widget: model-skrevet HTML renderet i en SANDKASSE.
 *
 * Det er første gang model-skrevet markup tegnes i desk, og husets regel har
 * været et klart nej — `MermaidBlock` siger selv at `dangerouslySetInnerHTML`
 * sidder på «bibliotekets tilsigtede API, ikke model-HTML». Reglen viger kun
 * fordi der er TO uafhængige lag, og ingen af dem er en saniteringsliste:
 *
 *  1. SERVEREN (`core/services/widget_dokument.py`) har pakket fragmentet i et
 *     dokument med `default-src 'none'` — ingen netværk ind eller ud. Samme
 *     dokument går til mobilen, så de to flader ikke kan drive fra hinanden.
 *  2. HER: `sandbox="allow-scripts"` UDEN `allow-same-origin`. Det giver
 *     iframen en uigennemsigtig origin, så den ikke kan nå desks DOM, hans
 *     token, localStorage eller cookies.
 *
 * `allow-same-origin` må ALDRIG tilføjes sammen med `allow-scripts`. Tilsammen
 * ophæver de sandkassen, og widget'en ville kunne læse alt desk kan.
 *
 * **Tokenet kommer aldrig nær iframen.** HTML'en hentes HER med `Authorization`
 * og lægges i `srcdoc`. Pegede vi iframen på `/attachments/media/{id}`, ville
 * dokumentet blive serveret fra API'ets egen origin — og en fejl i
 * sandkasse-attributten ville så gøre det samme-origin med resten.
 *
 * Referencen hentes fra `/attachments/media/{id}`, ikke `/attachments/{id}`:
 * den sidste kender kun denne sessions registry og ville dø ved reload.
 */

/** Hvor stort et dokument vi vil hente. Serveren capper ved 256 KB; her står
 *  et uafhængigt loft, så en forkert reference ikke kan trække en stor fil
 *  ind i hukommelsen. */
const MAX_BYTES = 512 * 1024

export interface WidgetBlok {
  attachment_id?: string
  filename?: string
  size_bytes?: number
}

export function WidgetBlock({ block, config }: { block: WidgetBlok; config: ApiConfig }) {
  const [html, setHtml] = useState<string | null>(null)
  const [fejl, setFejl] = useState<string | null>(null)
  const iframe = useRef<HTMLIFrameElement | null>(null)
  const [hoejde, setHoejde] = useState(160)

  const id = String(block.attachment_id || '').trim()

  useEffect(() => {
    if (!id) { setFejl('widget uden reference'); return }
    let levende = true
    fetchBlobWithAuth(config, `/attachments/media/${encodeURIComponent(id)}`)
      .then(async (blob) => {
        if (blob.size > MAX_BYTES) throw new Error(`for stor (${blob.size} B)`)
        const t = await blob.text()
        if (levende) setHtml(t)
      })
      .catch((e) => { if (levende) setFejl(String(e?.message || e)) })
    return () => { levende = false }
  }, [id, config])

  // Højden kommer FRA widget'en: en iframe har ingen indholds-højde udefra, og
  // en fast højde ville give en rude med rullepanel midt i tråden. Beskeden er
  // det ENESTE vi lytter efter, og vi tjekker at den kom fra netop vores egen
  // iframe — et andet vindue må ikke kunne ændre højden her.
  useEffect(() => {
    function paaBesked(e: MessageEvent) {
      if (!iframe.current || e.source !== iframe.current.contentWindow) return
      const d = e.data
      if (!d || typeof d !== 'object' || d.type !== 'jarvis-widget-hoejde') return
      const h = Number(d.hoejde)
      if (!Number.isFinite(h) || h <= 0) return
      setHoejde(Math.min(Math.max(Math.round(h), 48), 1200))
    }
    window.addEventListener('message', paaBesked)
    return () => window.removeEventListener('message', paaBesked)
  }, [])

  if (fejl) {
    return <div className="rv-kort rv-widget-fejl">Widget kunne ikke vises: {fejl}</div>
  }
  if (html == null) {
    return <div className="rv-kort rv-widget-venter">Widget hentes…</div>
  }
  return (
    <iframe
      ref={iframe}
      className="rv-widget"
      title={block.filename || 'widget'}
      // UDEN allow-same-origin. Se komponentens docstring.
      sandbox="allow-scripts"
      // `referrerPolicy` og `loading` er ikke sikkerhed, men de fjerner to
      // utilsigtede signaler: hvor widget'en blev vist, og en hentning af en
      // flade der ikke er rullet frem endnu.
      referrerPolicy="no-referrer"
      loading="lazy"
      srcDoc={html + HOEJDE_SCRIPT}
      style={{ width: '100%', height: hoejde, border: 0, display: 'block' }}
    />
  )
}

/** Måler sit eget indhold og siger højden til forælderen. Ligger HER og ikke i
 *  serverens dokument, fordi det er en klient-detalje: mobilen måler på sin
 *  egen måde, og serverens dokument skal være ens for begge. */
const HOEJDE_SCRIPT = `
<script>
(function () {
  function sig() {
    try {
      var h = Math.max(
        document.body ? document.body.scrollHeight : 0,
        document.documentElement ? document.documentElement.scrollHeight : 0
      );
      parent.postMessage({ type: 'jarvis-widget-hoejde', hoejde: h + 24 }, '*');
    } catch (e) {}
  }
  sig();
  window.addEventListener('load', sig);
  if (window.ResizeObserver && document.body) {
    new ResizeObserver(sig).observe(document.body);
  }
})();
</script>
`
