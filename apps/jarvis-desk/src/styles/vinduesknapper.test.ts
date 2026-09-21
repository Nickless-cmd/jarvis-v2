/**
 * Panelernes hoveder må ikke ligge under vinduets egne knapper.
 *
 * Bjørn 20/9-2026, fire skærmbilleder: «et problem med alle paneler i desk i
 * højre side… ikoner der overlapper». Samme fejl fire steder — panelets eget
 * kryds lå oven i vinduets luk-knap.
 *
 * Roden er to ting der begge er ønskede: vinduesknapperne er `position: fixed`
 * i hjørnet (16/9: de er vinduets ENESTE knapper, så de må ikke forsvinde med
 * en header), og de højre ruder gik helt op til kanten (16/9: «baggrundjob og
 * changes paneler skal gaa laengere op»).
 *
 * ## To forskellige svar, fordi der er to forskellige tilfælde (21/9-2026)
 *
 * Skinnens ruder er SÆNKET: `.code-right-stack` starter under trækbjælken, så
 * hele stakken begynder fri af knapperne («de skal sænkes lidt så de bliver
 * under luk x knappen»). Deres hoveder har dermed ingen padding — de får hele
 * bredden igen, hvilket er hele pointen med at sænke frem for at lappe.
 *
 * Artefakt- og kodepanelet ligger stadig højt og kan ikke sænkes uden at tabe
 * plads. De beholder `--vk-plads`.
 *
 * Testen vogter derfor tre ting, og det er dem der kan rådne: at skinnen
 * faktisk ligger lavt nok, at de to høje hoveder bruger SAMME mål som
 * knapperne (ændrer nogen knap-størrelsen, følger pladsen med), og at hver
 * klasse i reglen faktisk RENDERES af en komponent. En CSS-regel mod en
 * klasse ingen skriver, er en rettelse der ser ud til at virke.
 */
import { describe, expect, it } from 'vitest'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const app = readFileSync(join(__dirname, 'app.css'), 'utf8')

/** Reglen der holder de to HØJE panel-hoveder fri af knapperne. */
const regel = app.slice(app.indexOf('body.egen-ramme .artifact-head')).split('}')[0] ?? ''

/** Skinnen selv — den løser sit eget tilfælde ved at ligge lavere. */
const skinne = app.slice(app.indexOf('.code-right-stack {')).split('}')[0] ?? ''

const HOEJE = ['artifact-head', 'codepanel-head']
const I_SKINNEN = ['changes-head', 'jobs-head']

describe('vinduesknapperne og panel-hovederne', () => {
  it('sænker skinnen fri af knapperne i stedet for at lappe dens hoveder', () => {
    // Knapperne: top 6 px, 24 px høje → slutter ved 30. Trækbjælken er 36.
    const top = /top:\s*(\d+)px/.exec(skinne)
    expect(top).not.toBeNull()
    expect(Number(top![1])).toBeGreaterThanOrEqual(30)
  })

  it('giver IKKE skinnens hoveder padding — de skal have hele bredden', () => {
    // Lappen stod her indtil 21/9. Kommer den igen, har nogen sat `top`
    // tilbage til 0 uden at sige det.
    for (const k of I_SKINNEN) expect(regel).not.toContain(`.${k}`)
  })

  it('reserverer plads i de to hoveder der stadig ligger øverst til højre', () => {
    for (const k of HOEJE) expect(regel).toContain(`.${k}`)
  })

  it('bruger SAMME mål som knapperne — ikke et nyt tal ved siden af', () => {
    // `--vk-plads` regnes ud af knap-størrelse, mellemrum og kant ét sted.
    // Et hårdkodet «96px» her ville holde indtil nogen ændrede knapperne.
    expect(regel).toMatch(/padding-right:\s*var\(--vk-plads\)/)
    expect(app).toMatch(/--vk-plads:\s*calc\(/)
  })

  it('hver klasse renderes FAKTISK af en komponent', () => {
    // Den fælde huset kender: en CSS-regel mod en klasse ingen skriver.
    const kilde = execFileSync('grep', ['-rl', '--include=*.tsx', '-e', 'className', 'src'],
                               { cwd: join(__dirname, '..', '..'), encoding: 'utf8' })
    const filer = kilde.trim().split('\n')
    const alt = filer.map((f) => readFileSync(join(__dirname, '..', '..', f), 'utf8')).join('\n')
    for (const k of [...HOEJE, ...I_SKINNEN]) {
      expect(alt).toContain(`"${k}"`)
    }
  })
})
