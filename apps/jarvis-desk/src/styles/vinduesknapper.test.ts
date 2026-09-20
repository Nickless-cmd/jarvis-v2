/**
 * Panelernes hoveder må ikke ligge under vinduets egne knapper.
 *
 * Bjørn 20/9-2026, fire skærmbilleder: «et problem med alle paneler i desk i
 * højre side… ikoner der overlapper». Samme fejl fire steder — panelets eget
 * kryds lå oven i vinduets luk-knap.
 *
 * Roden er to ting der begge er ønskede: vinduesknapperne er `position: fixed`
 * i hjørnet (16/9: de er vinduets ENESTE knapper, så de må ikke forsvinde med
 * en header), og de højre ruder går helt op til kanten (16/9: «baggrundjob og
 * changes paneler skal gaa laengere op»). Chat-headeren fik sin plads
 * reserveret 19/9; panelerne fik den aldrig.
 *
 * Testen vogter to ting, og det er dem der kan rådne: at reglen bruger SAMME
 * mål som knapperne (ændrer nogen knap-størrelsen, følger pladsen med), og at
 * hver klasse i den faktisk RENDERES af en komponent. En CSS-regel mod en
 * klasse ingen skriver, er en rettelse der ser ud til at virke.
 */
import { describe, expect, it } from 'vitest'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const app = readFileSync(join(__dirname, 'app.css'), 'utf8')

/** Reglen der holder panel-hovederne fri af knapperne. */
const regel = app.slice(
  app.indexOf('body.egen-ramme .code-right-stack > *:first-child > .changes-head'),
).split('}')[0]

const KLASSER = ['changes-head', 'jobs-head', 'artifact-head', 'codepanel-head']

describe('vinduesknapperne og panel-hovederne', () => {
  it('reserverer plads i hvert af de fire hoveder der ligger øverst til højre', () => {
    for (const k of KLASSER) expect(regel).toContain(`.${k}`)
  })

  it('bruger SAMME mål som knapperne — ikke et nyt tal ved siden af', () => {
    // `--vk-plads` regnes ud af knap-størrelse, mellemrum og kant ét sted.
    // Et hårdkodet «96px» her ville holde indtil nogen ændrede knapperne.
    expect(regel).toMatch(/padding-right:\s*var\(--vk-plads\)/)
    expect(app).toMatch(/--vk-plads:\s*calc\(/)
  })

  it('rammer kun den ØVERSTE rude i skinnen', () => {
    // De nedenunder har knapperne langt over sig; padding dér ville bare
    // efterlade et tomt hul i hvert panelhoved.
    expect(regel).toContain('> *:first-child >')
  })

  it('hver klasse renderes FAKTISK af en komponent', () => {
    // Den fælde huset kender: en CSS-regel mod en klasse ingen skriver.
    const kilde = execFileSync('grep', ['-rl', '--include=*.tsx', '-e', 'className', 'src'],
                               { cwd: join(__dirname, '..', '..'), encoding: 'utf8' })
    const filer = kilde.trim().split('\n')
    const alt = filer.map((f) => readFileSync(join(__dirname, '..', '..', f), 'utf8')).join('\n')
    for (const k of KLASSER) {
      expect(alt).toContain(`"${k}"`)
    }
  })
})
