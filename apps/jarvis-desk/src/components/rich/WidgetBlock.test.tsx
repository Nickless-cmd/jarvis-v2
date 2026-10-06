import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { WidgetBlock } from './WidgetBlock'

/**
 * Sandkassen er GRÆNSEN om model-skrevet HTML. De to første tests er derfor de
 * vigtigste i filen: de fejler hvis nogen tilføjer `allow-same-origin` eller
 * peger iframen på en URL i stedet for at lægge dokumentet i `srcdoc`.
 *
 * `allow-scripts` + `allow-same-origin` ophæver tilsammen sandkassen: iframen
 * ville få desks egen origin og kunne læse token, localStorage og DOM.
 */

const config = { apiBaseUrl: 'https://api.test/', authToken: 'hemmelig-token' } as never

function mockHent(html: string, size?: number) {
  const blob = { size: size ?? html.length, text: async () => html } as unknown as Blob
  return vi.fn().mockResolvedValue(blob)
}

let hent: ReturnType<typeof mockHent>

vi.mock('../../lib/api', () => ({
  fetchBlobWithAuth: (...a: unknown[]) => hent(...a),
}))

beforeEach(() => { hent = mockHent('<p>hej</p>') })
afterEach(() => { vi.restoreAllMocks() })

describe('WidgetBlock', () => {
  it('sandkassen tillader scripts men ALDRIG same-origin', async () => {
    render(<WidgetBlock block={{ attachment_id: 'a1', filename: 'w.html' }} config={config} />)
    const ramme = await waitFor(() => screen.getByTitle('w.html'))
    const sandbox = ramme.getAttribute('sandbox') || ''
    expect(sandbox).toContain('allow-scripts')
    expect(sandbox).not.toContain('allow-same-origin')
    expect(sandbox).not.toContain('allow-top-navigation')
    expect(sandbox).not.toContain('allow-popups')
    expect(sandbox).not.toContain('allow-forms')
  })

  it('dokumentet lægges i srcdoc — iframen får ALDRIG en url', async () => {
    render(<WidgetBlock block={{ attachment_id: 'a1', filename: 'w.html' }} config={config} />)
    const ramme = await waitFor(() => screen.getByTitle('w.html'))
    expect(ramme.getAttribute('srcdoc')).toContain('<p>hej</p>')
    expect(ramme.getAttribute('src')).toBeNull()
    // Tokenet må ikke kunne læses af nogen i iframens dokument.
    expect(ramme.getAttribute('srcdoc')).not.toContain('hemmelig-token')
  })

  it('henter fra den DB-backede /media/-sti, ikke sessions-registret', async () => {
    render(<WidgetBlock block={{ attachment_id: 'a-9', filename: 'w.html' }} config={config} />)
    await waitFor(() => expect(hent).toHaveBeenCalled())
    const sti = String(hent.mock.calls[0][1])
    expect(sti).toBe('/attachments/media/a-9')
    // `/attachments/{id}` kender kun denne sessions registry og ville dø ved reload.
    expect(sti).not.toBe('/attachments/a-9')
  })

  it('en widget uden reference siger det frem for at stå tom', async () => {
    render(<WidgetBlock block={{ filename: 'w.html' }} config={config} />)
    expect(await screen.findByText(/uden reference/)).toBeInTheDocument()
  })

  it('et for stort dokument afvises', async () => {
    hent = mockHent('<p>x</p>', 2 * 1024 * 1024)
    render(<WidgetBlock block={{ attachment_id: 'a1', filename: 'w.html' }} config={config} />)
    expect(await screen.findByText(/for stor/)).toBeInTheDocument()
  })

  it('en hentefejl vises som tekst, ikke som en tom rude', async () => {
    hent = vi.fn().mockRejectedValue(new Error('403'))
    render(<WidgetBlock block={{ attachment_id: 'a1', filename: 'w.html' }} config={config} />)
    expect(await screen.findByText(/kunne ikke vises/)).toBeInTheDocument()
  })

  it('en højde-besked fra et FREMMED vindue ignoreres', async () => {
    render(<WidgetBlock block={{ attachment_id: 'a1', filename: 'w.html' }} config={config} />)
    const ramme = await waitFor(() => screen.getByTitle('w.html')) as HTMLIFrameElement
    const foer = ramme.style.height
    // `source` er ikke vores iframe → skal ikke kunne ændre højden.
    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'jarvis-widget-hoejde', hoejde: 999 },
      source: window as unknown as MessageEventSource,
    }))
    await new Promise((r) => setTimeout(r, 0))
    expect(ramme.style.height).toBe(foer)
  })

  it('højde-scriptet følger med dokumentet', async () => {
    render(<WidgetBlock block={{ attachment_id: 'a1', filename: 'w.html' }} config={config} />)
    const ramme = await waitFor(() => screen.getByTitle('w.html'))
    expect(ramme.getAttribute('srcdoc')).toContain('jarvis-widget-hoejde')
  })
})
