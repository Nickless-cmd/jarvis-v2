import { act, fireEvent, render } from '@testing-library/react-native'
import { MessageAttachments, formatSize } from './MessageAttachments'

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config: { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' } })
}))

describe('formatSize', () => {
  it('viser bytes under 1 kB', () => {
    expect(formatSize(512)).toBe('512 B')
  })

  it('bruger dansk komma og skjuler tom decimal', () => {
    expect(formatSize(1536)).toBe('1,5 kB')
    expect(formatSize(2048)).toBe('2 kB')
  })

  it('gaar op i MB og GB', () => {
    expect(formatSize(5 * 1024 * 1024)).toBe('5 MB')
    expect(formatSize(3 * 1024 * 1024 * 1024)).toBe('3 GB')
  })
})

it('åbner billedvedhæftninger i fullscreen preview ved tryk', async () => {
  const screen = await render(
    <MessageAttachments
      items={[{ type: 'image', attachment_id: 'img1', filename: 'køkken.png' }]}
    />
  )

  await act(async () => {
    fireEvent.press(screen.getByTestId('attachment-open-img1'))
  })

  expect(screen.getByText('køkken.png')).toBeTruthy()
  expect(screen.getByTestId('attachment-fullscreen-image')).toBeTruthy()
})

/** children kan være en streng, et array eller nested — fladgør før vi ser efter. */
const tekstAf = (node: { props: { children?: unknown } }): string => {
  const ud: string[] = []
  const gaa = (v: unknown) => {
    if (typeof v === 'string' || typeof v === 'number') ud.push(String(v))
    else if (Array.isArray(v)) v.forEach(gaa)
    else if (v && typeof v === 'object' && 'props' in (v as Record<string, unknown>)) {
      gaa(((v as { props: { children?: unknown } }).props || {}).children)
    }
  }
  gaa(node.props.children)
  return ud.join('')
}

it('siger HVAD filen er — en PDF og en zip så ens ud før', async () => {
  const screen = await render(
    <MessageAttachments items={[{ type: 'file', attachment_id: 'f1', filename: 'rapport.pdf', size_bytes: 1000 } as never]} />
  )
  expect(tekstAf(screen.getByTestId('attachment-kind-f1'))).toContain('PDF')
})

it('siger til når filen åbnes uden for appen', async () => {
  const screen = await render(
    <MessageAttachments items={[{ type: 'file', attachment_id: 'f2', filename: 'a.zip', size_bytes: 10 } as never]} />
  )
  expect(tekstAf(screen.getByTestId('attachment-kind-f2'))).toContain('åbnes i telefonen')
})

it('en lille kodefil vises ikke som «åbnes i telefonen»', async () => {
  const screen = await render(
    <MessageAttachments items={[{ type: 'file', attachment_id: 'f3', filename: 'x.py', size_bytes: 200 } as never]} />
  )
  const t = tekstAf(screen.getByTestId('attachment-kind-f3'))
  expect(t).toContain('Python')
  expect(t).not.toContain('åbnes i telefonen')
})
