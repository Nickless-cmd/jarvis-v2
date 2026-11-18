/**
 * Karakter-modellen (lag 7): hver Matrix-karakter har en fast figur.
 *
 * ## Hvorfor modellen er udledt og ikke en tabel
 *
 * `matrix_karakterer.py` henter navnene fra cadence-registret ved at køre
 * registreringen mod en opsamler — der findes ingen karakter-liste, og der
 * skal ikke komme en. En figur-tabel ville genindføre præcis den liste:
 * glemmer man at tilføje en ny karakter, har den ingen figur, og ingen ser det.
 *
 * Her er figuren derfor en FUNKTION af navnet. Samme navn giver altid samme
 * figur, på tværs af processer og genindlæsninger, og en ny karakter har en
 * figur i det øjeblik den registreres. Målt 18/11-2026: registret har 28
 * karakterer, og alle 28 rammer en gyldig figur.
 *
 * ## Hvad modellen er lånt fra, og hvad den ikke er
 *
 * ChatGPTs app har `reference-characters.json`: 108 figurer med `appearance`
 * sammensat af 10 shapes × 10 farver × 8 accessories × øjne. Det er en
 * sammensætnings-model, ikke 108 tegninger — og det er den model der bærer.
 * Deres datafil er siden forsvundet fra disken (`/home/bs/rea` findes ikke
 * længere), så figurerne her er vores egne former; kun STRUKTUREN er lånt.
 *
 * ## Figuren er identitet, ikke tilstand
 *
 * Tilstand (kørt/ikke kørt, udfald) bæres af prikken og udfaldskolonnen i
 * `MatrixKarakterer.tsx`. Figurens farve må derfor ikke kodes til udfald, og
 * paletten her er bevidst holdt UDEN OM husets signal-farver (teal #3fc7b4,
 * gul #e8b04a, rød #e0645c, grøn #7cc49b). Ellers ville en violet karakter
 * se ud som en tilstand nogen havde valgt.
 */

/** De ti former. Navnene følger den målte liste fra deres fil, så de kan
 *  genkendes — formerne er tegnet af os. */
export const KARAKTER_SHAPES = [
  'capsule',
  'circle_two_ears',
  'four_lobed_butterfly',
  'heart',
  'rounded_cube',
  'rounded_diamond',
  'rounded_head_two_ears',
  'rounded_triangle',
  'six_lobed_flower',
  'twelve_scalloped_rosette',
] as const
export type KarakterShape = (typeof KARAKTER_SHAPES)[number]

/** Dæmpede farver, alle forskellige fra husets signal-palet. */
export const KARAKTER_FARVER = [
  '#8b7fd4', // violet
  '#6f8fd0', // indigo
  '#c98b5e', // kobber
  '#8fa86a', // oliven
  '#5f8f9e', // dæmpet marine
  '#c47a6b', // terracotta
  '#a87fb0', // plomme
  '#7fa88f', // salvie
  '#c9a55e', // okker
  '#8a8f9e', // skifer
] as const

export const KARAKTER_ACCESSORIES = [
  'beanie',
  'beret',
  'bow',
  'crown',
  'hat',
  'headphones',
  'orb',
  'three_lobe',
] as const
export type KarakterAccessory = (typeof KARAKTER_ACCESSORIES)[number]

/**
 * Accessory er et VALG der også omfatter «ingen».
 *
 * Alle 28 karakterer med hver sin hat ville se ud som en uniform. Fire nuller
 * ud af tolv giver en tredjedel uden, og det er stadig deterministisk.
 */
const ACCESSORY_VALG: readonly (KarakterAccessory | null)[] = [
  null, null, null, null,
  ...KARAKTER_ACCESSORIES,
]

export interface KarakterFigur {
  shape: KarakterShape
  farve: string
  accessory: KarakterAccessory | null
  /** Øjnenes indbyrdes afstand og højde i viewBox-enheder (0-48). */
  oejeAfstand: number
  oejeHoejde: number
}

/**
 * FNV-1a, 32 bit. Valgt frem for `Math.random` eller en tæller fordi den er
 * stabil: samme navn giver samme figur i hver proces, og fordi den spreder
 * korte ens-opbyggede navne (`red_dress`, `redpill`) uden at de lander ens.
 *
 * ## Hvorfor finalizeren er nødvendig (målt 18/11-2026)
 *
 * Rå FNV-1a over de 28 registrerede navne gav en skæv fordeling: farven
 * `#c98b5e` ramte 8 af 28 (29 %, forventet 2,8), én farve blev aldrig brugt,
 * og kun 17 af 28 figurer var unikke på form+farve. Årsagen er kendt for
 * FNV-1a: dens LAVE bits er ikke blandet, og `% n` læser netop dem.
 *
 * `fmix32` er murmur3's afslutning. Den blander high bits ned i low bits, så
 * `% n` ser et blandet tal. Det er ikke kosmetik — det er forskellen mellem
 * en figur-familie der ser ud som en familie og en der klumper.
 */
function fmix32(h: number): number {
  h ^= h >>> 16
  h = Math.imul(h, 0x85ebca6b) >>> 0
  h ^= h >>> 13
  h = Math.imul(h, 0xc2b2ae35) >>> 0
  h ^= h >>> 16
  return h >>> 0
}

function fnv1a(tekst: string): number {
  let hash = 0x811c9dc5
  for (let i = 0; i < tekst.length; i++) {
    hash ^= tekst.charCodeAt(i)
    // >>> 0 holder os i uint32; ellers bliver det et flydende tal efter få tegn.
    hash = (hash + ((hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24))) >>> 0
  }
  return fmix32(hash >>> 0)
}

/**
 * Ét felt ad gangen, med sit eget salt.
 *
 * Uden salt ville shape og farve trækkes fra samme tal, og så ville to
 * karakterer der ligger tæt i hash-rummet få både samme form OG samme farve —
 * altså være til at forveksle. Saltet gør felterne uafhængige.
 *
 * ## Hvorfor shape-saltet heder `krop` og ikke `shape` (målt 18/11-2026)
 *
 * Saltet er en fri konstant, men ikke en ligegyldig en: med `shape` faldt
 * `rounded_triangle` uden for alle 28 karakterer — en tegning ingen ville se,
 * altså død kode i paletten. Tolv kandidater blev målt mod de 28 rigtige navne;
 * `krop` var det første med fuld dækning (10/10 former, 10/10 farver, største
 * gruppe 5, 24 unikke form+farve-par). Fordelingen er deterministisk pr. navn,
 * så den ændrer sig ikke ved at nye karakterer registreres — de kan kun lægge
 * til.
 */
function vaelg<T>(liste: readonly T[], navn: string, felt: string): T {
  const i = fnv1a(`${navn}:${felt}`) % liste.length
  return liste[i] as T
}

/** Figuren for et karakternavn. Ren funktion — ingen state, ingen tilfældighed. */
export function karakterFigur(navn: string): KarakterFigur {
  return {
    shape: vaelg(KARAKTER_SHAPES, navn, 'krop'),
    farve: vaelg(KARAKTER_FARVER, navn, 'farve'),
    accessory: vaelg(ACCESSORY_VALG, navn, 'accessory'),
    // Blikket er også en funktion af navnet: to figurer med samme form og farve
    // skal stadig kunne skelnes på øjnene. 2.6-3.5 i afstand, 19.5-22.5 i højde.
    oejeAfstand: 2.6 + (fnv1a(`${navn}:oeje-afstand`) % 9) / 10,
    oejeHoejde: 19.5 + (fnv1a(`${navn}:oeje-hoejde`) % 31) / 10,
  }
}
