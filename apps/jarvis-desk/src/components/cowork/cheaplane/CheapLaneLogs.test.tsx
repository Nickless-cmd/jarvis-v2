/**
 * Logsøgningen: serveren søger, ikke klienten.
 *
 * 90.000 kald kan ikke ligge i en browser, og en klient-side-filtrering ville
 * kun kunne søge i den side der tilfældigvis var hentet — og se rigtig ud
 * imens. Derfor går hvert filter til serveren, og markøren følger dens
 * `next_cursor`.
 *
 * Og det vigtigste: en udeladt payload skal SIGE at den er udeladt. En tom
 * prompt-boks ser ud som et kald uden prompt, hvilket er en helt anden — og
 * forkert — historie end «redigeringen fejlede, så vi gemte den ikke».
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CheapLaneLogs } from './CheapLaneLogs'

const side1 = {
  items: [
    { invocation_id: 'inv-1', at: '2026-09-18T09:00:00Z', provider: 'groq', model: 'llama',
      status: 'error', error_class: 'timeout', error: 'read timed out', latency_ms: 30000,
      correlation_id: 'corr-1', has_payload: true },
  ],
  next_cursor: 'cursor-2', count: 1,
}

let hentLogs: ReturnType<typeof vi.fn>
let hentDetalje: ReturnType<typeof vi.fn>

function opsæt(detalje?: Record<string, unknown>) {
  hentLogs = vi.fn().mockResolvedValue(side1)
  hentDetalje = vi.fn().mockResolvedValue(detalje ?? {
    invocation_id: 'inv-1', provider: 'groq', model: 'llama', status: 'error',
    request_payload: null, response_payload: null, redacted: false,
  })
  render(<CheapLaneLogs hentLogs={hentLogs} hentDetalje={hentDetalje} timer={24} />)
  return { bruger: userEvent.setup() }
}

beforeEach(() => { vi.restoreAllMocks() })

describe('CheapLaneLogs', () => {
  it('henter fra serveren med det samme', async () => {
    opsæt()
    await waitFor(() => expect(hentLogs).toHaveBeenCalled())
    expect(await screen.findByText('read timed out')).toBeTruthy()
  })

  it('sender filteret til SERVEREN og følger dens markør', async () => {
    const { bruger } = opsæt()
    await waitFor(() => expect(hentLogs).toHaveBeenCalled())
    await bruger.type(screen.getByRole('searchbox'), 'timeout')
    await waitFor(() => expect(hentLogs).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: 'timeout' })), { timeout: 2000 })

    await bruger.click(screen.getByRole('button', { name: /næste side/i }))
    await waitFor(() => expect(hentLogs).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: 'timeout', cursor: 'cursor-2' })))
  })

  it('et nyt filter starter forfra — ikke midt i den gamle søgning', async () => {
    const { bruger } = opsæt()
    await waitFor(() => expect(hentLogs).toHaveBeenCalled())
    await bruger.click(screen.getByRole('button', { name: /næste side/i }))
    await bruger.type(screen.getByRole('searchbox'), 'x')
    await waitFor(() => {
      const sidste = hentLogs.mock.calls.at(-1)?.[0]
      expect(sidste?.cursor ?? '').toBe('')
    }, { timeout: 2000 })
  })

  it('en udeladt payload siger det — en tom boks ville lyve', async () => {
    const { bruger } = opsæt()
    await waitFor(() => expect(hentLogs).toHaveBeenCalled())
    await bruger.click(await screen.findByRole('button', { name: /inv-1/ }))
    expect(await screen.findByText(/ingen payload er gemt/i)).toBeTruthy()
  })

  it('payload vises som ren tekst — aldrig som markup', async () => {
    // Detaljen skal saettes FOER opsaet: ellers overskriver opsaet mocken, og
    // testen maaler sin egen fikstur i stedet for komponenten.
    const { bruger } = opsæt({
      invocation_id: 'inv-1', request_payload: '<img src=x onerror=alert(1)>',
      response_payload: 'ok', redacted: true,
    })
    await waitFor(() => expect(hentLogs).toHaveBeenCalled())
    await bruger.click(await screen.findByRole('button', { name: /inv-1/ }))
    const pre = await screen.findByText(/<img src=x onerror=alert\(1\)>/)
    expect(pre.tagName).toBe('PRE')
    expect(document.querySelector('img[src="x"]')).toBeNull()
  })

  it('siger det når vinduet er tomt frem for at vise en tom tabel', async () => {
    hentLogs = vi.fn().mockResolvedValue({ items: [], next_cursor: null, count: 0 })
    render(<CheapLaneLogs hentLogs={hentLogs} hentDetalje={vi.fn()} timer={24} />)
    expect(await screen.findByText(/ingen kald matcher/i)).toBeTruthy()
  })
})
