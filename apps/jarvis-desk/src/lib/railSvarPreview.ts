/**
 * Svar-uddraget til skinnens preview (spec punkt 3.2).
 *
 * Skinnens etiket er i dag én linje af BRUGERENS besked — altsaa spoergsmaalet.
 * Det svarer paa «hvad spurgte jeg om», men ikke paa «fik jeg det jeg skulle
 * bruge», og det er som regel dét man leder efter naar man scroller tilbage i
 * en lang samtale.
 *
 * DSH viser én prompt-linje og op til tre svarlinjer. Samme princip her; vores
 * egne maal, ikke DSH's, jf. punktets note om at det er princippet der laanes.
 *
 * To ting som en naiv `slice()` ville faa galt:
 *
 *  - **Kodehegn og tabeller er ikke prosa.** Et svar der aabner med ```bash
 *    ville give et uddrag paa «bash» — vaerre end ingenting. Hegnets INDHOLD
 *    springes over, ikke bare hegnets linje.
 *  - **Et klip midt i et surrogat-par** giver et oedelagt tegn. `Array.from`
 *    itererer paa kodepunkter, saa et emoji enten kommer med eller ikke.
 */

/** Hoejst tre linjer, som DSH. Flere goer preview'et til en besked. */
export const MAX_LINJER = 3
/** Samlet loft. DSH bruger 120; vores skinne er smallere, men teksten ombrydes. */
export const MAX_TEGN = 120

// Klippet bor i `tekstKlip` og deles med udeladelses-laget (30/9-2026). To
// kopier af et surrogat-sikkert klip er to steder fejlen kan komme tilbage.
//
// `export { x } from './y'` alene ville IKKE virke: den videresender uden at
// binde navnet lokalt, og modulets egen kode her bruger det. Derfor import
// OG re-eksport.
import { klipTegn } from './tekstKlip'
export { klipTegn }

/** Ren tekst ud af en besked-krop, uanset om den er streng eller blokke. */
function tekstAf(content: unknown): string {
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content
    .map((b) => (b && typeof b === 'object' && (b as { type?: string }).type === 'text'
      ? (b as { text?: string }).text ?? '' : ''))
    .join('')
}

/**
 * Op til tre laesbare linjer af et svar.
 *
 * Tomme linjer, kodehegn og deres indhold, tabel-linjer og rene
 * markdown-markoerer springes over — de siger intet om hvad svaret var.
 */
export function svarPreview(content: unknown, maksLinjer = MAX_LINJER, maksTegn = MAX_TEGN): string {
  const raa = tekstAf(content)
  if (!raa.trim()) return ''
  const ud: string[] = []
  let iHegn = false
  for (const raw of raa.split('\n')) {
    const l = raw.trim()
    if (l.startsWith('```')) { iHegn = !iHegn; continue }
    if (iHegn) continue
    // Tabel-linjer og vandrette streger er struktur, ikke indhold.
    if (/^\|/.test(l) || /^[-=*_]{3,}$/.test(l)) continue
    const ren = l.replace(/^[>#*\-•\d.)\s]+/, '').trim()
    if (!ren) continue
    ud.push(ren)
    if (ud.length >= maksLinjer) break
  }
  if (ud.length === 0) return ''
  return klipTegn(ud.join(' '), maksTegn)
}

/**
 * Svaret der hoerer til et anker: beskederne EFTER det, indtil naeste
 * bruger-besked.
 *
 * Et anker peger paa brugerens besked (eller paa den foerste synlige besked
 * efter en komprimering). Svaret ligger bagefter — og kan vaere delt over
 * flere assistent-beskeder, saa der samles indtil der er linjer nok.
 */
export function svarTilAnker(
  beskeder: Array<{ id: string; role: string; content: unknown }>,
  ankerId: string,
): string {
  const i = beskeder.findIndex((m) => m.id === ankerId)
  if (i < 0) return ''
  const dele: string[] = []
  for (let j = i; j < beskeder.length; j++) {
    const m = beskeder[j]!
    if (j > i && m.role === 'user') break        // naeste tur er begyndt
    if (m.role !== 'assistant') continue
    const s = svarPreview(m.content)
    if (s) dele.push(s)
    if (dele.join(' ').length >= MAX_TEGN) break
  }
  return dele.length ? klipTegn(dele.join(' '), MAX_TEGN) : ''
}
