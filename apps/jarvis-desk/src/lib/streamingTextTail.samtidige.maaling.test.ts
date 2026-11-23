// @vitest-environment node
/**
 * Hvor MANGE ord er accent-farvede på samme tid — målt i Chromium.
 *
 * BAGGRUND (Bjørn 23/11-2026): «ord for ord animationen køre så hurtigt det
 * næsten virker klumperne … og ikke 5 ord, 2 max 3».
 *
 * Halen er `STREAMING_TAIL_WORD_LIMIT = 3`, så det er ikke antallet af ord der
 * FÅR klassen der er problemet. `StreamingWord` fryser sin klasse ved første
 * render, så et ord der forlader de sidste tre animerer FÆRDIGT. Ved hurtig
 * pacing hober ordene sig derfor op: flere er accent-farvede samtidigt end de
 * tre, og teksten ligner en farveblok der vandrer.
 *
 * TO MÅLEFÆLDER, begge ramt i første udgave:
 *  1. Ordets TEKST som identitet — under SSE vokser det («o»→«or»→«ord1»), så
 *     ét ord blev talt som tre. Her bruges `data-stream-part-key`, hvis første
 *     led er ordets POSITION.
 *  2. `addStyleTag` til at overskrive konfigurationen — `--streaming-tail-*`
 *     sættes som INLINE style pr. ord, og inline slår en CSS-regel. Alle fem
 *     konfigurationer målte derfor identisk. Her erstattes keyframes via CSSOM,
 *     og variablerne overskrives med `!important`.
 *
 * Gates som de øvrige målinger: RUN_BROWSER_LAYOUT_MEASUREMENT=1.
 */
import { describe, expect, it } from 'vitest'
import { PACE_ANKOMST_VINDUE_S, PACE_GULV, naesteRate, startPace, type RateTilstand } from './paceRate'
import { aabnBaenk, ordTekst } from './streamingTextTail.baenk'

const KOERT = process.env.RUN_BROWSER_LAYOUT_MEASUREMENT === '1'
const FRAME_S = 1 / 60

/** Samme pacer-replikering som `streamingTextTail.rytme.maaling.test.ts`. */
function pacerSkema(total: number, ankomst: (frame: number) => number | null): { t: number; shown: number }[] {
  let shown = 0, rate = PACE_GULV, maal = 0, vStartMaal = 0, vStartTid = 0, kredit = 0
  let tilstand: RateTilstand = startPace()
  const ud: { t: number; shown: number }[] = []
  for (let frame = 1; shown < total && frame < 100_000; frame++) {
    const nu = frame * FRAME_S
    const v = ankomst(frame)
    if (v !== null) maal = Math.min(total, maal + v)
    const pending = Math.max(0, maal - shown)
    if (pending <= 0 && maal < total) continue
    const dtA = vStartTid > 0 ? nu - vStartTid : 0
    const vindueUde = dtA >= PACE_ANKOMST_VINDUE_S
    const a = maal - vStartMaal > 0 && vindueUde ? (maal - vStartMaal) / dtA : null
    if (vindueUde || vStartTid === 0) { vStartMaal = maal; vStartTid = nu }
    const paceSvar = naesteRate({ pending, forrigeRate: rate, ankomst: a, dt: FRAME_S, tilstand })
    rate = paceSvar.rate
    tilstand = paceSvar.tilstand
    const maks = Math.max(6, Math.ceil(rate * 0.1))
    kredit = Math.min(maks, kredit + rate * FRAME_S)
    const step = Math.min(maks, Math.floor(kredit))
    if (step > 0) { kredit -= step; shown = Math.min(maal, shown + step); ud.push({ t: Math.round(nu * 1000), shown }) }
  }
  return ud
}

const JAEVN = '0% { color: var(--accent); } 100% { color: var(--fg-1); }'

type Konfig = { navn: string; keyframes?: string; vars?: string }

const KONFIGURATIONER: Konfig[] = [
  { navn: 'IMPLEMENTERET (120ms farve, delay40, jaevn)' },
  { navn: 'KONTROL: gammel (220ms, delay99, 70% hold)', keyframes: '0% { color: var(--accent); } 70% { color: var(--accent); } 100% { color: var(--fg-1); }', vars: '--streaming-tail-color-duration: 220ms !important; --streaming-tail-color-delay: 99ms !important;' },
]

/** Farvebanens FORM for ét ord: hvor mange frames den bevæger sig, og det
 *  største spring mellem to frames. Et hop har få frames og et stort spring. */
