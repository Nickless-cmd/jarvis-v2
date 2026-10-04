/**
 * Den udgivne fils række og dens tre handlinger (Bjørn 4/10-2026).
 *
 * Det vigtigste her er ikke at knapperne findes. Det er at de to ÅBNE-veje
 * kun findes på en udgivet fil: en vedhæftning ligger på `/attachments/…`,
 * hvor hverken browser-injektionen eller signeringen rækker, og to knapper
 * der gav 401 ville være værre end ingen.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const { hentSigneretFilLink, fetchBlobWithAuth, downloadBlob } = vi.hoisted(() => ({
  hentSigneretFilLink: vi.fn(),
  fetchBlobWithAuth: vi.fn(),
  downloadBlob: vi.fn(),
}))

vi.mock('../../lib/api', () => ({
  hentSigneretFilLink,
  fetchBlobWithAuth,
  downloadBlob,
  absolutApiUrl: (c: { apiBaseUrl: string }, sti: string) => new URL(sti, c.apiBaseUrl).toString(),
}))
vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'https://api.srvlab.dk', authToken: 't' } }),
}))
vi.mock('./BilledLightbox', () => ({ KlikbartBillede: () => null }))

import { AttachmentBlock } from './AttachmentBlock'

const UDGIVET = { type: 'file' as const, filename: 'oktober-tal.xlsx',
                  url: '/files/oktober-tal.xlsx', size_bytes: 18_842 }
const VEDHAEFTET = { type: 'file' as const, filename: 'upload.pdf',
                     attachment_id: 'abc123', size_bytes: 1024 }

beforeEach(() => {
  vi.clearAllMocks()
  ;(window as unknown as Record<string, unknown>).jarvisDesk = undefined
})

describe('en udgivet fil', () => {
  it('viser alle tre handlinger', () => {
    render(<AttachmentBlock block={UDGIVET} />)
    expect(screen.getByLabelText("Åbn i Jarvis' browser")).toBeTruthy()
    expect(screen.getByLabelText('Åbn i din egen browser')).toBeTruthy()
    expect(screen.getByLabelText('Hent oktober-tal.xlsx')).toBeTruthy()
  })

  it('viser navn og størrelse som en RÆKKE, ikke en chip', () => {
    const { container } = render(<AttachmentBlock block={UDGIVET} />)
    expect(container.querySelector('.fil-raekke')).toBeTruthy()
    // Chippen var husets tredje malede flade. Den må ikke komme igen.
    expect(container.querySelector('.file-block')).toBeNull()
    expect(screen.getByText('oktober-tal.xlsx')).toBeTruthy()
    expect(screen.getByText('18,4 kB')).toBeTruthy()
  })

  it('sender den ABSOLUTTE adresse til Jarvis browser', () => {
    // Relativt ville webvisningen slå op mod sig selv. Det var præcis den
    // fejl der gjorde udgivne filer uåbnelige.
    const aabn = vi.fn()
    ;(window as unknown as Record<string, unknown>).jarvisDesk = { browser: { aabn } }
    render(<AttachmentBlock block={UDGIVET} />)
    screen.getByLabelText("Åbn i Jarvis' browser").click()
    expect(aabn).toHaveBeenCalledWith('https://api.srvlab.dk/files/oktober-tal.xlsx')
  })

  it('henter et SIGNERET link til egen browser — ikke den rå adresse', () => {
    const openExternal = vi.fn()
    ;(window as unknown as Record<string, unknown>).jarvisDesk = { openExternal }
    hentSigneretFilLink.mockResolvedValue(
      'https://api.srvlab.dk/files/oktober-tal.xlsx?udloeb=9&sig=abc')
    render(<AttachmentBlock block={UDGIVET} />)
    screen.getByLabelText('Åbn i din egen browser').click()
    expect(hentSigneretFilLink).toHaveBeenCalledWith(
      { apiBaseUrl: 'https://api.srvlab.dk', authToken: 't' }, 'oktober-tal.xlsx')
    return waitFor(() => {
      expect(openExternal).toHaveBeenCalledWith(
        'https://api.srvlab.dk/files/oktober-tal.xlsx?udloeb=9&sig=abc')
    })
  })

  it('henter linket ved KLIK, ikke når rækken tegnes', () => {
    // Et link pr. visning ville udstede en signatur for hver fil i tråden
    // ved hver render, og de ville være udløbet længe før nogen klikkede.
    render(<AttachmentBlock block={UDGIVET} />)
    expect(hentSigneretFilLink).not.toHaveBeenCalled()
  })

  it('navnet er stadig download — det var chippens eneste handling', () => {
    fetchBlobWithAuth.mockResolvedValue(new Blob(['x']))
    render(<AttachmentBlock block={UDGIVET} />)
    screen.getByText('oktober-tal.xlsx').click()
    expect(fetchBlobWithAuth).toHaveBeenCalledWith(
      { apiBaseUrl: 'https://api.srvlab.dk', authToken: 't' }, '/files/oktober-tal.xlsx')
  })

  it('siger til naar et signeret link ikke kunne hentes', () => {
    ;(window as unknown as Record<string, unknown>).jarvisDesk = { openExternal: vi.fn() }
    hentSigneretFilLink.mockRejectedValue(new Error('503'))
    render(<AttachmentBlock block={UDGIVET} />)
    screen.getByLabelText('Åbn i din egen browser').click()
    return waitFor(() => expect(screen.getByText('kunne ikke hentes')).toBeTruthy())
  })
})

describe('en vedhæftning', () => {
  it('har KUN download — de to åbne-veje rækker ikke til /attachments', () => {
    render(<AttachmentBlock block={VEDHAEFTET} />)
    expect(screen.queryByLabelText("Åbn i Jarvis' browser")).toBeNull()
    expect(screen.queryByLabelText('Åbn i din egen browser')).toBeNull()
    expect(screen.getByLabelText('Hent upload.pdf')).toBeTruthy()
  })
})
