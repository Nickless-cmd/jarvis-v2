import { apiFetch, type ApiConfig } from './api'

/** Projekt-materiale: de filer der hører til et projekt (varig kontekst). */
export interface ProjektMateriale {
  navn: string
  size_bytes?: number
}

export interface Projekt {
  id: string
  navn: string
  beskrivelse?: string
  materiale: ProjektMateriale[]
}

/* AFTALT KONTRAKT med backend-agenten (parallelt arbejde — endpointet kan
   mangle når denne klient kører). Fejl kastes videre til kalderen, som VISER
   dem; der er bevidst ingen tom-liste-fallback, for en manglende backend må
   ikke ligne «du har ingen projekter».

     GET /api/projects                       → { projects: [{ id, name, description?, files?: [{ name, size_bytes? }] }] }
     GET /chat/sessions/{sid}/project        → { project_id: string | null }
     PUT /chat/sessions/{sid}/project        ← { project_id: string | null }
*/
interface RaaProjekt {
  id: string
  name?: string
  description?: string
  files?: Array<{ name: string; size_bytes?: number }>
}

export async function listProjekter(config: ApiConfig): Promise<Projekt[]> {
  const d = await apiFetch<{ projects?: RaaProjekt[] }>(config, '/api/projects')
  if (!Array.isArray(d.projects)) throw new Error('Uventet svar fra /api/projects')
  return d.projects.map((p) => ({
    id: p.id,
    navn: p.name || p.id,
    beskrivelse: p.description,
    materiale: (p.files ?? []).map((f) => ({ navn: f.name, size_bytes: f.size_bytes })),
  }))
}

export async function hentSessionProjekt(config: ApiConfig, sessionId: string): Promise<string | null> {
  const d = await apiFetch<{ project_id?: string | null }>(
    config, `/chat/sessions/${encodeURIComponent(sessionId)}/project`,
  )
  return d.project_id ?? null
}

export async function bindSessionProjekt(
  config: ApiConfig, sessionId: string, projectId: string | null,
): Promise<void> {
  await apiFetch<unknown>(config, `/chat/sessions/${encodeURIComponent(sessionId)}/project`, {
    method: 'PUT', body: { project_id: projectId },
  })
}