const FORM: { navn: string; keyframes?: string; vars?: string }[] = [
  { navn: 'IMPLEMENTERET' },
  { navn: 'KONTROL: gammel', keyframes: '0% { color: var(--accent); } 70% { color: var(--accent); } 100% { color: var(--fg-1); }', vars: '--streaming-tail-color-duration: 220ms !important; --streaming-tail-color-delay: 99ms !important;' },
]

const FULD = ordTekst(60)
// «normal» fra rytme-målingen: ~40 tegn hver 100 ms.
const SKEMA = pacerSkema(FULD.length, (f) => (f % 6 === 0 ? 40 : null))

describe.skipIf(!KOERT)('antal ord der er accent-farvede samtidigt', () => {
  for (const k of KONFIGURATIONER) {
    it(`${k.navn}: maks antal samtidige accent-ord`, async () => {
      const b = await aabnBaenk({ theme: 'dark' })
      try {
        const { page } = b
        const m = await page.evaluate(async (args) => {
          const { fuld, skema, keyframes, vars } = args as { fuld: string; skema: { t: number; shown: number }[]; keyframes?: string; vars?: string }
          const w = window as any
          // 1. Erstat keyframes via CSSOM — deterministisk, uafhængigt af cascade.
          if (keyframes) {
            for (const sheet of Array.from(document.styleSheets)) {
              let rules: CSSRule[] = []
              try { rules = Array.from(sheet.cssRules) } catch { continue }
              for (let i = rules.length - 1; i >= 0; i--) {
                const r = rules[i] as CSSKeyframesRule
                if (r.type === CSSRule.KEYFRAMES_RULE && r.name === 'streaming-word-color') {
                  sheet.deleteRule(i)
                }
              }
              sheet.insertRule(`@keyframes streaming-word-color { ${keyframes} }`, sheet.cssRules.length)
            }
          }
          // 2. Variabel-override med !important — slår ordets inline style.
          if (vars) {
            const st = document.createElement('style')
            st.textContent = `.streaming-word-tail { ${vars} }`
            document.head.appendChild(st)
          }
          // 3. Sanity: er keyframes faktisk skiftet?
          let kfTekst = ''
          for (const sheet of Array.from(document.styleSheets)) {
            let rules: CSSRule[] = []
            try { rules = Array.from(sheet.cssRules) } catch { continue }
            for (const r of rules) {
              const kr = r as CSSKeyframesRule
              if (kr.type === CSSRule.KEYFRAMES_RULE && kr.name === 'streaming-word-color') kfTekst = kr.cssText
            }
          }
          const prover: { t: number; nokkel: string; color: string }[] = []
          let stop = false
          const prov = () => {
            if (stop) return
            const t = performance.now()
            document.querySelectorAll('#krop span').forEach((n) => {
              const el = n as HTMLElement
              const nokkel = (el.dataset.streamPartKey ?? '').split(':')[0]
              if (!nokkel) return
              prover.push({ t, nokkel, color: getComputedStyle(el).color })
            })
            requestAnimationFrame(prov)
          }
          requestAnimationFrame(prov)
          const t0 = performance.now()
          let i = 0
          await new Promise<void>((klar) => {
            const tick = () => {
              const nu = performance.now() - t0
              while (i < skema.length && skema[i]!.t <= nu) {
                w.__saetTekst(fuld.slice(0, skema[i]!.shown))
                i++
              }
              if (i < skema.length) requestAnimationFrame(tick); else klar()
            }
            requestAnimationFrame(tick)
          })
          await new Promise((r) => setTimeout(r, 900))
          stop = true
          return { prover, kfTekst }
        }, { fuld: FULD, skema: SKEMA, keyframes: k.keyframes, vars: k.vars })

        // Slutfarven er brødtekstens `--fg-1` (mørkt tema: rgb(240, 239, 236)).
        const perFrame = new Map<number, Set<string>>()
        for (const p of m.prover) {
          if (p.color.includes('240, 239, 236')) continue
          const f = Math.round(p.t / (1000 / 60))
          if (!perFrame.has(f)) perFrame.set(f, new Set())
          perFrame.get(f)!.add(p.nokkel)
        }
        const antal = [...perFrame.values()].map((s) => s.size).filter((n) => n > 0)
        const maks = antal.length ? Math.max(...antal) : 0
        const fordeling: Record<number, number> = {}
        for (const n of antal) fordeling[n] = (fordeling[n] ?? 0) + 1
        const over3 = antal.filter((n) => n > 3).length
        console.info('[SAMTIDIGE]', k.navn, JSON.stringify({ frames: antal.length, maks, over3, fordeling }), '| kf:', m.kfTekst.slice(0, 90))
        expect(b.fejl).toEqual([])
        // VAGT: den nye konfiguration maa ikke hobe sig op som den gamle.
        // Maalt 23/11-2026: 68/171 frames over 3 ord (40 %) mod 153/180 (85 %)
        // foer. Graensen er sat midt imellem, saa den fanger en tilbagegang
        // uden at flakke paa en enkelt burst.
        if (k.navn.startsWith('IMPLEMENTERET')) {
          expect(over3 / antal.length).toBeLessThan(0.6)
        }
      } finally {
        await b.luk()
      }
    }, 60_000)
  }
})


