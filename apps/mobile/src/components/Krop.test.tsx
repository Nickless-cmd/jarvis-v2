import { act, fireEvent, render } from '@testing-library/react-native'
import {
  TerminalKrop, FilKrop, ListeKrop, Krop, MAX_LINJER, MAX_PUNKTER,
  MindeKrop, WebKrop, SpoergsmaalKrop, OpgaveKrop, SkrivKrop, FejlKrop,
  BilledeKrop, UnderagentKrop, Raadata,
} from './Krop'

// Billede og underagent henter gennem `config` fra AuthContext. Vi giver dem
// én, og mock'er de to hentninger — ellers slog de ud i netvaerk i en test.
jest.mock('../state/AuthContext', () => ({
  useAuthOptional: () => ({ config: { apiBaseUrl: 'http://x', authToken: 't' } }),
}))
jest.mock('./AuthImage', () => ({ hentTilCache: jest.fn(async () => '/tmp/x.png') }))
jest.mock('../lib/apiClient', () => ({
  hentAgentKald: jest.fn(async () => [{ tool_name: 'read_file', arguments_json: '{"path":"a"}' }]),
}))

/**
 * `render` er ASYNKRON i dette bibliotek (samme mønster som
 * `InlineToolGroup.test.tsx`), så hver test venter.
 */

/** Alle farver der faktisk sættes i render-træet — oppefra og ned. */
const farver = (node: unknown, ud: string[] = []): string[] => {
  if (Array.isArray(node)) { node.forEach((n) => farver(n, ud)); return ud }
  if (!node || typeof node !== 'object') return ud
  const n = node as { props?: Record<string, unknown>; children?: unknown }
  const st = n.props?.style
  const tag = (x: unknown) => {
    if (x && typeof x === 'object' && 'color' in (x as object)) {
      const c = (x as { color: unknown }).color
      if (typeof c === 'string') ud.push(c)
    }
  }
  if (Array.isArray(st)) st.forEach(tag)
  else tag(st)
  if (n.children) farver(n.children, ud)
  return ud
}

