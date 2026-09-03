import { File, UploadType } from 'expo-file-system'
import { transcribeAudio } from './voiceApi'
import type { ApiConfig } from './types'

const config = { apiBaseUrl: 'https://api.example.test', authToken: 'tok' } as ApiConfig

function mockUpload(res: { status: number; body: string }) {
  const upload = jest.fn(async () => ({ ...res, headers: {} }))
  ;(File as unknown as jest.Mock).mockImplementation((uri: string) => ({ uri, upload }))
  return upload
}

beforeEach(() => jest.clearAllMocks())

describe('transcribeAudio', () => {
  // Kernen i fejlen: fetch + FormData({uri}) kastede «Unsupported FormDataPart
  // implementation» FØR noget forlod telefonen. Uploadet skal gå nativt.
  it('sender filen nativt og rører ikke fetch', async () => {
    const upload = mockUpload({ status: 200, body: '{"status":"ok","text":"hej"}' })
    const spy = jest.spyOn(global, 'fetch' as never)

    const out = await transcribeAudio(config, 'file:///cache/utterance.m4a')

    expect(File).toHaveBeenCalledWith('file:///cache/utterance.m4a')
    expect(spy).not.toHaveBeenCalled()
    expect(out).toEqual({ status: 'ok', text: 'hej' })
    spy.mockRestore()
  })

  it('bruger multipart med feltnavnet serveren læser', async () => {
    const upload = mockUpload({ status: 200, body: '{"status":"ok","text":"x"}' })
    await transcribeAudio(config, 'file:///cache/a.m4a')

    const [url, opts] = upload.mock.calls[0] as unknown as [string, Record<string, unknown>]
    expect(url).toBe('https://api.example.test/transcribe')
    expect(opts.uploadType).toBe(UploadType.MULTIPART)
    expect(opts.fieldName).toBe('file')
    expect(opts.mimeType).toBe('audio/m4a')
    // Serveren defaulter til dansk, men den skal stå der eksplicit: whisper
    // gætter korte ytringer forkert og skifter til engelsk.
    expect(opts.parameters).toEqual({ language: 'da' })
    expect(opts.headers).toEqual({ Authorization: 'Bearer tok' })
  })

  it('kaster ved HTTP-fejl i stedet for at aflevere tom tekst', async () => {
    mockUpload({ status: 500, body: 'boom' })
    await expect(transcribeAudio(config, 'file:///cache/a.m4a')).rejects.toThrow('transcribe HTTP 500')
  })

  // Et 200 med en HTML-fejlside ville ellers blive JSON.parse'et og kaste en
  // rå SyntaxError op i overlayet, hvor brugeren ser den.
  it('kaster forståeligt når svaret ikke er JSON', async () => {
    mockUpload({ status: 200, body: '<html>nope</html>' })
    await expect(transcribeAudio(config, 'file:///cache/a.m4a')).rejects.toThrow('uventet svar')
  })
})
