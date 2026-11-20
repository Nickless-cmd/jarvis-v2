// @vitest-environment node
/**
 * Ordhalen skal køre i BEGGE flader — chat og code — målt i Chromium.
 *
 * Bjørn 20/11-2026: «den nyeste ord animation er kun for begge modes både chat
 * og code». Præmissen var ikke bevist nogen vegne: alle syv eksisterende
 * målinger åbnede bænken i `.chatview`, så ingen af dem kunne sige om halen
 * også kører i code-fladens `.raekkevisning`. En måling der kun ser den ene
 * flade er grøn af den forkerte grund når spørgsmålet er om BEGGE virker.
 *
 * Koden er fælles (`MarkdownRenderer` → `MarkdownBlok` med `hale`), men det er
 * en PÅSTAND om koden, ikke et bevis. Det der kan gå galt er CSS-konteksten:
 * `.streaming-word-tail` er defineret i `chat-reading.css`, som hedder «chat» i
 * navnet. Her måles det: samme tekst, samme spring, to rammer — og tallene
 * skal være ens.
 *
 * Målt på klasserne, ikke på `jarvis-stream-word`: det er et hast-tag, og
 * `StreamingWord` renderer et `<span>`, så tag-navnet findes aldrig i DOM'en.
 */
import { describe, expect, it } from 'vitest'
import { aabnBaenk } from './streamingTextTail.baenk'

const SPRING = 90

interface FladeMaaling {
  ordIAlt: number
  antalSpans: number
  haleOrd: string[]
  sidsteHarHale: boolean
  /** `animationstart` for `streaming-word-color` — beviset på at uret faktisk
   *  blev startet, ikke bare at klassen stod på elementet. */
  farveStart: number
  /** Antal ord hvis målte farve var animationsfarven (blå) undervejs. */
  blaOrd: number
  /** Ord der bærer palettens accentfarve — det farve-uafhængige bevis. */
  accentOrd: number
}

async function maalFlade(flade: 'chat' | 'code', tekst: string): Promise<FladeMaaling> {
  const baenk = await aabnBaenk({ theme: 'dark', flade })
  try {
    await baenk.page.evaluate(() => {
      const w = window as unknown as { __ev: { navn: string }[] }
      w.__ev = []
      document.addEventListener(
        'animationstart',
        (e) => {
          const a = e as AnimationEvent
          w.__ev.push({ navn: a.animationName })
        },
        true,
      )
    })

    await baenk.page.evaluate(
      (t) => (window as unknown as { __saetTekst: (s: string) => void }).__saetTekst(t),
      tekst,
    )
    await baenk.page.waitForTimeout(SPRING)

    const fund = await baenk.page.evaluate(() => {
      const w = window as unknown as { __ev: { navn: string }[] }
      const spans = Array.from(
        document.querySelectorAll('#krop span.streaming-word-tail, #krop span.streaming-word-settled'),
      ) as HTMLElement[]
      // Den blå er `#3a83f7` = rgb(58, 131, 247). Vi tæller ord der måles i
      // nærheden af den, uanset om animationen lige er startet eller midt i.
      const erBlaa = (farve: string) => {
        const m = farve.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
        if (!m) return false
        const [, r, g, b] = m.map(Number) as [string, number, number, number]
        return Math.abs(r - 58) < 60 && Math.abs(g - 131) < 60 && Math.abs(b - 247) < 60
      }
      return {
        antalSpans: spans.length,
        haleOrd: spans
          .filter((s) => s.className.includes('streaming-word-tail'))
          .map((s) => (s.textContent ?? '').trim()),
        sidsteHarHale: (spans[spans.length - 1]?.className ?? '').includes('streaming-word-tail'),
        farveStart: w.__ev.filter((e) => e.navn === 'streaming-word-color').length,
        blaOrd: spans.filter((s) => erBlaa(getComputedStyle(s).color)).length,
        // 20/11-2026: farven er ikke længere en fast blå men palettens accent
        // (Bjørn: «farven skal følge farve paletten valgt i desk»). Derfor
        // måles også ord hvis BEREGNEDE farve afviger fra brødtekstens.
        accentOrd: spans.filter((s) => getComputedStyle(s).color
          !== getComputedStyle(document.getElementById('krop')!).color).length,
        // 20/11-2026 (Bjørn: «palettes farve … skal den vaere skarpere»):
        // ankomsten baerer nu en kort gloed i accentfarven. Den maales som en
        // BEREGNET text-shadow der ikke er `none` — det er det eneste bevis
        // der kan skelne «skarpere» fra «en anden hex», og det virker uanset
        // om temaet er moerkt (hvor --accent og --accent-text er ens).
        gloedOrd: spans.filter((s) => {
          const skygge = getComputedStyle(s).textShadow
          return Boolean(skygge) && skygge !== 'none'
        }).length,
      }
    })

    expect(baenk.fejl).toEqual([])
    return {
      ordIAlt: tekst.split(' ').filter(Boolean).length,
      ...fund,
    }
  } finally {
    await baenk.luk()
  }
}

describe('ordhalen i begge flader', () => {
  it('kører i chat og i code — samme pakning, samme farve-ur', async () => {
    // Seks ord uden efterfølgende mellemrum, som SSE leverer dem. Halen er de
    // sidste tre (`STREAMING_TAIL_WORD_LIMIT`); resten skal stå `settled`.
    const tekst = 'ord1 ord2 ord3 ord4 ord5 ord6'

    const chat = await maalFlade('chat', tekst)
    const code = await maalFlade('code', tekst)

    console.log('[FLADER chat]', JSON.stringify(chat))
    console.log('[FLADER code]', JSON.stringify(code))

    // 1. Alle ord skal være pakket i BEGGE flader — ellers er det nyeste ord rå
    //    tekst uden animation.
    expect({ flade: 'chat', spans: chat.antalSpans, ord: chat.ordIAlt })
      .toEqual({ flade: 'chat', spans: chat.ordIAlt, ord: chat.ordIAlt })
    expect({ flade: 'code', spans: code.antalSpans, ord: code.ordIAlt })
      .toEqual({ flade: 'code', spans: code.ordIAlt, ord: code.ordIAlt })

    // 2. De sidste tre ord skal bære halen — i begge.
    expect(chat.haleOrd).toEqual(['ord4', 'ord5', 'ord6'])
    expect(code.haleOrd).toEqual(['ord4', 'ord5', 'ord6'])

    // 3. Farven skal faktisk være ANVENDT i begge. `animationstart` blev målt
    //    til 0 i BEGGE flader — ikke som et produktfund, men fordi lytteren
    //    først blev installeret efter bænken havde renderet, og animationen
    //    startede ved første render. Det var min måling der var skæv, ikke
    //    produktet. `blaOrd` er det ægte bevis: den læser den BEREGNEDE farve
    //    på de pakkede ord, uanset hvornår uret startede.
    expect(chat.accentOrd).toBe(3)
    expect(code.accentOrd).toBe(3)

    // 4. Og de målte tal skal være ENS. Er de ikke det, er det CSS-konteksten
    //    der gør forskellen — og så er halen reelt kun for én flade.
    expect({
      spans: code.antalSpans,
      hale: code.haleOrd,
      sidsteHarHale: code.sidsteHarHale,
    }).toEqual({
      spans: chat.antalSpans,
      hale: chat.haleOrd,
      sidsteHarHale: chat.sidsteHarHale,
    })
  }, 90_000)
})
