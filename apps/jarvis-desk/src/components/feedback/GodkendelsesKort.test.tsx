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

function vis(p: unknown, rolle: string | null = 'owner') {
  vi.spyOn(useStreamHook, 'useStream').mockReturnValue({
    pendingApproval: p, approve: vi.fn(), deny: vi.fn(),
  } as unknown as ReturnType<typeof useStreamHook.useStream>)
  vi.spyOn(useSettingsHook, 'useSettings').mockReturnValue({
    settings: { apiBaseUrl: 'http://x/', authToken: 't' },
    auth: rolle ? { user_id: 'u', display_name: 'B', role: rolle } : null,
  } as unknown as ReturnType<typeof useSettingsHook.useSettings>)
  return render(<GodkendelsesKort />)
}

const kort = { approvalId: 'a1', tool: 'bash', action: 'ls -la' }

describe('GodkendelsesKort', () => {
  it('tegner kortet naar der venter en godkendelse', () => {
    vis(kort)
    expect(screen.getByText(/bash/i)).toBeInTheDocument()
  })

  it('tegner intet naar der ikke venter nogen', () => {
    const { container } = vis(null)
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
