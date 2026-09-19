import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

/**
 * Arbejde-fladen: Mission Control ER siden — ikke noget der ligger under fire
 * løse sektioner.
 *
 * Bjørn 15/9-2026: «de 4 bør være under mission control da det er toppen af
 * siden... der findes allerede en felt der hedder agenter foreks. arbejder er
 * dobbelt sandhed... og arbejde er i afventer dig feltet».
 *
 * Målt før omlægningen:
 *
 *   «Arbejde»        /cowork/queue        = MC's «Afventer dig» (samme endpoint)
 *   «Hans arbejdere» /central/agents/work ≈ Agenter-fanen (/central/agents)
 *   Lektier          /review/lessons      — intet modstykke
 *   Arbejdstræet     /review/changes      — intet modstykke
 *
 * Testen er en kilde-vagt: jsdom regner ikke layout, og disse påstande handler
 * om STRUKTUR, ikke om pixels. Den er svagere end at se fladen, og det skal
 * siges. Men den fanger det der ellers ville skride tilbage: at en kopi
 * genopstår, eller at en sektion falder ud af fanen.
 */
const læs = (p: string) => fs.readFileSync(path.join(__dirname, '..', p), 'utf8')

describe('Mission Control er hele Arbejde-fladen', () => {
  it('zonen indeholder KUN Mission Control', () => {
    const v = læs('views/CoworkView.tsx')
    expect(v).toMatch(/case 'mc': return missionControl/)
  })

  it('de fire ligger ikke længere løst ovenover', () => {
    const v = læs('views/CoworkView.tsx')
    // Kun omtale i kommentarer er i orden; en JSX-brug er ikke.
    for (const navn of ['WorkQueue', 'Lektier', 'ReviewPanel', 'AgentWork']) {
      expect(v).not.toContain(`<${navn} `)
    }
  })

  it('duplikatet af koeen er VAEK, ikke bare skjult', () => {
    // Dobbelt sandhed loeses ikke ved at lade kopien ligge som doed kode.
    expect(fs.existsSync(path.join(__dirname, '../components/cowork/WorkQueue.tsx'))).toBe(false)
    expect(fs.existsSync(path.join(__dirname, '../hooks/useWorkQueue.ts'))).toBe(false)
  })

  it('prompt-sammensaetningen overlevede flytningen', () => {
    // Den var WorkQueue's ENESTE unikke funktion. Uden denne ville sletningen
    // have kostet en evne — og ingen anden test ville have opdaget det.
    const rd = læs('components/cowork/missioncontrol/RunDetail.tsx')
    expect(rd).toContain('<PromptSammensaetning')
  })

  it('arbejderne bor under Agenter-fanen', () => {
    const mc = læs('components/cowork/missioncontrol/MissionControl.tsx')
    const fane = mc.slice(mc.indexOf("tab === 'agenter'"))
    expect(fane.slice(0, 700)).toContain('<AgentRoster')
    expect(fane.slice(0, 700)).toContain('<AgentWork')
  })

  it('Lektier og arbejdstraeet har deres egen fane', () => {
    const mc = læs('components/cowork/missioncontrol/MissionControl.tsx')
    expect(mc).toMatch(/\{ id: 'review', label: 'Gennemgang'/)
    const fane = mc.slice(mc.indexOf("tab === 'review'"))
    expect(fane.slice(0, 700)).toContain('<Lektier')
    expect(fane.slice(0, 700)).toContain('<ReviewPanel')
  })

  it('fanen er med i Tab-typen — ellers kan den ikke vaelges', () => {
    const mc = læs('components/cowork/missioncontrol/MissionControl.tsx')
    expect(mc).toMatch(/type Tab =[^\n]*'review'/)
  })
})
