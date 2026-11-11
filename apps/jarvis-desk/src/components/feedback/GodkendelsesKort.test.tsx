import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GodkendelsesKort } from './GodkendelsesKort'
import * as useStreamHook from '../../hooks/useStream'
import * as useSettingsHook from '../../hooks/useSettings'

/**
 * Kortet skal staa der hvor han staar.
 *
 * Bjoerns symptom, gentaget over maaneder: «jeg kan sidde i en samtale i desk
 * og tro han er staaet af, fordi mobilen har overtaget og approval-kortet er
 * landet der.»
 *
 * Maalt 25/9-2026: `ApprovalCard` blev renderet ÉT sted i hele desk —
 * `CodeView.tsx:1200`. Paa chat-fladen fandtes kortet slet ikke. Tilstanden
 * (`stream.pendingApproval`) laa hele tiden i den delte StreamContext; kun
 * tegningen manglede. Det var aldrig en overtagelse.
 *
 * Foerste udgave af denne test gav `initialAuth` til `SettingsProvider` — en
 * prop der ikke findes. Den blev ignoreret, saa rolle-testen maalte ingenting.
 * `tsc -b` fangede det; `tsc --noEmit` gjorde ikke. Derfor mockes hooken.
 */
afterEach(() => { vi.restoreAllMocks() })

function vis(p: unknown, rolle: string | null = 'owner', sessionId: string | null = 'session-a') {
  vi.spyOn(useStreamHook, 'useStream').mockReturnValue({
    pendingApproval: p, approve: vi.fn(), deny: vi.fn(),
  } as unknown as ReturnType<typeof useStreamHook.useStream>)
  vi.spyOn(useSettingsHook, 'useSettings').mockReturnValue({
    settings: { apiBaseUrl: 'http://x/', authToken: 't' },
    auth: rolle ? { user_id: 'u', display_name: 'B', role: rolle } : null,
  } as unknown as ReturnType<typeof useSettingsHook.useSettings>)
  return render(<GodkendelsesKort sessionId={sessionId} />)
}

const kort = { approvalId: 'a1', tool: 'bash', action: 'ls -la', sessionId: 'session-a' }

/** En AGENT-godkendelse (11/11-2026). Den blokerer ingen stream — den parkerer et
 *  assignment — saa den hoerer ikke til en samtale paa samme maade som en
 *  tool-godkendelse. `kind` er det der skiller de to. */
const agentKort = { ...kort, kind: 'agent' as const, digest: 'd1' }

describe('GodkendelsesKort', () => {
  it('tegner kortet naar der venter en godkendelse', () => {
    vis(kort)
    expect(screen.getByText(/bash/i)).toBeInTheDocument()
  })

  it('tegner intet naar der ikke venter nogen', () => {
    const { container } = vis(null)
    expect(container.innerHTML).toBe('')
  })

  it('viser ikke et kort fra en anden session', () => {
    const { container } = vis(kort, 'owner', 'session-b')
    expect(container.innerHTML).toBe('')
  })

  it('viser ikke et kort uden en aktiv session', () => {
    const { container } = vis(kort, 'owner', null)
    expect(container.innerHTML).toBe('')
  })

  // ── Agent-godkendelser: sessionen maa ikke skjule dem (11/11-2026) ────────
  //
  // Bjoerns klage: «jeg skal have panelet aaben naar du kalder en agent jeg skal
  // godkende ellers ser jeg dem ikke … approvals burde kun lande over composer.»
  //
  // En agent startet fra en ANDEN samtale (eller fra en autonom koersel) lagde
  // sit kort i en session han ikke stod i. Gaten skjulte det, og tilbage var
  // kun panel-raekken. Det er praecis den fejl disse to tests værner imod.
  it('viser en agent-godkendelse fra en ANDEN samtale', () => {
    vis(agentKort, 'owner', 'session-b')
    expect(screen.getByText(/bash/i)).toBeInTheDocument()
  })

  it('viser en agent-godkendelse selv uden en aktiv samtale', () => {
    // Den hoerer ikke til en stream, saa der er ingen session at hoere til.
    vis(agentKort, 'owner', null)
    expect(screen.getByText(/bash/i)).toBeInTheDocument()
  })

  it('en tool-godkendelse fra en anden samtale er STADIG skjult', () => {
    // Regression paa den anden side: tool-kortet blokerer sin egen stream, og
    // maa ikke dukke op i en samtale det ikke hoerer til.
    const { container } = vis({ ...kort, kind: 'tool' as const }, 'owner', 'session-b')
    expect(container.innerHTML).toBe('')
  })

  it('ejeren kan svare', () => {
    vis(kort, 'owner')
    expect(screen.getByRole('button', { name: /godkend|tillad/i })).toBeEnabled()
  })

  it('en anden end ejeren kan SE kortet men ikke svare', () => {
    // Kortet skal stadig vises — ellers ser fladen ud som om intet sker.
    // Det er svaret der er ejerens, ikke synligheden.
    vis(kort, 'member')
    expect(screen.getByText(/bash/i)).toBeInTheDocument()
    const knap = screen.queryByRole('button', { name: /godkend|tillad/i })
    expect(knap === null || knap.hasAttribute('disabled')).toBe(true)
  })
})
