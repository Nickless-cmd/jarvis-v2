import { render, waitFor } from '@testing-library/react-native'
import { AuthVideo } from './AuthVideo'
import { MessageAttachments } from './MessageAttachments'
import { blokUrl } from '../lib/aabnFil'
import { erVideoVaerktoej, billedArbejdeFor } from '../lib/billedArbejde'
import type { ApiConfig } from '../lib/types'
import type { PersistedBlock } from '../lib/persistedBlocks'

/**
 * Video i mobil-tråden.
 *
 * ## Hvad der var galt (28/9-2026)
 *
 * `MessageAttachments` kendte `image` og «alt andet». Alt andet blev et
 * fil-kort. `filePreview` vidste godt at `mp4` er «Video» — men som en FIL man
 * kunne åbne i et andet program, ikke som noget man kunne se i tråden. Der var
 * ingen afspiller installeret overhovedet.
 */

const config = { apiBaseUrl: 'https://api.test/', authToken: 't' } as unknown as ApiConfig

/** Hentningen styres pr. test. Uden den styring ser «henter» og «hentet» ens
 *  ud, og testen kan ikke skelne dem — samme greb som AuthImage.plads.test. */
const fsMock = jest.requireMock('expo-file-system/legacy') as {
  createDownloadResumable: jest.Mock
  getInfoAsync: jest.Mock
}
beforeEach(() => {
  fsMock.getInfoAsync.mockResolvedValue({ exists: false, size: 0 })
  fsMock.createDownloadResumable.mockReturnValue({
    downloadAsync: jest.fn(async () => ({ uri: 'file:///cache/vid-aid-1' })),
  })
})

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config: { apiBaseUrl: 'https://api.test/', authToken: 't' } }),
}))

describe('AuthVideo', () => {
  it('henter filen til telefonen og spiller den lokale kopi', async () => {
    const s = await render(<AuthVideo config={config} url="/attachments/media/aid-1" navn="aid-1" testID="v" />)
    await waitFor(() => expect(s.getByTestId('v')).toBeTruthy())
  })

  it('siger at den henter mens den henter — ikke et tomt felt', async () => {
    fsMock.createDownloadResumable.mockReturnValue({
      downloadAsync: () => new Promise(() => {}),   // haenger med vilje
    })
    const s = await render(<AuthVideo config={config} url="/attachments/media/aid-1" navn="aid-1" testID="v" />)
    expect(s.getByLabelText('Henter video')).toBeTruthy()
  })
})

describe('adressen', () => {
  it('video peger paa /media/, ikke paa den generiske rute', async () => {
    expect(blokUrl({ type: 'video', attachment_id: 'aid-1' }, 'https://api.test/'))
      .toBe('https://api.test/attachments/media/aid-1')
  })
  it('billede og fil er uroerte', async () => {
    expect(blokUrl({ type: 'image', attachment_id: 'a' }, 'https://api.test/'))
      .toBe('https://api.test/attachments/image/a')
    expect(blokUrl({ type: 'file', attachment_id: 'a' }, 'https://api.test/'))
      .toBe('https://api.test/attachments/a')
  })
  it('en UDGIVET video bruger sin egen url', async () => {
    expect(blokUrl({ type: 'video', url: '/files/k.mp4', attachment_id: 'x' }, 'https://api.test/'))
      .toBe('https://api.test/files/k.mp4')
  })
})

describe('i traaden', () => {
  it('en video-blok bliver en AFSPILLER, ikke et fil-kort', async () => {
    const blokke = [{
      type: 'video', attachment_id: 'aid-7', filename: 'k.mp4', mime_type: 'video/mp4',
    }] as unknown as PersistedBlock[]
    const s = await render(<MessageAttachments items={blokke} side="left" />)
    expect(s.getByTestId('attachment-video-aid-7')).toBeTruthy()
    expect(s.queryByTestId('attachment-file-aid-7')).toBeNull()
  })

  it('en almindelig fil er STADIG et fil-kort', async () => {
    const blokke = [{
      type: 'file', attachment_id: 'aid-8', filename: 'r.zip', mime_type: 'application/zip',
    }] as unknown as PersistedBlock[]
    const s = await render(<MessageAttachments items={blokke} side="left" />)
    expect(s.getByTestId('attachment-file-aid-8')).toBeTruthy()
  })
})

describe('arbejdet mens den laves', () => {
  it('video-vaerktoejerne kendes', async () => {
    expect(erVideoVaerktoej('pollinations_video')).toBe(true)
    expect(erVideoVaerktoej('pollinations_video_edit')).toBe(true)
    expect(erVideoVaerktoej('pollinations_image')).toBe(false)
  })

  it('et koerende video-kald giver video-arbejde — ikke billed-arbejde', async () => {
    expect(billedArbejdeFor({ name: 'pollinations_video', status: 'running' }))
      .toEqual({ slags: 'video' })
    expect(billedArbejdeFor({ name: 'pollinations_image', status: 'running' }))
      .toEqual({ slags: 'generering' })
  })

  it('et FAERDIGT kald animerer ikke', async () => {
    expect(billedArbejdeFor({ name: 'pollinations_video', status: 'done' })).toBeNull()
  })
})
