import { act, render } from '@testing-library/react-native'
import { WidgetFlade, dokumentets_egen, MAX_WIDGET_BYTES, WidgetPrompt } from './WidgetFlade'

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

  // DENNE TEST PINNEDE FEJLEN (6/10-2026). Foerste udgave kaldte `guard()` UDEN
  // adresse og kraevede «foerst true, saa false» — altsaa taelleren, ikke
  // adfaerden. Den bestod mens widget'en var usynlig paa telefonen, fordi
  // Android fyrer tjekket flere gange for EN indlaesning og taelleren derfor
  // blokerede selve dokumentet. En test der maaler sin egen opfindelse kan
  // ikke se virkeligheden fejle.
  it('slipper dokumentet igennem og afviser navigation — paa ADRESSEN', async () => {
    const p = await props()
    const guard = p.onShouldStartLoadWithRequest as (r: { url: string }) => boolean
    // Dokumentet, gentagne gange — Android spoerger mere end en gang.
    expect(guard({ url: 'about:blank' })).toBe(true)
    expect(guard({ url: 'about:blank' })).toBe(true)
    // Og enhver vej ud, ogsaa som det FOERSTE kald.
    expect(guard({ url: 'https://api.srvlab.dk/' })).toBe(false)
    expect(guard({ url: 'intent://scan/#Intent;scheme=zxing;end' })).toBe(false)
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

// ── GATEN SKAL SE PAA ADRESSEN (Bjørn 6/10-2026) ───────────────────────────
//
// Foerste udgave talte kald: «foerste = dokumentet, resten = navigation».
// Android fyrer tjekket flere gange for EN `loadDataWithBaseURL`, saa
// taelleren blokerede selve dokumentet. Bjoern saa en tom ramme.
describe('dokumentets_egen', () => {
  it('slipper dokumentet igennem — uanset hvor mange gange den spoerges', () => {
    for (let i = 0; i < 5; i++) {
      expect(dokumentets_egen('about:blank')).toBe(true)
    }
    expect(dokumentets_egen('data:text/html;base64,PGh0bWw+')).toBe(true)
    expect(dokumentets_egen('')).toBe(true)
    expect(dokumentets_egen(undefined)).toBe(true)
  })

  it('afviser enhver vej UD af sandkassen', () => {
    for (const u of [
      'https://api.srvlab.dk/attachments/media/abc',
      'http://10.0.0.39/',
      'file:///data/data/dk.srvlab.jarvis.mobile/',
      'intent://scan/#Intent;scheme=zxing;end',
      'javascript:alert(1)',
      'content://media/external/images/1',
    ]) {
      expect(dokumentets_egen(u)).toBe(false)
    }
  })

  it('store bogstaver maa ikke smutte udenom', () => {
    expect(dokumentets_egen('HTTPS://api.srvlab.dk/')).toBe(false)
    expect(dokumentets_egen('About:Blank')).toBe(true)
  })
})

// ── RAMMEN SKAL SIGE HVAD DER SKETE (Bjørn 6/10-2026) ──────────────────────
//
// To rettelser i traek ramte ved siden af, fordi en blank flade ikke kan
// skelne «indlaeste aldrig» fra «indlaeste og malede intet» fra «fejlede
// tavst». WebView'ens fejl-callbacks blev slet ikke lyttet paa.
describe('widget-rammens tilstand', () => {
  const props = async (html = '<p>hej</p>') => {
    const screen = await render(<WidgetFlade html={html} />)
    return screen.getByTestId('widget-webview').props as Record<string, never>
  }

  it('siger «indlaeses» indtil WebView melder klar', async () => {
    const screen = await render(<WidgetFlade html="<p>hej</p>" />)
    expect(screen.getByTestId('widget-tilstand')).toBeTruthy()
  })

  it('statuslinjen forsvinder naar dokumentet RAPPORTERER sin hoejde', async () => {
    // Kontrakten (7/10-2026): `onLoadEnd` maa ikke skjule noget — biblioteket
    // kalder `onError` FOER `onLoadEnd`, saa et ukritisk «klar» her gjorde
    // enhver fejl usynlig. Linjen forsvinder derfor FOERST naar dokumentet har
    // koert JS og maalt sig selv: en `jarvis-widget-hoejde`-besked. Testen
    // pinner begge trin — foer melder den «loadet, men tavs», efter er den vaek.
    const screen = await render(<WidgetFlade html="<p>hej</p>" />)
    const p = screen.getByTestId('widget-webview').props as Record<string, never>
    await act(async () => { (p.onLoadEnd as unknown as () => void)() })
    // Loadet, men dokumentet svarede ikke: linjen STAAR og siger hvad der mangler.
    expect(JSON.stringify(screen.getByTestId('widget-tilstand').props.children))
      .toContain('svarede ikke')
    // Foerst da dokumentet maalte sig selv, forsvinder den.
    await act(async () => {
      (p.onMessage as unknown as (e: unknown) => void)({
        nativeEvent: { data: JSON.stringify({ type: 'jarvis-widget-hoejde', hoejde: 200 }) },
      })
    })
    expect(screen.queryByTestId('widget-tilstand')).toBeNull()
  })

  it('NAVNGIVER en fejl i stedet for at staa tom', async () => {
    const screen = await render(<WidgetFlade html="<p>hej</p>" />)
    const p = screen.getByTestId('widget-webview').props as Record<string, never>
    await act(async () => {
      (p.onError as unknown as (e: unknown) => void)({ nativeEvent: { description: 'net::ERR_FOO' } })
    })
    expect(JSON.stringify(screen.getByTestId('widget-tilstand').props.children)).toContain('net::ERR_FOO')
  })

  it('bruger hardware-lag — en WebView i en FlatList tegner ellers blankt', async () => {
    expect((await props()).androidLayerType).toBe('hardware')
  })
})
