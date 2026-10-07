import { useEffect, useState } from 'react'
import { Text } from 'react-native'
import { WidgetFlade, MAX_WIDGET_BYTES } from './WidgetFlade'
import { blokUrl } from '../lib/aabnFil'
import { useAuth } from '../state/AuthContext'

/**
 * Henter en widget og giver dens dokument til `WidgetFlade`.
 *
 * Hentningen ligger HER og ikke i `WidgetFlade`, saa fladen kan testes uden
 * et netvaerk — og saa tokenet kun findes ét sted. `WidgetFlade` faar ren
 * tekst og har ingen adgang til `config`.
 *
 * `blokUrl` giver `/attachments/media/{id}`, som slaar op i DB'en og er
 * user-scopet. `/attachments/{id}` kender kun denne sessions registry og
 * ville doe ved en genindlaesning.
 */
export function WidgetVedhaeftning({ blok }: {
  blok: { attachment_id?: string; url?: string; type?: string; filename?: string }
}) {
  const { config } = useAuth()
  const [html, setHtml] = useState<string | null>(null)
  const [fejl, setFejl] = useState<string | null>(null)

  const url = config?.apiBaseUrl ? blokUrl(blok, config.apiBaseUrl) : ''

  useEffect(() => {
    if (!url || !config?.authToken) { setFejl('widget uden adgang'); return }
    let levende = true
    fetch(url, { headers: { Authorization: `Bearer ${config.authToken}` } })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const t = await r.text()
        if (t.length > MAX_WIDGET_BYTES) throw new Error('for stor')
        if (levende) setHtml(t)
      })
      .catch((e) => { if (levende) setFejl(String(e?.message || e)) })
    return () => { levende = false }
  }, [url, config?.authToken])

  if (fejl) return <Text style={{ fontSize: 13, opacity: 0.8, padding: 8 }}>Widget kunne ikke vises: {fejl}</Text>
  if (html == null) return <Text style={{ fontSize: 13, opacity: 0.7, padding: 8 }}>Widget hentes…</Text>
  return <WidgetFlade html={html} titel={blok.filename} />
}

/** En GENERERET `text/html` er en widget, ikke en fil man henter.
 *  `kilde: 'generated'` udelukker en UDGIVET html-fil, som Bjoern selv har
 *  bedt om at faa som fil — den skal stadig vaere et kort. */
export function erWidget(b: {
  mime_type?: string; kilde?: string; attachment_id?: string
}): boolean {
  return String(b.mime_type || '').toLowerCase().startsWith('text/html')
    && String(b.kilde || '') === 'generated'
    && !!String(b.attachment_id || '').trim()
}
