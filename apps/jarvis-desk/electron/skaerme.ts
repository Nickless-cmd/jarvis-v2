/**
 * Skærm-oversigten — den liste Jarvis kan tale om.
 *
 * Bygget 21/9-2026 efter Bjørn: «halo og markør følges ikke lige nu.. det skal
 * bygges sammen med din skærm info ting til dig selv». Hans pointe er
 * arkitektonisk: der må ikke være to kortlægninger. Den halo'en tegner efter,
 * og den Jarvis får gennem `operator_screen_size`, er den SAMME.
 *
 * Hvorfor ikke bare `screen.getAllDisplays()`: på Bjørns maskine er der tre
 * fysiske skærme i ÉT X-screen (Xinerama). X selv ved det — `xrandr
 * --listmonitors` svarer:
 *
 *   Monitors: 3
 *    0: +*DP-0 1920/597x1080/336+1920+0  DP-0
 *    1: +DP-4 1920/531x1080/299+0+0     DP-4
 *    2: +DP-2 1920/531x1080/299+3840+0  DP-2
 *
 * Om Chromium melder det samme, er et åbent spørgsmål — og det spørgsmål skal
 * ikke afgøre om halo'en kan følge markøren. Derfor læses X først på Linux
 * (se skaermeHost.ts), med Electron som fallback og som eneste kilde på
 * macOS/Windows.
 *
 * Denne fil er REN — ingen electron-import — så parser og oversigt kan testes
 * uden en skærm.
 */
import type { Skærm } from './markoerOmraade'

/** Én skærm som den kommer fra værten, før den er nummereret. */
export interface SkærmKilde extends Skærm {
  /** Værtens eget id. Electron: display-id. Xrandr: monitor-nummeret. */
  id: number
  /** Er dette værtenens primære skærm? */
  primaer: boolean
  /** Menneskelæsbart navn — «DP-0», eller Electrons label. */
  navn: string
}

/** Én skærm som Jarvis ser den: nummereret fra venstre, med et midtpunkt. */
export interface SkærmInfo extends Skærm {
  /** 1-baseret, sorteret venstre → højre, så «skærm 1» er den længst til
   *  venstre. Det er den nummerering Jarvis kan sige højt og ramme. */
  indeks: number
  primaer: boolean
  navn: string
  /** Hvor Jarvis skal lægge markøren for at stå midt på skærmen. */
  midtpunkt: { x: number; y: number }
}

/**
 * Læs `xrandr --listmonitors`.
 *
 * Linjerne ser sådan ud — navn, pixel- og millimeter-mål, position:
 *
 *     0: +*DP-0 1920/597x1080/336+1920+0  DP-0
 *
 * `*` i flagene markerer den primære skærm. Returnerer `null` når ikke én
 * eneste linje kunne læses, så kalderen kan se forskel på «formatet passede
 * ikke» og «der er ingen skærme».
 */
export function parseXrandrMonitors(ud: string): SkærmKilde[] | null {
  // Positionen kan være negativ (skærm sat til venstre for den primære), og
  // xrandr skriver den som `+-1920+0` — derfor `-?` inde i gruppen.
  const mønster = /^\s*(\d+):\s+([+*]+)(\S+)\s+(\d+)\/\d+x(\d+)\/\d+\+(-?\d+)\+(-?\d+)/
  const skærme: SkærmKilde[] = []
  for (const linje of ud.split('\n')) {
    const m = mønster.exec(linje)
    if (!m) continue
    skærme.push({
      id: Number(m[1]),
      navn: m[3],
      primaer: m[2].includes('*'),
      width: Number(m[4]),
      height: Number(m[5]),
      x: Number(m[6]),
      y: Number(m[7]),
    })
  }
  return skærme.length > 0 ? skærme : null
}

/**
 * Gør værtens skærme til den nummererede liste Jarvis læser.
 *
 * Sorteringen er venstre → højre (x, så y) og ikke værtens egen rækkefølge.
 * xrandr nummererer efter tilslutning: på Bjørns maskine er `0: DP-0` den
 * MIDTERSTE skærm. En liste hvor «skærm 1» var den midterste ville være en
 * fælde at pege efter — Jarvis ville ramme den forkerte og have ret i at
 * tro han ramte den rigtige.
 */
export function skærmOversigt(skaerme: SkærmKilde[]): SkærmInfo[] {
  return [...skaerme]
    .sort((a, b) => a.x - b.x || a.y - b.y)
    .map((s, i) => ({
      indeks: i + 1,
      primaer: s.primaer,
      navn: s.navn,
      x: s.x,
      y: s.y,
      width: s.width,
      height: s.height,
      midtpunkt: {
        x: Math.round(s.x + s.width / 2),
        y: Math.round(s.y + s.height / 2),
      },
    }))
}
