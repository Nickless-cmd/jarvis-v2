import { StyleSheet } from 'react-native'
/**
 * Farvepaletter — mørk og lys, med et valgbart accent-familie.
 *
 * Den mørke palet er MÅLT i ChatGPT-appen (se tokens.ts) og er uændret; kun
 * accenten er Jarvis' egen. Den lyse er afledt af den, ikke opfundet ved siden
 * af: samme rolle-navne, samme afstand mellem lagene, spejlvendt.
 *
 * Accenten er skilt ud fra paletten, fordi de to spørgsmål er forskellige:
 * «lys eller mørk?» handler om omgivelserne, «hvilken farve?» handler om hvem
 * han er. Man skal kunne skifte det ene uden det andet.
 */

export type ThemeMode = 'dark' | 'light' | 'auto'
export type AccentName = 'gron' | 'teal' | 'lilla' | 'rav' | 'bla' | 'rose'

export interface Accent {
  name: AccentName
  label: string
  /** Selve accenten — knapper, markeringer, links. */
  color: string
  /** Brugerens boble: samme kulør, dybt nedtonet. Én pr. tema. */
  bubbleDark: string
  bubbleLight: string
  /** rgb-trippel til gennemsigtige varianter (dim/ghost). */
  rgb: string
}

export const ACCENTS: Accent[] = [
  { name: 'gron',  label: 'Grøn',  color: '#6EE7A8', bubbleDark: '#14402F', bubbleLight: '#CFF3E0', rgb: '110, 231, 168' },
  { name: 'teal',  label: 'Teal',  color: '#3FC7B4', bubbleDark: '#10403A', bubbleLight: '#C8EFEA', rgb: '63, 199, 180' },
  { name: 'lilla', label: 'Lilla', color: '#A07FEB', bubbleDark: '#382462', bubbleLight: '#E2D8FA', rgb: '160, 127, 235' },
  { name: 'rav',   label: 'Rav',   color: '#E8A33D', bubbleDark: '#4A3316', bubbleLight: '#F8E4C4', rgb: '232, 163, 61' },
  { name: 'bla',   label: 'Blå',   color: '#5B8DEF', bubbleDark: '#1E2C52', bubbleLight: '#D6E2FB', rgb: '91, 141, 239' },
  { name: 'rose',  label: 'Rosa',  color: '#F4849B', bubbleDark: '#4A1F2A', bubbleLight: '#FBD9E0', rgb: '244, 132, 155' }
]

export function accentByName(name: string | null | undefined): Accent {
  return ACCENTS.find((a) => a.name === name) ?? ACCENTS[0]!
}

/** Farver der IKKE afhænger af accenten. */
const DARK_BASE = {
  bg0: '#000000',
  bg1: '#121212',
  bg2: '#212121',
  // Fladen for noget der SVÆVER over indholdet — headerens knapper, komposeren.
  // I mørkt tema løftes den ved at være LYSERE end grunden; en skygge ville
  // være usynlig på næsten-sort.
  bgFloat: '#212121',
  bg3: '#303030',
  line: '#2A2A2A',
  fg1: '#FFFFFF',
  fg2: '#B0B0B0',
  fg3: '#7A7A7A',
  codeBg: '#303030',
  segmentTrack: '#414141',
  segmentActive: '#212121',
  ok: '#4CAF50',
  error: '#ff8080',
  warn: '#FFB347',
  depth0: '#000000',
  depth1: '#121212',
  depth2: '#1D1D1D',
  depth3: '#212121',
  glassFill: 'rgba(255, 255, 255, 0.07)',
  glassLine: 'rgba(255, 255, 255, 0.10)'
}

/**
 * Den lyse palet er SPEJLVENDT, ikke bare «hvid baggrund».
 *
 * bg0 er ikke rent hvidt: en helt hvid flade under sort tekst blænder i en
 * mørk stue, og det er dér telefonen oftest bruges om aftenen. #FAFAFA giver
 * samme afstand op til kortene (#FFFFFF) som den mørke palet giver ned.
 *
 * fg2/fg3 er MØRKERE end deres mørke modstykker er lyse — sort tekst på hvidt
 * skal bruge mindre kontrast for at være lige læselig som hvid på sort.
 */
const LIGHT_BASE = {
  bg0: '#FAFAFA',
  bg1: '#FFFFFF',
  bg2: '#F0F0F0',
  // Svævende flader skal være LYSERE end grunden, ikke mørkere. Komposeren og
  // headerens knapper brugte bg2 (#F0F0F0) på en grund af #FAFAFA — altså
  // mørkere — og så ser de nedsænkede ud i stedet for løftede, uanset hvor god
  // skyggen er. Det er dét der manglede.
  bgFloat: '#FFFFFF',
  bg3: '#E6E6E6',
  line: '#DCDCDC',
  fg1: '#111111',
  fg2: '#5A5A5A',
  fg3: '#8A8A8A',
  codeBg: '#F2F2F2',
  // Sporet bag segment-kontrollen. Var #E0E0E0 — 26 trin mørkere end grunden,
  // mens ChatGPTs kun er 12. Da de omkringliggende flader blev hvide, stod det
  // tilbage som et mørkt FELT i headeren frem for som et spor bag en knap.
  segmentTrack: '#EFEFEF',
  segmentActive: '#FFFFFF',
  ok: '#2E7D32',
  error: '#C62828',
  warn: '#B26A00',
  depth0: '#FAFAFA',
  depth1: '#FFFFFF',
  depth2: '#F4F4F4',
  depth3: '#EDEDED',
  glassFill: 'rgba(0, 0, 0, 0.05)',
  glassLine: 'rgba(0, 0, 0, 0.09)'
}

