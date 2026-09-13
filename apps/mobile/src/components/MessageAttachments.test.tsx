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


// ── udgivne filer (12/9-2026) ────────────────────────────────────────────
//
// publish_file lagde filen i files/ og gav en URL, men turen bar den aldrig:
// nul assistent-beskeder havde en image/file-blok. Nu baerer den dem, og
// kortet skal kunne AABNES — foer viste det navn og type og kunne ikke trykkes.
// /files kraever token, saa appen henter filen selv og viser telefonens kopi.

jest.mock('../lib/aabnFil', () => ({
  ...jest.requireActual('../lib/aabnFil'),
  aabnUdgivetFil: jest.fn(async () => undefined),
}))

it('en udgivet fil uden attachment_id faar stadig et kort', async () => {
  const screen = await render(
    <MessageAttachments
      items={[{ type: 'file', filename: 'rapport.html',
                url: 'https://api.srvlab.dk/files/rapport.html',
                mime_type: 'text/html' } as never]}
    />
  )
  expect(screen.getByText('rapport.html')).toBeTruthy()
})

it('fil-kortet kan trykkes og aabner den UDGIVNE adresse', async () => {
  const { aabnUdgivetFil } = require('../lib/aabnFil')
  const screen = await render(
    <MessageAttachments
      items={[{ type: 'file', filename: 'rapport.html',
                url: 'https://api.srvlab.dk/files/rapport.html',
                mime_type: 'text/html' } as never]}
    />
  )
  await act(async () => {
    fireEvent.press(screen.getByTestId('attachment-file-rapport.html'))
  })
  expect(aabnUdgivetFil).toHaveBeenCalled()
  const [, url, navn, mime] = (aabnUdgivetFil as jest.Mock).mock.calls[0]
  expect(url).toBe('https://api.srvlab.dk/files/rapport.html')
  expect(navn).toBe('rapport.html')
  expect(mime).toBe('text/html')
})

it('MessageList laegger assistentens filer fra sig FOER grenene', () => {
  // Koblingen. Baade ordre-grenen og taenke-grenen `continue`r, saa en
  // haandtering placeret efter dem ville aldrig naas paa en almindelig tur —
  // og uden denne proeve var mutationen usynlig: at fjerne linjen lod alle
  // 156 komponent-tests bestaa.
  const kilde = require('fs').readFileSync(
    require('path').join(__dirname, 'MessageList.tsx'), 'utf8') as string
  const iAssistent = kilde.split("if (m.role === 'assistant') {")[1] ?? ''
  const foerOrdre = iAssistent.split('if (hasOrdering(blocks))')[0] ?? ''
  expect(foerOrdre).toContain('attachmentBlocks(blocks)')
})

// ── hvilken side af traaden? (13/9-2026) ─────────────────────────────────
//
// Komponenten var stilet til HOEJRE side alene, og blev brugt til BAADE
// brugerens uploads og assistentens udgivne billeder. Et billede Jarvis havde
// lavet landede derfor i brugerens boble og saa ud som om brugeren havde sendt
// det. Siden er nu en prop — og koblingen skal kunne ses.

it('assistentens billeder tegnes i VENSTRE side — brugerens i hoejre', () => {
  const kilde = require('fs').readFileSync(
    require('path').join(__dirname, 'MessageList.tsx'), 'utf8') as string

  // Proeven kraever den KONKRETE kodelinje, ikke bare ordene. Foerste udgave
  // spurgte om `side: 'left'` — og bestod mutationen, fordi kommentaren
  // ovenfor selv skriver `side: 'left'`. En test der matcher beskrivelsen af
  // rettelsen i stedet for rettelsen.
  const iAssistent = kilde.split("if (m.role === 'assistant') {")[1] ?? ''
  expect(iAssistent.split('if (hasOrdering(blocks))')[0] ?? '')
    .toContain("items: afiler, side: 'left'")

  const iBruger = kilde.split("if (m.role === 'user') {")[1] ?? ''
  expect(iBruger.split("if (m.role === 'tool')")[0] ?? '')
    .toContain("items: ublocks, side: 'right'")
})

it('siden foelger med hele vejen ud i komponenten', () => {
  const kilde = require('fs').readFileSync(
    require('path').join(__dirname, 'MessageList.tsx'), 'utf8') as string
  expect(kilde).toContain('<MessageAttachments items={item.items} side={item.side} />')
})

const flad = (s: unknown): Record<string, unknown> =>
  Array.isArray(s)
    ? Object.assign({}, ...s.map(flad))
    : ((s as Record<string, unknown>) ?? {})

it('en assistent-vedhaeftning staar til venstre', async () => {
  const screen = await render(
    <MessageAttachments
      side="left"
      items={[{ type: 'image', attachment_id: 'imgL', filename: 'a.png' }]}
    />
  )
  expect(flad(screen.getByTestId('attachment-wrap').props.style).alignSelf).toBe('flex-start')
})

it('en bruger-vedhaeftning staar til hoejre — ogsaa uden at sige det', async () => {
  const screen = await render(
    <MessageAttachments items={[{ type: 'image', attachment_id: 'imgR', filename: 'b.png' }]} />
  )
  expect(flad(screen.getByTestId('attachment-wrap').props.style).alignSelf).toBe('flex-end')
})
