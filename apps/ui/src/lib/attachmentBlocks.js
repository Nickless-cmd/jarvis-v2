import { authHeaders } from './auth.js'

/**
 * Server-blokke → vedhæftninger på en besked.
 *
 * Serveren sender `content_json` som en liste af blokke pr. besked — og den
 * følger med til ALLE klienter. Målt 15/9-2026: `get_chat_session` returnerer
 * blokke, og file-blokken for det udgivne regneark lå i payloadet (besked
 * `message-06532e…`, `kilde: "published"`). Web-UI'en normaliserede beskeder
 * ned til id/role/content/ts og kastede dem væk — så en fil Jarvis lagde ud
 * kun kunne nævnes i prosa, med en adresse man selv skulle skrive af.
 *
 * Der er TO slags referencer, og de hentes hver for sig:
 *
 *  - `attachment_id` — en upload eller et genereret billede. Hentes over det
 *    user-scopede `/attachments/{id}?session_id=…`
 *  - `url` — en fil Jarvis selv har udgivet med `publish_file`. Adressen
 *    kræver Authorization: målt 12/9-2026 svarer `/files/{navn}` 401 uden
 *    token, så et almindeligt link virker ikke. Den hentes med token (se
 *    `hentUdgivetFil`).
 *
 * Blokke uden nogen af delene springes over: en halv reference kan ikke hentes.
 */
export function attachmentsFromBlocks(blocks) {
  if (!Array.isArray(blocks)) return []
  const ud = []
  for (const b of blocks) {
    if (!b || typeof b !== 'object') continue
    const type = String(b.type || '')
    if (type !== 'file' && type !== 'image') continue
    const id = String(b.attachment_id || '').trim()
    const url = String(b.url || '').trim()
    if (!id && !url) continue
    ud.push({
      id: id || null,
      filename: String(b.filename || '').trim() || 'fil',
      mimeType: String(b.mime_type || '').trim(),
      size: Number(b.size_bytes) || 0,
      url,
      kilde: String(b.kilde || '').trim(),
      type,
    })
  }
  return ud
}

/**
 * Hent en fil Jarvis har udgivet — MED token, som blob-URL.
 *
 * `/files/{navn}` svarer 401 uden Authorization, så et almindeligt `<a href>`
 * giver «unauthorized». Samme vej som desk'ens `AttachmentBlock` og mobilens
 * `aabnFil`: hent med Bearer, lav en blob, og gem den.
 *
 * Returnerer blob-URL'en, så kalderen kan vise eller gemme den.
 */
export async function hentUdgivetFil(url, filename = '') {
  const absolut = new URL(url, window.location.origin).toString()
  const res = await fetch(absolut, { headers: { ...authHeaders() } })
  if (!res.ok) {
    throw new Error(`Kunne ikke hente filen (HTTP ${res.status})`)
  }
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = filename || ''
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Frigiv efter download er startet — ellers lækker vi blob'en.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000)
  return objectUrl
}
