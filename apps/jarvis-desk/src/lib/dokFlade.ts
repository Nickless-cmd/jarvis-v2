/**
 * Tolkningen af de tre Google-læseres svar — til visning i panelet.
 *
 * ## Hvorfor den er sin egen fil
 *
 * `docs_read`, `sheets_read` og `slides_read` returnerer alle tre JSON, men
 * med helt forskellig form: et dokument er titel + tekst, et regneark er et
 * 2D-array af celler, en præsentation er en liste af slides. Indtil
 * 27/10-2026 blev alle tre vist som rå tekst i tool-kortet — man kunne læse
 * JSON'en, men ikke SE regnearkets form eller dokumentets løbende tekst.
 *
 * Tolkningen ligger her og ikke i komponenten, fordi den skal kunne testes
 * uden at rendere React: en parser der er svær at teste bliver en parser der
 * gætter.
 *
 * ## Hvorfor navnet afgør, ikke indholdet
 *
 * Det afkortede resultat i samtalen er de første 2.000 tegn (serveren
 * afkorter). For et regneark kan det klippe midt i JSON'en, så en
 * `JSON.parse` på det ville fejle — og en knap der forsvandt fordi svaret var
 * stort ville være en knap der løj om sin egen grund. Derfor: værktøjsnavnet
 * afgør om fladen TILBYDES, og det FULDE resultat afgør hvad den VISER.
 */

export type DokFlade =
  | { kind: 'docs'; titel: string; tekst: string }
  | { kind: 'sheets'; interval: string; raekker: string[][] }
  | { kind: 'slides'; titel: string; antal: number; slides: { nr: number; tekst: string }[] }

/** De værktøjer der har en flade. Ét sted — både knappen og panelet læser her. */
export const DOK_VAERKTOEJER = ['docs_read', 'sheets_read', 'slides_read'] as const

export function erDokVaerktoej(navn: string): boolean {
  return (DOK_VAERKTOEJER as readonly string[]).includes(navn)
}

function somObjekt(raat: string): Record<string, unknown> | null {
  const t = (raat || '').trim()
  if (!t) return null
  try {
    const v = JSON.parse(t)
    return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
  } catch {
    return null
  }
}

function tekst(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

/**
 * Oversæt et værktøjssvar til en flade. `null` betyder «kan ikke vises» —
 * aldrig «vis noget der ligner». Panelet siger det højt i stedet for at
 * tegne en tom rude.
 */
export function dokFraResultat(navn: string, raat?: string | null): DokFlade | null {
  const d = somObjekt(raat || '')
  if (!d) return null
  // Fejl-svar har ingen flade: `{status: "error", error: "docs_http_404"}` er
  // en besked, ikke et dokument. Den vises i tool-kortet som den er.
  if (tekst(d.status) && tekst(d.status) !== 'ok') return null

  if (navn === 'docs_read') {
    const t = tekst(d.text)
    if (!t) return null
    return { kind: 'docs', titel: tekst(d.title), tekst: t }
  }

  if (navn === 'sheets_read') {
    const raw = d.values
    if (!Array.isArray(raw) || raw.length === 0) return null
    // Celler kan komme som tal eller null fra Google; fladen vil have strenge.
    // Vi tømmer ikke rækker for tomme felter — en tom kolonne er information
    // om at arket har en kolonne, og forskudte rækker ville lyve om formen.
    const raekker = raw.map((r) =>
      Array.isArray(r) ? r.map((c) => (c === null || c === undefined ? '' : String(c))) : [],
    )
    return { kind: 'sheets', interval: tekst(d.range), raekker }
  }

  if (navn === 'slides_read') {
    const raw = d.slides
    if (!Array.isArray(raw) || raw.length === 0) return null
    const slides = raw.map((s, i) => {
      const o = (s && typeof s === 'object' ? s : {}) as Record<string, unknown>
      const nr = typeof o.slide === 'number' ? o.slide : i + 1
      return { nr, tekst: tekst(o.text) }
    })
    return {
      kind: 'slides',
      titel: tekst(d.title),
      antal: typeof d.slide_count === 'number' ? d.slide_count : slides.length,
      slides,
    }
  }

  return null
}
