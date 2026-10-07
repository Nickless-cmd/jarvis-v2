import { render } from '@testing-library/react-native'
import { WidgetFlade, MAX_WIDGET_BYTES, WidgetPrompt } from './WidgetFlade'

/**
 * Mobilen har ingen `sandbox`-attribut, saa graensen er bygget af FLAG. Disse
 * tests fejler hvis et af dem forsvinder — enten ved en rettelse her eller
 * ved at nogen fjerner det eksplicitte flag og lader bibliotekets standard
 * gaelde.
 */

// WebView-mocken bor i jest.setup.js — den er et miljoe-forhold, ikke
// denne tests egen sag.

async function props(html = '<p>hej</p>') {
  // Husets moenster: `render` ventes paa, og `screen` baerer forespoergslerne.
  const screen = await render(<WidgetFlade html={html} titel="proeve" />)
  return screen.getByTestId('widget-webview').props as Record<string, unknown>
}

describe('WidgetFlade', () => {
  it('dokumentet faar INGEN baseUrl — origin skal vaere about:blank', async () => {
    const p = await props()
    expect(p.source).toEqual({ html: '<p>hej</p>' })
    expect((p.source as Record<string, unknown>).baseUrl).toBeUndefined()
  })

  it('ingen origin er tilladt, og navigation efter foerste indlaesning afvises', async () => {
    const p = await props()
    expect(p.originWhitelist).toEqual([])
    const guard = p.onShouldStartLoadWithRequest as () => boolean
    expect(guard()).toBe(true)    // selve dokumentet
    expect(guard()).toBe(false)   // alt derefter er navigation
    expect(guard()).toBe(false)
  })

  it('fil-adgang, storage, cookies og flere vinduer er LUKKET eksplicit', async () => {
    const p = await props()
    for (const flag of [
      'domStorageEnabled', 'allowFileAccess', 'allowFileAccessFromFileURLs',
      'allowUniversalAccessFromFileURLs', 'allowsInlineMediaPlayback',
      'setSupportMultipleWindows', 'cacheEnabled', 'thirdPartyCookiesEnabled',
    ]) {
      expect(p[flag]).toBe(false)
    }
    expect(p.incognito).toBe(true)
  })

  it('javascript er TAENDT — en widget uden det er et billede', async () => {
    expect((await props()).javaScriptEnabled).toBe(true)
  })

  it('hoejde-scriptet injiceres', async () => {
    expect(String((await props()).injectedJavaScript)).toContain('jarvis-widget-hoejde')
  })

  it('en uparsebar besked vaelter ikke komponenten', async () => {
    const p = await props()
    const paa = p.onMessage as (e: unknown) => void
    expect(() => paa({ nativeEvent: { data: 'ikke json' } })).not.toThrow()
    expect(() => paa({ nativeEvent: { data: '{}' } })).not.toThrow()
  })

  it('et tomt eller for stort dokument siger det frem for at staa tomt', async () => {
    const tom = await render(<WidgetFlade html="" />)
    expect(tom.getByText(/tomt dokument/)).toBeTruthy()
    const stor = await render(<WidgetFlade html={'x'.repeat(MAX_WIDGET_BYTES + 1)} />)
    expect(stor.getByText(/for stor/)).toBeTruthy()
  })
})

describe('WidgetFlade sendPrompt-kanalen', () => {
  async function medFlade(onPrompt?: (t: string) => void) {
    const screen = await render(
      <WidgetPrompt.Provider value={onPrompt ?? null}>
        <WidgetFlade html="<p>hej</p>" titel="Tabel" />
      </WidgetPrompt.Provider>,
    )
    const p = screen.getByTestId('widget-webview').props as Record<string, unknown>
    const paa = p.onMessage as (e: unknown) => void
    return (data: unknown) => paa({ nativeEvent: { data: JSON.stringify(data) } })
  }

  it('en MAERKET besked naar frem med maerket foran', async () => {
    const set: string[] = []
    const send = await medFlade((t) => set.push(t))
    send({ type: 'jarvis-widget-prompt', tekst: 'sorter efter miss', maerke: '[fra widget «Tabel»]' })
    expect(set).toEqual(['[fra widget «Tabel»] sorter efter miss'])
  })

  it('en UMAERKET besked sendes IKKE', async () => {
    const set: string[] = []
    const send = await medFlade((t) => set.push(t))
    send({ type: 'jarvis-widget-prompt', tekst: 'goer noget' })
    send({ type: 'jarvis-widget-prompt', tekst: 'goer noget', maerke: 'Bjørn:' })
    expect(set).toEqual([])
  })

  it('takten begraenses — en loekke kan ikke spamme samtalen', async () => {
    const set: string[] = []
    const send = await medFlade((t) => set.push(t))
    for (let i = 0; i < 20; i++) {
      send({ type: 'jarvis-widget-prompt', tekst: `nr ${i}`, maerke: '[fra widget]' })
    }
    expect(set).toHaveLength(1)
  })

  it('tom og overlang tekst afvises', async () => {
    const set: string[] = []
    const send = await medFlade((t) => set.push(t))
    send({ type: 'jarvis-widget-prompt', tekst: '  ', maerke: '[fra widget]' })
    send({ type: 'jarvis-widget-prompt', tekst: 'x'.repeat(2001), maerke: '[fra widget]' })
    send({ type: 'jarvis-widget-prompt', tekst: 7, maerke: '[fra widget]' })
    expect(set).toEqual([])
  })

  it('uden provider sker der ingenting — ingen kasten', async () => {
    const send = await medFlade(undefined)
    expect(() => send({ type: 'jarvis-widget-prompt', tekst: 'x', maerke: '[fra widget]' })).not.toThrow()
  })
})

// ── BREDDEN SKAL VAERE ET TAL (Bjørn 6/10-2026) ────────────────────────────
//
// Rammen havde `width: '100%'` inde i en wrapper med `alignSelf: 'flex-start'`
// og `alignItems: 'flex-start'`. En procent resolver mod foraelderens definite
// bredde; har foraelderen ingen — fordi den selv maales af sine boern — bliver
// den nul. Med `overflow: 'hidden'` saa Bjørn «ingenting».
describe('widget-rammens bredde', () => {
  const flad = (node: unknown): Record<string, unknown> => {
    const s = (node as { props?: { style?: unknown } })?.props?.style
    const dele = Array.isArray(s) ? s : [s]
    return Object.assign({}, ...dele.filter((d) => d && typeof d === 'object'))
  }

  it('er et TAL, ikke en procent', async () => {
    const screen = await render(<WidgetFlade html="<!doctype html><p>hej</p>" />)
    const web = screen.getByTestId('widget-webview')
    const ramme = (web as unknown as { parent: unknown }).parent
    const style = flad(ramme)
    expect(typeof style.width).toBe('number')
    expect(style.width as number).toBeGreaterThan(0)
  })

  it('har stadig en hoejde, saa den ikke kollapser den anden vej', async () => {
    const screen = await render(<WidgetFlade html="<!doctype html><p>hej</p>" />)
    const ramme = (screen.getByTestId('widget-webview') as unknown as { parent: unknown }).parent
    expect(typeof flad(ramme).height).toBe('number')
  })
})