describe.skipIf(!KOERT)('farvebanens form for ét ord', () => {
  for (const k of FORM) {
    it(`${k.navn}: hvor mange frames bevæger farven sig`, async () => {
      const b = await aabnBaenk({ theme: 'dark' })
      try {
        const { page } = b
        const m = await page.evaluate(async (args) => {
          const { keyframes, vars } = args as { keyframes?: string; vars?: string }
          const w = window as any
          if (keyframes) {
            for (const sheet of Array.from(document.styleSheets)) {
              let rules: CSSRule[] = []
              try { rules = Array.from(sheet.cssRules) } catch { continue }
              for (let i = rules.length - 1; i >= 0; i--) {
                const r = rules[i] as CSSKeyframesRule
                if (r.type === CSSRule.KEYFRAMES_RULE && r.name === 'streaming-word-color') sheet.deleteRule(i)
              }
              sheet.insertRule(`@keyframes streaming-word-color { ${keyframes} }`, sheet.cssRules.length)
            }
          }
          if (vars) {
            const st = document.createElement('style')
            st.textContent = `.streaming-word-tail { ${vars} }`
            document.head.appendChild(st)
          }
          const prover: { t: number; color: string; nokkel: string }[] = []
          let stop = false
          const prov = () => {
            if (stop) return
            const t = performance.now()
            document.querySelectorAll('#krop span').forEach((n) => {
              const el = n as HTMLElement
              const nokkel = (el.dataset.streamPartKey ?? '').split(':')[0]
              if (!nokkel) return
              prover.push({ t, nokkel, color: getComputedStyle(el).color })
            })
            requestAnimationFrame(prov)
          }
          requestAnimationFrame(prov)
          // Ét ord, én ankomst — så banen ikke blandes med naboer.
          w.__saetTekst('alfa ')
          await new Promise((r) => setTimeout(r, 700))
          stop = true
          return { prover }
        }, { keyframes: k.keyframes, vars: k.vars })

        const rgb = (s: string) => (s.match(/\d+/g) ?? []).map(Number)
        // Første ords bane: alle prøver med nøgle '0'.
        const bane = m.prover.filter((p) => p.nokkel === '0').map((p) => rgb(p.color))
        const unikke: number[][] = []
        for (const c of bane) {
          const forrige = unikke[unikke.length - 1]
          if (!forrige || forrige.join() !== c.join()) unikke.push(c)
        }
        // RØDkanal: accent #6ee7a8 = 110, slut #f0efec = 240 — 130 trins
        // afstand. Grønkanalen gaar 231 → 239 og kan næsten ikke skelne dem.
        const roed = unikke.map((c) => c[0] ?? 0)
        const spring = roed.slice(1).map((g, i) => Math.abs(g - roed[i]!))
        const stoerste = spring.length ? Math.max(...spring) : 0
        console.info('[FORM]', k.navn, JSON.stringify({ skridt: unikke.length, stoersteSpring: stoerste }))
        expect(b.fejl).toEqual([])
        // VAGT: farven skal GLIDE, ikke hoppe. Maalt 23/11-2026: 9 skridt og
        // stoerste spring 36 mod 5 skridt og 58 foer. Et hop er faa skridt
        // med et stort spring — praecis det Bjørn kaldte «klumper».
        if (k.navn === 'IMPLEMENTERET') {
          expect(unikke.length).toBeGreaterThanOrEqual(7)
          expect(stoerste).toBeLessThanOrEqual(50)
        }
      } finally {
        await b.luk()
      }
    }, 60_000)
  }
})
