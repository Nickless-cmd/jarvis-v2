/**
 * Et langt værktøjs-resultat sendes afkortet med samtalen (serveren: de
 * første 2.000 tegn af 5,7 MB resultater — 2,5 MB af dem ligger efter
 * grænsen). Resten hentes FØRST når linjen foldes ud.
 *
 * Det farlige her er ikke bytes, men at et resultat ser komplet ud når det
 * ikke er det. Derfor: linjen SIGER det, og udfoldningen henter.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { ToolCard } from './ToolCard'
import type { ContentBlock } from '../../lib/sseProtocol'

const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' }
const HOVED = 'x'.repeat(2000)
const HELE = HOVED + 'RESTEN-AF-OUTPUTTET'

function blok(over: Record<string, unknown> = {}): Extract<ContentBlock, { type: 'tool_use' }> {
  return {
    type: 'tool_use', id: 'call_1', name: 'bash', input: { command: 'ls' },
    status: 'done', result: HOVED, resultAfkortet: true, resultTegnIAlt: 2019,
    ...over,
  } as Extract<ContentBlock, { type: 'tool_use' }>
}

beforeEach(() => {
  global.fetch = vi.fn(async () => ({
    ok: true, status: 200, headers: { get: () => null },
    json: async () => ({ content: HELE, chars: HELE.length }),
  })) as unknown as typeof fetch
})
afterEach(() => vi.restoreAllMocks())

describe('afkortet værktøjs-resultat', () => {
  it('folder man ud, hentes resten og vises', async () => {
    render(<ToolCard block={blok()} density="full" beskedId="m1" config={config} />)
    await waitFor(() => expect(screen.getByText(/RESTEN-AF-OUTPUTTET/)).toBeTruthy())
    const kaldt = String((global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0])
    expect(kaldt).toContain('/chat/messages/m1/tool-result/call_1')
  })

  it('siger hvor meget der mangler indtil resten er hentet', () => {
    global.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch
    render(<ToolCard block={blok()} density="full" beskedId="m1" config={config} />)
    expect(screen.getByText(/henter resten|viser de første/)).toBeTruthy()
  })

  it('henter IKKE så længe linjen er foldet sammen', () => {
    render(<ToolCard block={blok()} density="compact" beskedId="m1" config={config} />)
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('henter når man klikker linjen op', async () => {
    render(<ToolCard block={blok()} density="compact" beskedId="m1" config={config} />)
    fireEvent.click(document.querySelector('.toolcard-head') as HTMLElement)
    await waitFor(() => expect(global.fetch).toHaveBeenCalled())
  })

  it('et HELT resultat henter aldrig noget', () => {
    render(
      <ToolCard block={blok({ result: 'kort', resultAfkortet: undefined, resultTegnIAlt: undefined })}
        density="full" beskedId="m1" config={config} />,
    )
    expect(global.fetch).not.toHaveBeenCalled()
    expect(screen.getByText('kort')).toBeTruthy()
  })

  it('uden config vises det afkortede — ingen tom linje', () => {
    render(<ToolCard block={blok()} density="full" />)
    expect(global.fetch).not.toHaveBeenCalled()
    expect(screen.getByText(/viser de første/)).toBeTruthy()
  })
})
