import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GodkendelsesKort } from './GodkendelsesKort'
import { SettingsProvider } from '../../contexts/SettingsContext'
import * as useStreamHook from '../../hooks/useStream'

/**
 * Kortet skal staa der hvor han staar.
 *
 * Bjoerns symptom, gentaget over maaneder: «jeg kan sidde i en samtale i desk
 * og tro han er staaet af, fordi mobilen har overtaget og approval-kortet er
 * landet der.»
 *
 * Maalt 25/9-2026: `ApprovalCard` blev renderet ÉT sted i hele desk —
 * `CodeView.tsx:1200`. Paa chat-fladen fandtes kortet slet ikke. Tilstanden
 * (`stream.pendingApproval`) var der hele tiden i den delte StreamContext; kun
 * tegningen manglede. Det var aldrig en overtagelse.
 */
const cfg = { apiBaseUrl: 'http://x/', authToken: 'tok' }

function medGodkendelse(p: unknown, rolle = 'owner') {
  vi.spyOn(useStreamHook, 'useStream').mockReturnValue({
    pendingApproval: p, approve: vi.fn(), deny: vi.fn(),
  } as unknown as ReturnType<typeof useStreamHook.useStream>)
  return render(
    <SettingsProvider initialConfig={cfg} initialAuth={{ user_id: 'u', display_name: 'B', role: rolle }}>
      <GodkendelsesKort />
    </SettingsProvider>,
  )
}

describe('GodkendelsesKort', () => {
  it('tegner kortet naar der venter en godkendelse', () => {
    medGodkendelse({ approvalId: 'a1', tool: 'bash', action: 'ls -la' })
    expect(screen.getByText(/bash/i)).toBeInTheDocument()
  })

  it('tegner intet naar der ikke venter nogen', () => {
    const { container } = medGodkendelse(null)
    expect(container.innerHTML).toBe('')
  })
})
