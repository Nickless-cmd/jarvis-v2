import { klipTegn, tegnTal } from './tekstKlip'

/**
 * Udeladelses-laget for lange vaerktoejs-resultater (spec punkt 5).
 *
 * I dag stopper et langt resultat bare. Serveren afkorter ved 2.000 tegn —
 * begrundelsen staar i endpointets docstring: 2.309 resultater vejede 5,7 MB,
 * hvoraf 2,5 MB laa efter de foerste 2.000 tegn — men klienten siger det ikke,
 * og indtil klippet ligger hele teksten i DOM'en.
 *
 * To ting skal vaere sande om en udeladelse:
 *
 *  1. **Den skal kunne ses.** Et resultat der bare holder op ligner et
 *     resultat der var saa langt. Klausulen siger hvor meget der mangler og
 *     hvordan man faar fat i det.
 *  2. **Den skal beholde det rigtige.** Shell-vaerktoejer gemmer det vigtige
 *     til SIDST — exit-koden og fejlen staar i halen. En fil-laesning goer det
 *     modsatte: man laeser fra begyndelsen. Derfor er politikken pr. vaerktoej
 *     og ikke ét tal for alle.
 *
 * Bjoern 30/9-2026 valgte den daempede klausul og hoved+hale for shell,
 * kun hoved for fil-laesning.
 */

export interface Politik {
  /** Linjer beholdt fra begyndelsen. */
  hoved: number
  /** Linjer beholdt fra enden. 0 = ingen hale. */
  hale: number
  /** Hvad den der vil se resten skal goere. Staar i klausulen. */
  vejledning: string
}

/**
 * Shell: halen baerer exit-koden og fejlen.
 *
 * 20 + 12 er valgt paa formen, ikke paa en maaling: 20 linjer daekker et
 * `ls`-hoved eller en kommandos opstart, 12 daekker en stak-sporing eller en
 * fejllinje med kontekst. Er en maaling uenig, er det tallene der skal
 * flytte sig — ikke formen.
 */
const SHELL: Politik = { hoved: 20, hale: 12, vejledning: 'kør igen med `| tail -40` for halen' }

/** Fil-laesning: man laeser forfra, og halen er sjaeldent det man vil se. */
const FIL: Politik = { hoved: 30, hale: 0, vejledning: 'læs igen med et linjeinterval' }

/** Alt andet: hoved, og ingen paastand om at halen betyder noget. */
const STANDARD: Politik = { hoved: 24, hale: 0, vejledning: 'fold resultatet ud for resten' }

const SHELL_VAERKTOEJER = new Set([
  'bash', 'operator_bash', 'bash_session_run', 'operator_bash_session_run',
])
const FIL_VAERKTOEJER = new Set([
  'read_file', 'operator_read_file', 'read_attachment', 'view_file',
])

export function politikFor(vaerktoej: string): Politik {
  const n = String(vaerktoej || '').trim()
  if (SHELL_VAERKTOEJER.has(n)) return SHELL
  if (FIL_VAERKTOEJER.has(n)) return FIL
  return STANDARD
}

export interface Udeladelse {
  /** Det der vises. Uden udeladelse: hele teksten, uaendret. */
  tekst: string
  /** Hovedet for sig — klausulen skal staa MELLEM de to, ikke efter begge. */
  hoved: string
  /** Halen for sig. Tom naar politikken ingen hale har. */
  hale: string
  /** Linjer udeladt i midten. 0 betyder at intet blev udeladt. */
  udeladt: number
  /** Linjer i alt i den raa tekst. */
  ialt: number
  /** Sand naar der ER klippet — laeses frem for at sammenligne `udeladt`. */
  klippet: boolean
}

/**
 * Behold hoved og (maaske) hale.
 *
 * Klipper ALDRIG naar der ikke er noget at spare: er der faerre linjer end
 * hoved+hale, returneres teksten uaendret. En klausul om «0 linjer udeladt»
 * ville vaere stoej med en paastand i.
 */
export function behold(tekst: string, p: Politik): Udeladelse {
  const raa = String(tekst ?? '')
  const linjer = raa.split('\n')
  const ialt = linjer.length
  const hoved = Math.max(0, p.hoved)
  const hale = Math.max(0, p.hale)
  // `>` og ikke `>=`: er der praecis hoved+hale linjer, er der intet at udelade.
  if (ialt <= hoved + hale) {
    return { tekst: raa, hoved: raa, hale: '', udeladt: 0, ialt, klippet: false }
  }
  const udeladt = ialt - hoved - hale
  const h = linjer.slice(0, hoved).join('\n')
  const t = hale > 0 ? linjer.slice(ialt - hale).join('\n') : ''
  return {
    tekst: t ? `${h}\n${t}` : h,
    hoved: h, hale: t,
    udeladt, ialt, klippet: true,
  }
}

/** Hvor klausulen skal staa, i linjer fra toppen af det viste. */
export function klausulEfterLinje(p: Politik): number {
  return Math.max(0, p.hoved)
}

/**
 * Klausulens tekst. Én form for alle vaerktoejer, med vaerktoejets egen
 * vejledning bagpaa — DSH's `formatRetentionNotice`.
 */
export function klausul(u: Udeladelse, p: Politik): string {
  if (!u.klippet) return ''
  const n = u.udeladt.toLocaleString('da-DK')
  const hvor = p.hale > 0 ? 'i midten' : 'til sidst'
  return `${n} ${u.udeladt === 1 ? 'linje' : 'linjer'} udeladt ${hvor} · ${p.vejledning}`
}

/**
 * Sidste vaern: en enkelt LINJE kan vaere laengere end hele skaermen — en
 * minificeret fil, et base64-blob. Linje-taellingen ser den som én linje og
 * lader den staa.
 */
export const MAX_LINJE_TEGN = 2000

export function klipLangeLinjer(tekst: string, maks = MAX_LINJE_TEGN): string {
  if (tegnTal(tekst) <= maks) return tekst
  return tekst
    .split('\n')
    .map((l) => (tegnTal(l) > maks ? klipTegn(l, maks) : l))
    .join('\n')
}
