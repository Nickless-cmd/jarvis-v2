import { apiFetch, type ApiConfig } from './api'

/** Chat-artefakter: dokumenter der kan redigeres og udgives med et link.
 *
 *  Kontrakten er backend-ruterne i `apps/api/jarvis_api/routes/chat_documents.py`
 *  (målt 22/11-2026). Der er bevidst ingen tom-fallback: et manglende svar må
 *  ikke ligne «der findes ingen dokumenter».
 */
export interface Dokument {
  id: string
  sessionId: string
  titel: string
  tekst: string
  contentType: string
  version: number
  opdateret: string
}

interface RaaDokument {
  id: string
  session_id?: string
  title?: string
  content?: string
  content_type?: string
  version?: number
  updated_at?: string
}

function tilDokument(d: RaaDokument): Dokument {
  return {
    id: d.id,
    sessionId: d.session_id ?? '',
    titel: d.title ?? '',
    tekst: d.content ?? '',
    contentType: d.content_type ?? 'text/markdown',
    version: d.version ?? 1,
    opdateret: d.updated_at ?? '',
  }
}

export async function listDokumenter(config: ApiConfig, sessionId: string): Promise<Dokument[]> {
  const d = await apiFetch<{ documents?: RaaDokument[] }>(
    config, `/chat/sessions/${encodeURIComponent(sessionId)}/documents`,
  )
  if (!Array.isArray(d.documents)) throw new Error('Uventet svar fra /documents')
  return d.documents.map(tilDokument)
}

export async function opretDokument(
  config: ApiConfig, sessionId: string, titel: string, tekst: string,
): Promise<Dokument> {
  const d = await apiFetch<{ document?: RaaDokument }>(
    config, `/chat/sessions/${encodeURIComponent(sessionId)}/documents`,
    { method: 'POST', body: { title: titel, content: tekst } },
  )
  if (!d.document) throw new Error('Uventet svar ved oprettelse')
  return tilDokument(d.document)
}

export async function opdaterDokument(
  config: ApiConfig, id: string, tekst: string, version: number,
): Promise<Dokument> {
  const d = await apiFetch<{ document?: RaaDokument }>(
    config, `/chat/documents/${encodeURIComponent(id)}`,
    { method: 'PUT', body: { content: tekst, expected_version: version } },
  )
  if (!d.document) throw new Error('Uventet svar ved opdatering')
  return tilDokument(d.document)
}

/** Et tilbud på den næste sætning i dokumentet.
 *
 *  Tom streng betyder «intet forslag» — ikke en fejl. Backend svarer altid 200,
 *  så editoren kan skrives i uanset hvad der sker med modellen.
 *
 *  Forslaget hentes kun når brugeren beder om det (Bjørn 17/9-2026: grå tekst
 *  der kommer dumpende mens man skriver er «virkelig træls»).
 */
export async function foreslaaFortsaettelse(config: ApiConfig, id: string): Promise<string> {
  const d = await apiFetch<{ forslag?: string }>(
    config, `/chat/documents/${encodeURIComponent(id)}/suggest`, { method: 'POST' },
  )
  return (d.forslag ?? '').trim()
}

export interface Udgivelse {
  url: string
  filnavn: string
  udloeb: number
  levetidS: number
}

/** Skriv dokumentet til brugerens filmappe og få et kortlivet link tilbage. */
export async function udgivDokument(
  config: ApiConfig, id: string, filnavn = '',
): Promise<Udgivelse> {
  const d = await apiFetch<{ url?: string; filename?: string; udloeb?: number; levetid_s?: number }>(
    config, `/chat/documents/${encodeURIComponent(id)}/publish`,
    { method: 'POST', body: { filename: filnavn } },
  )
  if (!d.url) throw new Error('Uventet svar ved udgivelse')
  return {
    url: d.url,
    filnavn: d.filename ?? '',
    udloeb: d.udloeb ?? 0,
    levetidS: d.levetid_s ?? 0,
  }
}
