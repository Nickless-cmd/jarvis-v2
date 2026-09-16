import { railAnchors as ankrePrTur, type RailAnchor } from '../components/chat/MessageRail'

/**
 * Hvad saved rail viser: KAPITLER og KOMPRIMERINGER — ikke én streg pr. besked.
 *
 * Bjørn 16/9-2026: rail'en «bliver hurtigt fyldt med støj og giver ikk en
 * mulighed for at scroole til en faktisk brugbar sted». Målt samme aften på
 * hans hovedsession: 147 bruger-beskeder, 9 komprimeringer, 12 kapitler. De
 * 147 streger var støjen, og de kom to veje fra:
 *
 *  - ChatView faldt tilbage til én streg pr. bruger-besked, så snart færre end
 *    to kapitler matchede — også mens kapitlerne endnu ikke var hentet.
 *  - CodeView hentede slet ikke kapitler; den viste ALTID én pr. besked.
 *
 * Nu gælder én regel begge steder:
 *
 *  - Kort session (≤ KORT_SESSION bruger-beskeder): én streg pr. tur. Her ER
 *    hver tur et kapitel — serveren gør det samme uden LLM-kald.
 *  - Lang session: kun serverens kapitler. Er de ikke kommet endnu, vises
 *    ingen — hellere en tom rail et øjeblik end 147 streger.
 *  - Komprimeringer vises altid, som deres egen slags. Det er de punkter hvor
 *    konteksten blev skåret over, og dermed de steder man faktisk leder efter.
 *
 * En markør er ikke en synlig besked, så dens streg peger på den første synlige
 * besked EFTER den — dér hvor samtalen fortsatte.
 */
export const KORT_SESSION = 6

export type RailSlags = 'kapitel' | 'komprimering'
export type RailAnker = RailAnchor & { slags: RailSlags }

type Besked = { id: string; role: string; content: unknown; created_at?: string }

export function bygRailAnkre(
  beskeder: Besked[],
  kapitler: { anchor_id: string; title: string }[],
): RailAnker[] {
  const synlige = beskeder.filter((m) => m.role === 'user' || m.role === 'assistant')
  const prTur = ankrePrTur(synlige)
  const fejlPrId = new Map(prTur.map((a) => [a.id, a.fejl]))
  const synligeIds = new Set(synlige.map((m) => m.id))

  let kapitelAnkre: RailAnchor[]
  if (prTur.length <= KORT_SESSION) {
    kapitelAnkre = prTur
  } else {
    kapitelAnkre = kapitler
      .filter((k) => synligeIds.has(k.anchor_id))
      .map((k) => ({ id: k.anchor_id, label: k.title, fejl: fejlPrId.get(k.anchor_id) }))
  }

  // Plads i den fulde liste — det er rækkefølgen på skærmen.
  const plads = new Map(beskeder.map((m, i) => [m.id, i]))
  const ud: (RailAnker & { _plads: number })[] = kapitelAnkre.map((a) => ({
    ...a, slags: 'kapitel', _plads: plads.get(a.id) ?? 0,
  }))

  beskeder.forEach((m, i) => {
    if (m.role !== 'compact_marker') return
    const naeste = beskeder.slice(i + 1).find((n) => synligeIds.has(n.id))
    if (!naeste) return     // komprimeret efter sidste besked: intet at springe til
    // To markører uden en besked imellem (målt 14/9 og 15/9: par med 10 s
    // mellemrum) er ét punkt i samtalen — én streg, med det seneste tidspunkt.
    const forrige = ud.find((a) => a.slags === 'komprimering' && a.id === naeste.id)
    if (forrige) { forrige.label = `Komprimeret${tidspunkt(m.created_at)}`; return }
    ud.push({
      id: naeste.id,
      label: `Komprimeret${tidspunkt(m.created_at)}`,
      slags: 'komprimering',
      // En halv plads FØR beskeden: står et kapitel på samme besked, kommer
      // komprimeringen først — den skete før samtalen fortsatte.
      _plads: (plads.get(naeste.id) ?? i) - 0.5,
    })
  })

  return ud
    .sort((a, b) => a._plads - b._plads)
    .map(({ _plads, ...a }) => a)
}

/** « · 13/9 18:51» i lokal tid. Uden gyldigt tidspunkt: ingenting. */
function tidspunkt(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return ` · ${d.getDate()}/${d.getMonth() + 1} ${hh}:${mm}`
}