export type Scheme = 'dark' | 'light'

/**
 * Accenten MØRKNET til brug som tekst på lys flade.
 *
 * Accenterne er valgt til at lyse på sort. Sat som tekstfarve på hvidt bliver
 * de næsten ulæselige — «Forbundet til Jarvis ✓» i lys grøn på hvidt var det
 * første der faldt i øjnene da lyst tema kom op første gang.
 *
 * Fladen beholder den ægte accent (knapper, prikker, markeringer); kun TEKST
 * får den mørknede. Ellers ville brugerens farvevalg forsvinde.
 */
function darken(hex: string, amount: number): string {
  const n = hex.replace('#', '')
  const to = (i: number) => Math.round(parseInt(n.slice(i, i + 2), 16) * (1 - amount))
  const hh = (v: number) => Math.max(0, Math.min(255, v)).toString(16).padStart(2, '0')
  return `#${hh(to(0))}${hh(to(2))}${hh(to(4))}`
}

export function paletteFor(scheme: Scheme, accent: Accent) {
  const base = scheme === 'light' ? LIGHT_BASE : DARK_BASE
  return {
    ...base,
    accent: accent.color,
    accentText: scheme === 'light' ? darken(accent.color, 0.45) : accent.color,
    // Fladen bag de SVÆVENDE bjælker (header, komponist). Tråden ruller
    // bagved, så den skal dæmpe uden at dække — derfor gennemsigtig og ikke
    // en fast farve. I lyst tema er den hvid: en sort skygge under en lys
    // header ville se ud som en fejl, ikke som dybde.
    scrim: scheme === 'light' ? 'rgba(250, 250, 250, 0.82)' : 'rgba(0, 0, 0, 0.72)',
    userBubble: scheme === 'light' ? accent.bubbleLight : accent.bubbleDark,
    accentDim: `rgba(${accent.rgb}, 0.55)`,
    accentGhost: `rgba(${accent.rgb}, ${scheme === 'light' ? '0.16' : '0.12'})`
  }
}

/**
 * Tekstfarve der er læsbar OVEN PÅ accenten.
 *
 * Send-knappen har accent-baggrund og et ikon ovenpå. Med en mørk accent (blå,
 * lilla) skal ikonet være lyst; med en lys (grøn, rav) skal det være mørkt.
 * Uden dette ville ikonet forsvinde på halvdelen af paletterne.
 */
export function onAccent(accent: Accent): string {
  const [r, g, b] = accent.rgb.split(',').map((n) => Number(n.trim()))
  // Relativ luminans, forenklet (sRGB-vægte). Over midten → mørk tekst.
  const lum = (0.2126 * (r ?? 0) + 0.7152 * (g ?? 0) + 0.0722 * (b ?? 0)) / 255
  return lum > 0.55 ? '#111111' : '#FFFFFF'
}


/**
 * Løft: hvordan en flade der SVÆVER adskiller sig fra fladen under den.
 *
 * Målt i ChatGPT-appen: de svævende flader er rent hvide, og fladen omkring
 * dem er tonet — kraftigst helt inde ved kanten (ca. 9 % sort) og aftagende
 * over omtrent 100 px. Det er dét der får dem til at ligge OVENPÅ i stedet for
 * at være klippet ind i baggrunden.
 *
 * I mørkt tema kan man ikke gøre det med en skygge: sort på næsten-sort er
 * usynligt. Dér kommer løftet fra at fladen selv er LYSERE end grunden, plus
 * en hårfin kant der tegner omridset. Samme betydning, andet middel.
 */
export function elevation(scheme: Scheme): { boxShadow?: string; borderWidth?: number; borderColor?: string } {
  if (scheme === 'dark') {
    return { borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(255,255,255,0.10)' }
  }
  // To skygger, ikke én: den brede giver højden, den tætte giver kanten noget
  // at hvile på. Med kun den brede flyder omridset ud; med kun den tætte
  // ligner det en streg. Vægten er målt mod ChatGPT — deres flade er ca. 7 %
  // mørkere lige ved kanten og toner ud over omtrent 100 px.
  return { boxShadow: '0px 8px 34px rgba(0,0,0,0.16), 0px 2px 5px rgba(0,0,0,0.07)' }
}
