import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BlocksRenderer } from './BlocksRenderer'
import { RaekkeTranskript } from './RaekkeTranskript'
import { VisningContext } from '../../lib/visning'
import { billedKilde, billedSti, levendeBilledArbejde } from './ImageGeneration'
import type { ApiConfig } from '../../lib/api'
import type { ContentBlock } from '../../lib/sseProtocol'

/** Hentningen af selve billedet går gennem `/visning/billede`, og den skal
 *  kunne måles — derfor en optager i stedet for et rigtigt netværk. */
const hentede: string[] = []
let hentFejler = false
const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' } as unknown as ApiConfig

vi.mock('../../lib/api', async (importOriginal) => {
  const faktisk = await importOriginal<typeof import('../../lib/api')>()
  return {
    ...faktisk,
    fetchBlobWithAuth: async (_c: unknown, url: string) => {
      hentede.push(url)
      if (hentFejler) throw new Error('403')
      return new Blob(['billede'], { type: 'image/png' })
    },
  }
})

beforeEach(() => {
  hentede.length = 0
  hentFejler = false
  URL.createObjectURL = vi.fn(() => 'blob:analyse')
  URL.revokeObjectURL = vi.fn()
})

/**
 * Animationen for `analyze_image`.
 *
 * Hvorfor den findes: målt på CT105 27/9-2026 over fjorten dage er
 * `analyze_image` 232 kald med **median 8,49 s** og p90 28,6 s (219 ok, 13
 * fejl). Otte sekunder hvor der intet sker på skærmen er rigeligt til at tro
 * turen er gået i stå. Til sammenligning er `operator_screenshot` og
 * `jarvis_browser_screenshot` målt til ~0,1 s — de TAGER billeder og har
 * intet at animere.
 *
 * `read_attachment` er med vilje IKKE med: alle 18 målte kald var fejl, så
 * der findes endnu ikke én måling af et vellykket kald at bygge på.
 *
 * Testene sidder på ALLE TRE kaldesteder. Betingelsen stod før ordret tre
 * steder, og det var præcis dér `openrouter_image_edit` blev glemt.
 */

const analyse = (input: Record<string, unknown>, status: 'running' | 'done' = 'running'): ContentBlock =>
  ({ type: 'tool_use', id: 'a1', name: 'analyze_image', input, status })

describe('billedKilde', () => {
  it('tager sidste led af en sti', () => {
    expect(billedKilde({ image_path: '/home/bs/billeder/kat.png' })).toBe('kat.png')
  })

  it('klarer en sti med bagudskråstreger', () => {
    expect(billedKilde({ image_path: 'C:\\Users\\bs\\kat.png' })).toBe('kat.png')
  })

  it('en sti der ender på skråstreg giver mappen, ikke tom streng', () => {
    expect(billedKilde({ image_path: '/home/bs/billeder/' })).toBe('billeder')
  })

  it('falder tilbage til værten på en URL', () => {
    expect(billedKilde({ image_url: 'https://eksempel.dk/a/b/kat.png?x=1' })).toBe('eksempel.dk')
  })

  it('stien vinder over URL\'en når begge er der', () => {
    expect(billedKilde({ image_path: '/tmp/kat.png', image_url: 'https://eksempel.dk/x.png' })).toBe('kat.png')
  })

  it('en URL der ikke kan læses giver tom streng frem for at gætte', () => {
    expect(billedKilde({ image_url: 'ikke en url' })).toBe('')
  })

  it('intet input giver tom streng', () => {
    expect(billedKilde(undefined)).toBe('')
    expect(billedKilde({})).toBe('')
    expect(billedKilde({ image_path: 42 })).toBe('')
  })
})

