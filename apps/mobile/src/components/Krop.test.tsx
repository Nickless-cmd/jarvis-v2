import { fireEvent, render } from '@testing-library/react-native'
import { TerminalKrop, FilKrop, Krop, MAX_LINJER } from './Krop'

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

  it('tegner INTET for fald — kaldsstedet bærer den rå form', async () => {
    const s = await render(<Krop familie="fald" result="noget" />)
    expect(s.queryByTestId('krop-terminal')).toBeNull()
    expect(s.queryByTestId('krop-fil')).toBeNull()
  })
})
