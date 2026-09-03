/**
 * Gør markdown til noget der kan LÆSES OP.
 *
 * Bjørn: «den der er der nu citere tegn og det bliver rodet.» Oplæsningen fik
 * beskedens rå tekst, så en talesyntese sagde «stjerne stjerne vigtigt stjerne
 * stjerne» og læste hele kodeblokke op tegn for tegn.
 *
 * Reglen er ikke «fjern tegnsætning» — punktummer og kommaer er dét der giver
 * oplæsningen rytme. Reglen er: fjern det der er LAYOUT, og behold det der er
 * sprog.
 *
 * Kodeblokke nævnes i stedet for at blive læst. Ingen har lyst til at høre en
 * bash-kommando stavet, men man skal vide at der stod kode — ellers lyder
 * svaret som om der mangler noget.
 */

export function stripForSpeech(markdown: string): string {
  let s = String(markdown ?? '')

  // Kodeblokke → en kort omtale. Sproget følger blokkens eget sprog-mærke.
  s = s.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_m, lang) =>
    lang ? ` (${lang}-kode) ` : ' (kodeblok) ')

  s = s
    .replace(/`([^`]+)`/g, '$1')            // inline-kode: behold indholdet
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')  // billede → dets tekst
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')   // link → linkteksten, ikke url'en
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')     // overskrifts-havelåger
    .replace(/^\s{0,3}>\s?/gm, '')          // citat-pile
    .replace(/^\s*[-*+]\s+/gm, '')          // punkttegn
    .replace(/^\s*\d+\.\s+/gm, '')          // numre i lister
    .replace(/^\s*([-*_]\s*){3,}$/gm, '')   // vandrette linjer
    .replace(/\*\*([^*]+)\*\*/g, '$1')      // fed
    .replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, '$1$2')  // kursiv
    .replace(/(^|\W)_([^_\n]+)_(?=\W|$)/g, '$1$2')    // kursiv med underscore
    .replace(/~~([^~]+)~~/g, '$1')          // gennemstreget
    .replace(/\|/g, ' ')                    // tabel-streger
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return s
}

/**
 * Talesyntese har et loft (serveren siger 5000 tegn). Skær ved en SÆTNING.
 *
 * Tærsklen er lav med vilje. Første udgave krævede at sætningsgrænsen lå efter
 * halvdelen af loftet, ellers skar den hårdt — men et afbrudt ord lyder som en
 * fejl, mens en afsluttet sætning lyder som et valg. At miste lidt mere tekst
 * er den mindre pris. Hårdt snit sker kun når der slet ikke ER et punktum.
 */
export function clampForSpeech(text: string, limit = 4800): string {
  const s = text.trim()
  if (s.length <= limit) return s
  const cut = s.slice(0, limit)
  const stop = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('! '), cut.lastIndexOf('? '))
  return (stop > 0 ? cut.slice(0, stop + 1) : cut).trim()
}