describe('levendeBilledArbejde', () => {
  it('kender analysen fra genereringen', () => {
    expect(levendeBilledArbejde([{ name: 'analyze_image', status: 'running', input: { image_path: '/x/k.png' } }]))
      .toEqual({ slags: 'analyse', kilde: 'k.png', sti: '/x/k.png' })
    expect(levendeBilledArbejde([{ name: 'openrouter_image', status: 'running', input: {} }]))
      .toEqual({ slags: 'generering' })
  })

  it('alle tre billedværktøjer tæller som generering', () => {
    for (const navn of ['openrouter_image', 'openrouter_image_edit', 'pollinations_image']) {
      expect(levendeBilledArbejde([{ name: navn, status: 'running', input: {} }])).toEqual({ slags: 'generering' })
    }
  })

  it('et kald der er færdigt er ikke levende arbejde', () => {
    expect(levendeBilledArbejde([{ name: 'analyze_image', status: 'done', input: {} }])).toBeNull()
    expect(levendeBilledArbejde([{ name: 'analyze_image', status: 'error', input: {} }])).toBeNull()
  })

  it('manglende status regnes som kørende — sådan bar streamen det før', () => {
    expect(levendeBilledArbejde([{ name: 'analyze_image', input: {} }])).toEqual({ slags: 'analyse', kilde: '', sti: '' })
  })

  it('læser analyse-stien fra delvis JSON mens værktøjets argumenter streames', () => {
    expect(levendeBilledArbejde([{ name: 'analyze_image', status: 'running', input: {}, partialJson: '{"image_path":"/tmp/foto.png"}' }]))
      .toEqual({ slags: 'analyse', kilde: 'foto.png', sti: '/tmp/foto.png' })
  })

  it('andre værktøjer giver intet', () => {
    expect(levendeBilledArbejde([
      { name: 'read_file', status: 'running', input: {} },
      { name: 'bash', status: 'running', input: {} },
    ])).toBeNull()
  })

  it('kører begge, vinder det der blev startet først', () => {
    expect(levendeBilledArbejde([
      { name: 'analyze_image', status: 'running', input: { image_path: '/x/k.png' } },
      { name: 'openrouter_image', status: 'running', input: {} },
    ])).toEqual({ slags: 'analyse', kilde: 'k.png', sti: '/x/k.png' })
  })

  it('tom liste giver null', () => {
    expect(levendeBilledArbejde([])).toBeNull()
  })
})

describe('hvilken sti hentes billedet fra', () => {
  /**
   * Målt på telefonen 28/9-2026: Jarvis beskar et skærmbillede til
   * `/tmp/ss_mid.png` og analyserede det. Kortet viste navnet, men rammen stod
   * tom — `/visning/billede` svarer 403 på en bar `/tmp`-sti, og skal blive
   * ved med det. Serveren lægger derfor en hentbar sti i `visning_sti`:
   * originalen når den må vises, ellers en hvidlistet kopi.
   */
  it('serverens visning_sti vinder over image_path', () => {
    expect(billedSti({ image_path: '/tmp/ss_mid.png',
      visning_sti: '/tmp/jarvisx-vision-abc.png' })).toBe('/tmp/jarvisx-vision-abc.png')
  })

  it('uden visning_sti bruges image_path — en ældre server', () => {
    expect(billedSti({ image_path: '/home/bs/.jarvis-v2/uploads/a/k.png' }))
      .toBe('/home/bs/.jarvis-v2/uploads/a/k.png')
  })

  it('en visning_sti der ikke er absolut ignoreres', () => {
    expect(billedSti({ image_path: '/x/k.png', visning_sti: 'relativ.png' })).toBe('/x/k.png')
    expect(billedSti({ image_path: '/x/k.png', visning_sti: '' })).toBe('/x/k.png')
  })

  it('etiketten viser stadig det RIGTIGE filnavn, ikke kopiens', () => {
    expect(billedKilde({ image_path: '/tmp/ss_mid.png',
      visning_sti: '/tmp/jarvisx-vision-abc.png' })).toBe('ss_mid.png')
  })
})

