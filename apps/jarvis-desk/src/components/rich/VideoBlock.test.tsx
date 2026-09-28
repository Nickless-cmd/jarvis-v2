import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { VideoBlock } from './VideoBlock'
import { filAdresse } from './AttachmentBlock'
import { foldToolResults } from '../../lib/foldToolResults'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Video i tråden.
 *
 * ## Hvad der var galt (28/9-2026)
 *
 * `as_blocks` delte verden i `image` eller `file`, så en genereret video blev
 * et download-kort. Desk havde nul video-kode: ingen `<video>`, ingen type,
 * ingen komponent. En video kostede op til ti minutter at lave og kunne kun
 * hentes, ikke ses.
 *
 * Testene her måler tre ting, ikke én: at blokken OVERLEVER reload (det var
 * fejlen billederne havde indtil 15/9), at den hentes med token (ellers 401 på
 * ens egen fil), og at der faktisk står et afspiller-element på skærmen.
 */

const hentede: string[] = []
let hentFejler = false

vi.mock('../../lib/api', async (importOriginal) => {
  const faktisk = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...faktisk,
    fetchBlobWithAuth: async (_c: unknown, url: string) => {
      hentede.push(url)
      if (hentFejler) throw new Error('401')
      return new Blob(['video'], { type: 'video/mp4' })
    },
  }
})

vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'https://api.test/', authToken: 't' } }),
}))

beforeEach(() => {
  hentede.length = 0
  hentFejler = false
  URL.createObjectURL = vi.fn(() => 'blob:video-1')
  URL.revokeObjectURL = vi.fn()
})

describe('VideoBlock', () => {
  it('tegner en afspiller, ikke et download-kort', async () => {
    const { container } = render(
      <VideoBlock block={{ type: 'video', attachment_id: 'aid-1', filename: 'k.mp4' }} />)
    await waitFor(() => expect(container.querySelector('video')).not.toBeNull())
    const v = container.querySelector('video')!
    expect(v).toHaveAttribute('controls')
    expect(v.getAttribute('src')).toBe('blob:video-1')
  })

  it('henter MED token — et rent <video src> ville give 401 paa ens egen fil', async () => {
    render(<VideoBlock block={{ type: 'video', attachment_id: 'aid-1', filename: 'k.mp4' }} />)
    // ANTALLET er ikke det interessante — en effekt kan koere to gange under
    // test. ADRESSEN er: henter den fra en rute uden token-krav, eller fra den
    // rigtige, er forskellen 401 paa ens egen fil.
    await waitFor(() => expect(hentede.length).toBeGreaterThan(0))
    expect(new Set(hentede)).toEqual(new Set(['/attachments/media/aid-1']))
  })

  it('en LIVE video gaar direkte i elementet uden at hente noget', async () => {
    const { container } = render(
      <VideoBlock block={{ type: 'video', src: 'data:video/mp4;base64,AAA', filename: 'k.mp4' }} />)
    await waitFor(() => expect(container.querySelector('video')).not.toBeNull())
    expect(hentede).toHaveLength(0)
    expect(container.querySelector('video')!.getAttribute('src')).toBe('data:video/mp4;base64,AAA')
  })

  it('siger det aerligt naar den ikke kunne hentes', async () => {
    hentFejler = true
    const { container } = render(
      <VideoBlock block={{ type: 'video', attachment_id: 'aid-1', filename: 'k.mp4' }} />)
    await waitFor(() => expect(screen.getByText(/kunne ikke hentes/)).toBeInTheDocument())
    expect(container.querySelector('video')).toBeNull()
  })

  it('frigiver object-URL\'en naar den forsvinder — en video fylder meget', async () => {
    const { unmount, container } = render(
      <VideoBlock block={{ type: 'video', attachment_id: 'aid-1', filename: 'k.mp4' }} />)
    await waitFor(() => expect(container.querySelector('video')).not.toBeNull())
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:video-1')
  })
})

describe('adressen', () => {
  it('video henter fra /media/, ikke fra en adresse der hedder image', () => {
    expect(filAdresse({ type: 'video', attachment_id: 'a b' }))
      .toBe('/attachments/media/a%20b')
  })
  it('en UDGIVET video bruger sin egen url', () => {
    expect(filAdresse({ type: 'video', url: '/files/k.mp4', attachment_id: 'x' }))
      .toBe('/files/k.mp4')
  })
  it('billeder og filer er uroerte', () => {
    expect(filAdresse({ type: 'image', attachment_id: 'a' })).toBe('/attachments/image/a')
    expect(filAdresse({ type: 'file', attachment_id: 'a' })).toBe('/attachments/a')
  })
})

describe('overlever reload', () => {
  it('foldToolResults dropper ikke video-blokken', () => {
    const gemt = [{
      type: 'video', attachment_id: 'aid-9', filename: 'k.mp4',
      mime_type: 'video/mp4', kilde: 'generated', tool_use_id: 'call_1',
    }] as unknown as ContentBlock[]
    const ud = foldToolResults(gemt)
    expect(ud).toHaveLength(1)
    expect(ud[0]).toMatchObject({
      type: 'video', attachment_id: 'aid-9', filename: 'k.mp4', kilde: 'generated',
    })
  })

  it('baerer SAMME felter videre som en billed-blok', () => {
    const felter = (type: string) => {
      const ud = foldToolResults([{
        type, attachment_id: 'a', url: '/u', filename: 'f', mime_type: 'm',
        kilde: 'generated', tool_use_id: 't', src: 's', alt: 'a',
      }] as unknown as ContentBlock[])
      expect(ud).toHaveLength(1)
      return Object.keys(ud[0] as object).sort()
    }
    // video har size_bytes med (en video er stor nok til at det betyder noget)
    expect(felter('image').every((f) => felter('video').includes(f))).toBe(true)
  })
})
