/**
 * Den hvide i sidebarens fod og i miljø-feltets øverste blok.
 *
 * Bjørn 4/10-2026: «mit navn skal være samme hvid som sessions navnene over
 * navnet.. og bug ikonet skal osse være den hvid... og det øverste felt i
 * miljøfeltet altså ændringer og til og med opret pull request have samme
 * hvid, kontekst og kilder forbliver den farve de har nu».
 *
 * Referencen er `--fg-1` — den farve sessionsnavnene FAKTISK har. `.session-item`
 * står på `--fg-2` i app.css, men `.sidebar .session-item` i chat-reading.css
 * (0,2,0, indlæst sidst) løfter den til `--fg-1`. Den hvide skal matche den
 * viste farve, ikke den første regel der nævner klassen.
 *
 * ## Hvorfor `env-top` og ikke `.env-label` selv
 *
 * `.env-label` bærer OGSÅ RunHealth (Maskine / GPU / Disk / Kontekst) og
 * vælgerne i den samme liste-struktur. Bjørn bad om at kontekst og kilder
 * beholder deres farve. Derfor en klasse på netop den øverste liste.
 *
 * Testen vogter begge sider af den beslutning: at blokken ER blevet hvid, og
 * at RunHealth IKKE blev ramt. En regel der virker ét sted og brækker et andet
 * er ikke en rettelse — og den er usynlig i en diff.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const laes = (n: string) => readFileSync(join(__dirname, n), 'utf8')
const komponent = (n: string) =>
  readFileSync(join(__dirname, '..', 'components', 'code', n), 'utf8')

const app = laes('app.css')
const miljoe = laes('environment-inspector.css')
const panel = komponent('EnvironmentPanel.tsx')
const runHealth = komponent('RunHealth.tsx')

/** Reglen for én selektor, uden kommentarer der kan spise nabo-reglen.
 *  `[^{}]*` frem for `\s*` foran `{`: selektoren kan stå som FØRSTE led i en
 *  kommasepareret liste, og så kommer der flere selektorer før klammerne. */
const regel = (css: string, selektor: string) => {
  const ren = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const m = ren.match(new RegExp(`${selektor}[^{}]*\\{([^}]*)\\}`))
  return m?.[1] ?? ''
}

describe('hvid i sidebar-fod og miljø-felt', () => {
  it('løfter brugernavnet til --fg-1 — samme hvide som sessionsnavnene', () => {
    expect(regel(app, '\\.who-navn')).toMatch(/var\(--fg-1\)/)
  })

  it('løfter bug-ikonet til --fg-1 og lader --fg-3 ligge', () => {
    const r = regel(app, '\\.sidebar-bug')
    expect(r).toMatch(/var\(--fg-1\)/)
    expect(r).not.toMatch(/var\(--fg-3\)/)
  })

  it('giver den øverste blok i miljø-feltet samme hvide', () => {
    const r = regel(miljoe, '\\.env-rows\\.env-top \\.env-label')
    expect(r).toMatch(/var\(--fg-1/)
  })

  it('sætter env-top på netop den øverste liste — og kun der', () => {
    // Klassen skal RENDERES, ikke bare defineres: en regel mod en klasse ingen
    // skriver, ser ud til at virke. Den skal sidde på listen med «Ændringer».
    expect(panel).toMatch(/<ul className="env-rows env-top">\s*<li className="env-row env-changes">/)
    // RunHealth (Maskine/GPU/Disk/Kontekst) må ikke bære den — den beholder
    // sin dæmpede farve.
    expect(runHealth).not.toMatch(/env-top/)
  })
})