describe('animationen på skærmen', () => {
  it('BlocksRenderer: runden viser scanningen mens analysen kører', () => {
    render(<BlocksRenderer blocks={[analyse({ image_path: '/home/bs/skaerm.png' })]} density="compact" streaming />)
    expect(screen.getByLabelText('Analyserer skaerm.png')).toBeInTheDocument()
    // Det er ikke generatorens gitter — de to må kunne kendes fra hinanden.
    expect(screen.queryByLabelText('Genererer billede')).not.toBeInTheDocument()
  })

  it('BlocksRenderer: også i visningen «Alt», hvor hvert kald står for sig', () => {
    render(<VisningContext.Provider value="verbose">
      <BlocksRenderer blocks={[analyse({ image_path: '/home/bs/skaerm.png' })]} density="compact" streaming />
    </VisningContext.Provider>)
    expect(screen.getByLabelText('Analyserer skaerm.png')).toBeInTheDocument()
  })

  it('BlocksRenderer: generatoren har stadig sin egen animation', () => {
    render(<BlocksRenderer density="compact" streaming blocks={[
      { type: 'tool_use', id: 'g1', name: 'openrouter_image_edit', input: { prompt: 'kat' }, status: 'running' },
    ]} />)
    expect(screen.getByLabelText('Genererer billede')).toBeInTheDocument()
  })

  it('RaekkeTranskript: scanningen står uden for det foldede turhoved', () => {
    render(<RaekkeTranskript blocks={[analyse({ image_path: '/home/bs/skaerm.png' })]} streaming />)
    expect(screen.getByLabelText('Analyserer skaerm.png')).toBeInTheDocument()
  })

  it('RaekkeTranskript: generering vises også under en arbejdsrunde', () => {
    render(<RaekkeTranskript blocks={[
      { type: 'thinking', thinking: 'Laver billede' },
      { type: 'tool_use', id: 'g1', name: 'openrouter_image', input: {}, status: 'running' },
    ]} streaming />)
    expect(screen.getByLabelText('Genererer billede')).toBeInTheDocument()
  })

  it('uden navn står den stadig — men uden at finde på et', () => {
    render(<BlocksRenderer blocks={[analyse({})]} density="compact" streaming />)
    expect(screen.getByLabelText('Analyserer billede')).toBeInTheDocument()
  })

  it('når turen er slut er animationen væk', () => {
    render(<BlocksRenderer blocks={[analyse({ image_path: '/x/k.png' }, 'done')]} density="compact" streaming={false} />)
    expect(screen.queryByLabelText(/Analyserer/)).not.toBeInTheDocument()
  })

  it('et færdigt kald midt i en kørende stream animerer ikke', () => {
    render(<BlocksRenderer blocks={[analyse({ image_path: '/x/k.png' }, 'done')]} density="compact" streaming />)
    expect(screen.queryByLabelText(/Analyserer/)).not.toBeInTheDocument()
  })

  it('ingen procent — backend har ingen', () => {
    render(<BlocksRenderer blocks={[analyse({ image_path: '/x/k.png' })]} density="compact" streaming />)
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument()
  })
})

describe('billedet under scanneren', () => {
  const skaerm = { image_path: '/home/bs/.jarvis-v2/uploads/chat-x/skaerm.png' }

  it('henter det billede der kigges på gennem den hvidlistede rute', async () => {
    const { container } = render(
      <BlocksRenderer blocks={[analyse(skaerm)]} density="compact" streaming config={config} />)
    await waitFor(() => expect(hentede).toHaveLength(1))
    expect(hentede[0]).toBe(`/visning/billede?sti=${encodeURIComponent(skaerm.image_path)}`)
    expect(container.querySelector('img.image-analysis-billede')).not.toBeNull()
  })

  it('en Windows-sti hentes ikke — ruten tager kun absolutte unix-stier', () => {
    render(<BlocksRenderer blocks={[analyse({ image_path: 'C:\\Users\\bs\\kat.png' })]}
      density="compact" streaming config={config} />)
    expect(hentede).toHaveLength(0)
  })

  it('kun en URL hentes ikke — der er ingen sti at gå efter', () => {
    render(<BlocksRenderer blocks={[analyse({ image_url: 'https://eksempel.dk/kat.png' })]}
      density="compact" streaming config={config} />)
    expect(hentede).toHaveLength(0)
  })

  it('uden config står rammen tom frem for at kaste', () => {
    render(<BlocksRenderer blocks={[analyse(skaerm)]} density="compact" streaming />)
    expect(hentede).toHaveLength(0)
  })

  it('en afvist hentning giver tom ramme — kortet står stadig', async () => {
    hentFejler = true
    const { container } = render(
      <BlocksRenderer blocks={[analyse(skaerm)]} density="compact" streaming config={config} />)
    await waitFor(() => expect(hentede).toHaveLength(1))
    expect(container.querySelector('img.image-analysis-billede')).toBeNull()
    expect(screen.getByLabelText('Analyserer skaerm.png')).toBeInTheDocument()
  })
})

describe('billedSti', () => {
  it('giver den fulde sti når den er absolut', () => {
    expect(billedSti({ image_path: '/home/bs/skaerm.png' })).toBe('/home/bs/skaerm.png')
  })

  it('giver tom streng for alt der ikke er en absolut unix-sti', () => {
    expect(billedSti({ image_path: 'C:\\Users\\bs\\kat.png' })).toBe('')
    expect(billedSti({ image_path: 'relativ/kat.png' })).toBe('')
    expect(billedSti({ image_url: 'https://eksempel.dk/kat.png' })).toBe('')
    expect(billedSti(undefined)).toBe('')
    expect(billedSti({ image_path: 42 })).toBe('')
  })
})