describe('TerminalKrop', () => {
  it('viser stdout som den er', async () => {
    const s = await render(<TerminalKrop ud={'fil1\nfil2'} exit={0} />)
    expect(s.getByTestId('krop-terminal')).toBeTruthy()
    expect(s.getByText(/fil1/)).toBeTruthy()
  })

  it('oversaetter ANSI-farvekoder i stedet for at vise dem som skrald', async () => {
    // `ls --color` skriver SGR ind i stdout. Farven ER information — den skal
    // blive en farve, ikke forsvinde og ikke staa som «[32m» i teksten.
    const s = await render(<TerminalKrop ud={'\x1b[31mrødt\x1b[0m og normalt'} exit={0} />)
    expect(farver(s.toJSON())).toContain('#e06c75')
    expect(s.queryByText(/\[31m/)).toBeNull()
  })

  it('viser exit-pillen KUN naar koden ikke er nul', async () => {
    // Husets regel (`raekkeKroppe.tsx`): «exit 0 tegner INGEN pille».
    const nul = await render(<TerminalKrop ud="ok" exit={0} />)
    expect(nul.queryByTestId('krop-exit')).toBeNull()

    const fejl = await render(<TerminalKrop ud="bum" exit={2} />)
    expect(fejl.getByTestId('krop-exit')).toBeTruthy()
    expect(fejl.getByText('exit 2')).toBeTruthy()
  })

  it('siger «Kører…» naar kaldet er i gang uden output endnu', async () => {
    const s = await render(<TerminalKrop ud="" exit={0} running />)
    expect(s.getByText('Kører…')).toBeTruthy()
  })

  it('tegner INTET naar der hverken er output eller et loebende kald', async () => {
    const s = await render(<TerminalKrop ud="" exit={0} />)
    expect(s.queryByTestId('krop-terminal')).toBeNull()
  })

  it('fjerner ikke-SGR sekvenser der ellers staar som skrald', async () => {
    // `\x1b[2K` (slet linje) er en markoersekvens vi ikke har. Foer stod den
    // som «[2K» midt i teksten.
    const s = await render(<TerminalKrop ud={'\x1b[2Krent'} exit={0} />)
    expect(s.getByText('rent')).toBeTruthy()
  })
})

describe('FilKrop', () => {
  it('viser linjenumre og indhold', async () => {
    // Indholdet maa ikke selv indeholde et rent tal: saa ville «1» baade vaere
    // linjenummer og kode, og testen maalte to ting paa én gang.
    const s = await render(<FilKrop tekst={'const a = x\nexport b'} />)
    expect(s.getByTestId('krop-fil')).toBeTruthy()
    expect(s.getByText('1')).toBeTruthy()
    expect(s.getByText('2')).toBeTruthy()
  })

  it('klipper en lang fil med hale — og siger hvor meget der er udeladt', async () => {
    const lang = Array.from({ length: 40 }, (_, i) => `linje ${i + 1}`).join('\n')
    const s = await render(<FilKrop tekst={lang} />)
    // Hoved + hale vises, midten goer ikke.
    expect(s.getByText('linje 1')).toBeTruthy()
    expect(s.getByText('linje 40')).toBeTruthy()
    expect(s.queryByText('linje 25')).toBeNull()
    // 40 - 18 - 6 = 16 udeladt i midten.
    expect(s.getByText('16 linjer udeladt i midten')).toBeTruthy()
  })

  it('«Vis alle» folder den klippede midte ud — lokalt, uden at hente noget', async () => {
    const lang = Array.from({ length: 40 }, (_, i) => `linje ${i + 1}`).join('\n')
    const s = await render(<FilKrop tekst={lang} />)
    await fireEvent.press(s.getByTestId('krop-vis-alle'))
    expect(s.getByText('linje 25')).toBeTruthy()
  })

  it('klipper IKKE en fil der er kortere end snittet', async () => {
    const kort = Array.from({ length: MAX_LINJER }, (_, i) => `l${i + 1}`).join('\n')
    const s = await render(<FilKrop tekst={kort} />)
    expect(s.queryByTestId('krop-vis-alle')).toBeNull()
  })

  it('tegner INTET for en tom fil', async () => {
    const s = await render(<FilKrop tekst="" />)
    expect(s.queryByTestId('krop-fil')).toBeNull()
  })
})

describe('ListeKrop', () => {
  it('tegner hvert punkt — med praefiks naar der er en sti', async () => {
    const s = await render(<ListeKrop poster={[
      { p: 'a.ts:42', v: 'const x = 1' },
      { v: 'b.ts' },
    ]} />)
    expect(s.getByTestId('krop-liste')).toBeTruthy()
    expect(s.getByText('a.ts:42')).toBeTruthy()
    expect(s.getByText('const x = 1')).toBeTruthy()
    expect(s.getByText('b.ts')).toBeTruthy()
  })

  it('klipper en lang liste — og siger hvor mange der er', async () => {
    const poster = Array.from({ length: MAX_PUNKTER + 3 }, (_, i) => ({ v: `punkt ${i}` }))
    const s = await render(<ListeKrop poster={poster} />)
    expect(s.getByTestId('krop-vis-alle-punkter')).toBeTruthy()
    expect(s.queryByText(`punkt ${MAX_PUNKTER + 2}`)).toBeNull()
  })

  it('«Vis alle» folder resten ud — uden et kald', async () => {
    const poster = Array.from({ length: MAX_PUNKTER + 3 }, (_, i) => ({ v: `punkt ${i}` }))
    const s = await render(<ListeKrop poster={poster} />)
    await fireEvent.press(s.getByTestId('krop-vis-alle-punkter'))
    expect(s.getByText(`punkt ${MAX_PUNKTER + 2}`)).toBeTruthy()
    expect(s.queryByTestId('krop-vis-alle-punkter')).toBeNull()
  })

  it('en kort liste har ingen knap', async () => {
    const s = await render(<ListeKrop poster={[{ v: 'a' }]} />)
    expect(s.queryByTestId('krop-vis-alle-punkter')).toBeNull()
  })

  it('tegner INTET naar der ingen punkter er', async () => {
    const s = await render(<ListeKrop poster={[]} />)
    expect(s.queryByTestId('krop-liste')).toBeNull()
  })
})

describe('Krop — vælgeren', () => {
  it('giver terminal-kroppen og udtrækker stdout af JSON-blobben', async () => {
    // Kaldsstedet giver det RÅ resultat; vælgeren udtrækker selv. Uden det
    // ville `{"stdout": …}` blive vist som om det var output.
    const s = await render(<Krop familie="terminal" result={'{"stdout": "hej", "exit_code": 0}'} />)
    expect(s.getByTestId('krop-terminal')).toBeTruthy()
    expect(s.getByText('hej')).toBeTruthy()
    expect(s.queryByTestId('krop-fil')).toBeNull()
  })

  it('giver fil-kroppen og udtrækker indholdet af content-feltet', async () => {
    const s = await render(<Krop familie="fil" result={'{"content": "a\\nb"}'} />)
    expect(s.getByTestId('krop-fil')).toBeTruthy()
    expect(s.queryByTestId('krop-terminal')).toBeNull()
  })

  it('giver liste-kroppen for en hitliste', async () => {
    const s = await render(<Krop familie="liste" result={'{"files":["a.ts","b.ts"]}'} />)
    expect(s.getByTestId('krop-liste')).toBeTruthy()
    expect(s.getByText('a.ts')).toBeTruthy()
    expect(s.queryByTestId('krop-terminal')).toBeNull()
  })

  it('tegner INTET naar liste-resultatet ikke baerer en liste', async () => {
    // Kaldsstedet falder så til rå tekst — en tom ramme ville være værre end
    // den tekst vi havde i forvejen.
    const s = await render(<Krop familie="liste" result="ren tekst" />)
    expect(s.queryByTestId('krop-liste')).toBeNull()
  })

  it('tegner INTET for fald — kaldsstedet bærer den rå form', async () => {
    const s = await render(<Krop familie="fald" result="noget" />)
    expect(s.queryByTestId('krop-terminal')).toBeNull()
    expect(s.queryByTestId('krop-fil')).toBeNull()
  })
})

describe('MindeKrop', () => {
  it('viser titel, meta og tekst', async () => {
    const s = await render(<MindeKrop titel="Fundet" meta="fakta · self" tekst={'linje 1\nlinje 2'} />)
    expect(s.getByTestId('krop-minde')).toBeTruthy()
    expect(s.getByText('Fundet')).toBeTruthy()
    expect(s.getByText('fakta · self')).toBeTruthy()
    expect(s.getByText(/linje 1/)).toBeTruthy()
  })
})

describe('WebKrop', () => {
  it('tegner domaenet over titlen pr. traef', async () => {
    const s = await render(<WebKrop traef={[{ dom: 'a.dk', titel: 'A' }]} />)
    expect(s.getByTestId('krop-web')).toBeTruthy()
    expect(s.getByText('a.dk')).toBeTruthy()
    expect(s.getByText('A')).toBeTruthy()
  })
})

describe('SpoergsmaalKrop', () => {
  it('viser spoergsmaalet og svaret', async () => {
    const s = await render(<SpoergsmaalKrop q="Hvilken?" svar="Den anden" />)
    expect(s.getByTestId('krop-spoergsmaal')).toBeTruthy()
    expect(s.getByText('Hvilken?')).toBeTruthy()
    expect(s.getByText('Den anden')).toBeTruthy()
  })
})

describe('OpgaveKrop', () => {
  it('taeller faerdige og tegner de tre glyfer', async () => {
    const s = await render(<OpgaveKrop poster={[
      { tekst: 'a', status: 'completed' },
      { tekst: 'b', status: 'in_progress' },
      { tekst: 'c', status: 'pending' },
    ]} />)
    expect(s.getByText(/1 af 3/)).toBeTruthy()
    expect(s.getByText(/1 i gang/)).toBeTruthy()
    expect(s.getByText('☑')).toBeTruthy()
    expect(s.getByText('◐')).toBeTruthy()
    expect(s.getByText('☐')).toBeTruthy()
  })
})

describe('Raadata', () => {
  it('starter LUKKET og folder IN og OUT ud ved tryk', async () => {
    const s = await render(<Raadata ind='{"a":1}' ud="nej" />)
    expect(s.queryByText('IN')).toBeNull()
    await fireEvent.press(s.getByTestId('krop-raadata-knap'))
    expect(s.getByText('IN')).toBeTruthy()
    expect(s.getByText('OUT')).toBeTruthy()
  })
})

describe('SkrivKrop og FejlKrop', () => {
  it('skriv viser beviset og har raa data ét tryk væk', async () => {
    const s = await render(<SkrivKrop besked="1941 bytes skrevet" ind="{}" ud="ok" />)
    expect(s.getByTestId('krop-skriv')).toBeTruthy()
    expect(s.getByText('1941 bytes skrevet')).toBeTruthy()
    expect(s.getByTestId('krop-raadata')).toBeTruthy()
  })

  it('fejl viser beskeden frem for den tomme form', async () => {
    const s = await render(<FejlKrop besked="Stien maa ikke vises" ind="{}" ud="nej" />)
    expect(s.getByTestId('krop-fejl')).toBeTruthy()
    expect(s.getByText('Stien maa ikke vises')).toBeTruthy()
  })

  it('fejl uden besked siger det hoejt i stedet for at staa tom', async () => {
    const s = await render(<FejlKrop besked="" ind="{}" ud="" />)
    expect(s.getByText(/kunne ikke gennemføres/)).toBeTruthy()
  })
})

describe('BilledeKrop', () => {
  it('viser navn, maal og analysen — og henter gennem ruten', async () => {
    const s = await render(<BilledeKrop
      sti="/tmp/skaerm.png" navn="skaerm.png" meta="800 × 600"
      spoergsmaal="hvad staar der?" tekst="Et skaermbillede"
    />)
    expect(s.getByTestId('krop-billede')).toBeTruthy()
    expect(s.getByText('skaerm.png')).toBeTruthy()
    expect(s.getByText('800 × 600')).toBeTruthy()
    expect(s.getByText('Et skaermbillede')).toBeTruthy()
  })
})

describe('UnderagentKrop', () => {
  it('henter og viser agentens egne kald', async () => {
    const s = await render(<UnderagentKrop agentId="ag-1" resultat="Fandt 3 filer" />)
    expect(s.getByTestId('krop-underagent')).toBeTruthy()
    expect(s.getByText('Fandt 3 filer')).toBeTruthy()
    // Kaldet er asynkront — vent paa at det lander.
    await act(async () => { await Promise.resolve() })
    expect(s.getByTestId('krop-underagent-liste')).toBeTruthy()
    expect(s.getByText('read_file')).toBeTruthy()
  })
})

describe('Krop — de nye former', () => {
  it('minde bygges af ARGUMENTERNE', async () => {
    const s = await render(<Krop familie="minde" result={'{"id":"x"}'} input={'{"title":"T","content":"C"}'} />)
    expect(s.getByTestId('krop-minde')).toBeTruthy()
    expect(s.getByText('T')).toBeTruthy()
  })

  it('web tegner traef-listen', async () => {
    const s = await render(<Krop familie="web" result={'{"results":[{"url":"a.dk","title":"A"}]}'} />)
    expect(s.getByTestId('krop-web')).toBeTruthy()
  })

  it('opgave tegner linjerne', async () => {
    const s = await render(<Krop familie="opgave" result={'{"todos":[{"content":"a","status":"pending"}]}'} />)
    expect(s.getByTestId('krop-opgave')).toBeTruthy()
  })

  it('fejl tegner beskeden fra resultatet', async () => {
    const s = await render(<Krop familie="fejl" result={'{"status":"approval_needed","error":"naegtet"}'} />)
    expect(s.getByTestId('krop-fejl')).toBeTruthy()
    expect(s.getByText('naegtet')).toBeTruthy()
  })
})
