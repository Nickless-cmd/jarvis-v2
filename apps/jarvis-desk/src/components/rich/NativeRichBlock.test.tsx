import { describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fireEvent, render, screen } from '@testing-library/react'
import { FladeKontrolContext, NativeRichBlock, parseNativeRichSpec } from './NativeRichBlock'
import { WidgetPrompt } from './WidgetBlock'

describe('NativeRichBlock', () => {
  it('afviser ukendt, ugyldig og for stor struktur', () => {
    expect(parseNativeRichSpec('{')).toBeNull()
    expect(parseNativeRichSpec('{"type":"chart"}')).toBeNull()
    const spec = parseNativeRichSpec(JSON.stringify({
      type: 'stats', items: Array.from({ length: 20 }, (_, i) => ({ label: `L${i}`, value: `${i}` })),
    }))
    expect(spec?.type).toBe('stats')
    if (spec?.type === 'stats') expect(spec.items).toHaveLength(8)
  })

  it.each([
    [{ type: 'callout', tone: 'warning', title: 'Pas på', body: 'Noget vigtigt' }, 'Noget vigtigt'],
    [{ type: 'stats', title: 'Tal', items: [{ label: 'Fart', value: '42', detail: 'ms' }] }, '42'],
    [{ type: 'timeline', title: 'Plan', items: [{ time: 'Nu', title: 'Byg', detail: 'Først', status: 'current' }] }, 'Byg'],
    [{ type: 'comparison', title: 'Valg', columns: ['A', 'B'], rows: [{ label: 'Pris', values: ['1', '2'] }] }, 'Pris'],
    [{ type: 'location', title: 'Her', address: 'København' }, 'Åbn kort'],
  ])('renderer %s', (spec, expected) => {
    render(<NativeRichBlock code={JSON.stringify(spec)} />)
    expect(screen.getByText(expected)).toBeInTheDocument()
  })

  it('sender valg med synligt oprindelsesmærke', () => {
    const send = vi.fn()
    render(<WidgetPrompt.Provider value={send}><NativeRichBlock code={JSON.stringify({
      type: 'choices', title: 'Vælg', options: [{ label: 'Fortsæt', prompt: 'gør det' }],
    })} /></WidgetPrompt.Provider>)
    fireEvent.click(screen.getByRole('button', { name: 'Fortsæt' }))
    expect(send).toHaveBeenCalledWith('[fra valgkort] gør det')
  })

  // `control` (14/11-2026): den FØRSTE flade med lokal state. Det der skal
  // måles er ikke at den ser rigtig ud — det er at slideren rykker UDEN at et
  // modelkald går ud. `send` må ikke blive kaldt én eneste gang.
  const kontrol = (felter: unknown[], title = '') => JSON.stringify({ type: 'control', title, fields: felter })
  const slider = { kind: 'slider', bind: 'timer', label: 'Timer', min: 1, max: 24, step: 1, value: 8 }

  it('slideren rykker lokalt — nul modelkald', () => {
    const send = vi.fn()
    render(<FladeKontrolContext.Provider value><WidgetPrompt.Provider value={send}>
      <NativeRichBlock code={kontrol([slider, { kind: 'text', text: 'Du har valgt {timer} timer.' }])} />
    </WidgetPrompt.Provider></FladeKontrolContext.Provider>)
    const input = screen.getByRole('slider') as HTMLInputElement
    expect(input.value).toBe('8')
    fireEvent.change(input, { target: { value: '15' } })
    expect(input.value).toBe('15')
    // Det er hele pointen: teksten regnes om lokalt, og der gik intet run ud.
    expect(screen.getByText('Du har valgt 15 timer.')).toBeInTheDocument()
    expect(send).not.toHaveBeenCalled()
  })

  it('filtrerer felter væk der ikke kan bindes eller har ulovligt interval', () => {
    // Uden `bind` er der intet at holde state i — feltet ville se interaktivt
    // ud uden at være det.
    const udenBind = parseNativeRichSpec(kontrol([{ kind: 'slider', label: 'L', min: 1, max: 2, value: 1 }]))
    expect(udenBind).toBeNull()
    // `max <= min` giver et håndtag der ikke kan trækkes.
    expect(parseNativeRichSpec(kontrol([{ ...slider, min: 10, max: 2 }]))).toBeNull()
    // Kun tekstfelter er ingen kontrol.
    expect(parseNativeRichSpec(kontrol([{ kind: 'text', text: 'hej' }]))).toBeNull()
  })

  it('afviser NaN og Infinity — de ER tal for typeof, men ikke for en slider', () => {
    // Målt: `typeof NaN === 'number'` slipper igennem en naiv kontrol og giver
    // `value={NaN}`, altså en tavs tom slider uden fejl nogen steder.
    expect(parseNativeRichSpec(kontrol([{ ...slider, min: NaN }]))).toBeNull()
    expect(parseNativeRichSpec(kontrol([{ ...slider, max: Infinity }]))).toBeNull()
    // En `value` uden for intervallet klem-mes ind i stedet for at kassere.
    const klemt = parseNativeRichSpec(kontrol([{ ...slider, value: 999 }]))
    expect(klemt?.type === 'control' && klemt.fields[0]).toMatchObject({ value: 24 })
  })

  it('er gated: uden chat-flaget vises fladen slet ikke', () => {
    // `BlocksRenderer` deles med code mode. Default i konteksten er falsk, så
    // glemmer nogen at sætte flaget, forsvinder fladen frem for at dukke op i
    // maskinrummet.
    const { container } = render(<NativeRichBlock code={kontrol([slider])} />)
    expect(container.querySelector('.native-control')).toBeNull()
  })

  // `box` (14/11-2026): en flade der bærer børn. Den ÆGTE test er ikke at den
  // ser rigtig ud, men at en tur med en nestet flade ikke koster ét eneste
  // modelkald: hverken `send` (WidgetPrompt) eller netværket må røres.
  const box = (children: unknown[], title = '') => JSON.stringify({ type: 'box', title, children })
  const callout = { type: 'callout', title: 'Barn', body: 'Indre tekst' }
  const dyb = (n: number): Record<string, unknown> =>
    n <= 1 ? callout : { type: 'box', title: `niveau${n}`, children: [dyb(n - 1)] }

  it('GUARD: en nestet flade koster nul modelkald', () => {
    const send = vi.fn()
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => Promise.reject(new Error('intet netværk')))
    try {
      render(<FladeKontrolContext.Provider value><WidgetPrompt.Provider value={send}>
        <NativeRichBlock code={box([
          callout,
          { type: 'box', title: 'indre', children: [
            { type: 'control', title: 'K', fields: [slider, { kind: 'text', text: 'Du har valgt {timer} timer.' }] },
          ] },
        ], 'Ydre')} />
      </WidgetPrompt.Provider></FladeKontrolContext.Provider>)
      expect(screen.getByText('Indre tekst')).toBeInTheDocument()
      // Slideren to lag nede rykker lokalt og ændrer barnets tekst.
      fireEvent.change(screen.getByRole('slider'), { target: { value: '15' } })
      expect(screen.getByText('Du har valgt 15 timer.')).toBeInTheDocument()
      expect(send).not.toHaveBeenCalled()
      expect(fetchSpy).not.toHaveBeenCalled()
    } finally {
      fetchSpy.mockRestore()
    }
  })

  it('GUARD: form-felter læser værdien FØR state-kaldet — ikke fra et tømt event', () => {
    // Målt 14/11-2026: `select` og `toggle` læste `e.currentTarget` inde i
    // opdateringsfunktionen. React nulstiller `currentTarget` når handleren
    // returnerer, så den kørende funktion læste `.value` af `null` og kastede
    // «Cannot read properties of null (reading 'value')». Hele beskeden faldt
    // ud af visningen. Slideren var upåvirket, fordi den læste værdien ud i en
    // lokal variabel først — det er mønstret de to andre nu følger.
    //
    // VAGTEN LÆSER KILDEN, fordi en adfærdstest ikke kan fange det: jsdom
    // nulstiller ikke `currentTarget` som en rigtig browser gør, så mutations-
    // prøven bestod med den brækkede kode. Målt, ikke antaget.
    const kilde = readFileSync(resolve(process.cwd(), 'src/components/rich/NativeRichBlock.tsx'), 'utf8')
    expect(kilde).not.toMatch(/setKontrolVaerdi\(\(forrige\)\s*=>\s*\(\{[^}]*e\.currentTarget/)
    expect(kilde.match(/const v = e\.currentTarget\.(value|checked)/g) ?? []).toHaveLength(2)

    const send = vi.fn()
    const form = JSON.stringify({
      type: 'form', title: 'Prøv',
      fields: [
        { kind: 'select', bind: 'vej', label: 'Vej', options: ['Nesting', 'Katalog', 'DIL'], value: 'Nesting' },
        { kind: 'toggle', bind: 'kode', label: 'Rør code mode', value: false },
        { kind: 'text', text: 'Vej: {vej} — kode: {kode}' },
      ],
    })
    render(<FladeKontrolContext.Provider value><WidgetPrompt.Provider value={send}>
      <NativeRichBlock code={form} />
    </WidgetPrompt.Provider></FladeKontrolContext.Provider>)

    // Ingen af de to kald må kaste — det var selve fejlen.
    const valg = screen.getByRole('combobox') as HTMLSelectElement
    expect(() => fireEvent.change(valg, { target: { value: 'DIL' } })).not.toThrow()
    expect(valg.value).toBe('DIL')
    // `{kode}` står råt indtil toggle'en er rørt: `interpolér` falder tilbage
    // til pladsholderen når nøglen ikke findes i state. Ærligt, men uskønt —
    // checkboxen viser `false` mens teksten viser `{kode}`.
    expect(screen.getByText('Vej: DIL — kode: {kode}')).toBeInTheDocument()

    const knap = screen.getByRole('checkbox') as HTMLInputElement
    expect(() => fireEvent.click(knap)).not.toThrow()
    expect(knap.checked).toBe(true)
    expect(screen.getByText('Vej: DIL — kode: true')).toBeInTheDocument()

    // Stadig nul modelkald: hele pointen med lokal state.
    expect(send).not.toHaveBeenCalled()
  })

  it('box med børn renderer dem rekursivt', () => {
    render(<NativeRichBlock code={box([callout, { type: 'box', title: 'Indre', children: [callout] }], 'Ydre')} />)
    expect(screen.getByLabelText('Ydre')).toBeInTheDocument()
    expect(screen.getByLabelText('Indre')).toBeInTheDocument()
    expect(screen.getAllByText('Indre tekst')).toHaveLength(2)
  })

  it('box med ukendt barnetype: barnet filtreres væk, boxen vises', () => {
    render(<NativeRichBlock code={box([{ type: 'chart', title: 'X' }, 'streng', 42, callout], 'Ydre')} />)
    expect(screen.getByLabelText('Ydre')).toBeInTheDocument()
    expect(screen.getByText('Indre tekst')).toBeInTheDocument()
    // Kun ukendte børn = intet at bære = ingen flade (ligesom stats uden items).
    expect(parseNativeRichSpec(box([{ type: 'chart' }]))).toBeNull()
  })

  it('box i dybde 4 afvises (dybde 3 er det yderste)', () => {
    expect(parseNativeRichSpec(JSON.stringify(dyb(4)))?.type).toBe('box')
    // Fire bokse i hinanden: den inderste (dybde 4) afvises, og de tomme
    // forfædre falder med den — der er ingen børn tilbage at bære.
    const fire = { type: 'box', children: [{ type: 'box', children: [{ type: 'box', children: [{ type: 'box', children: [callout] }] }] }] }
    expect(parseNativeRichSpec(JSON.stringify(fire))).toBeNull()
    // Men et søskendebarn ved siden af den afviste bliver stående.
    const med = { type: 'box', title: 'Rod', children: [callout, { type: 'box', children: [{ type: 'box', children: [{ type: 'box', children: [callout] }] }] }] }
    const spec = parseNativeRichSpec(JSON.stringify(med))
    expect(spec?.type === 'box' && spec.children).toHaveLength(1)
  })

  it('uafsluttet JSON i et barn kaster ikke', () => {
    const halv = box([callout]).slice(0, -12)
    expect(() => parseNativeRichSpec(halv)).not.toThrow()
    expect(parseNativeRichSpec(halv)).toBeNull()
    expect(() => render(<NativeRichBlock code={halv} />)).not.toThrow()
  })

  // Målt 24/10-2026: boksen fik alle seks flader til at skære sig ud af
  // brødteksten. Data (comparison/timeline/stats) skal ligge i tekstens
  // materiale; kun objekter (callout/choices/location) skal skille sig ud.
  it.each([
    [{ type: 'callout', title: 'T', body: 'B' }, true],
    [{ type: 'choices', title: 'T', options: [{ label: 'A', prompt: 'a' }] }, true],
    [{ type: 'location', title: 'T', address: 'K' }, true],
    [{ type: 'stats', title: 'T', items: [{ label: 'L', value: 'V' }] }, false],
    [{ type: 'timeline', title: 'T', items: [{ title: 'X' }] }, false],
    [{ type: 'comparison', title: 'T', columns: ['A', 'B'], rows: [{ label: 'R', values: ['1', '2'] }] }, false],
  ])('boks kun på objekter: %s', (spec, boxed) => {
    const { container } = render(<NativeRichBlock code={JSON.stringify(spec)} />)
    const el = container.querySelector('.native-rich')
    expect(el).toBeInTheDocument()
    expect(el!.classList.contains('native-card')).toBe(boxed)
  })
})
