import { render, waitFor } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import { billedArbejdeFor, billedKilde, billedSti } from '../lib/billedArbejde'
import { hentTilCache } from './AuthImage'
import type { ContentBlock } from '../lib/sseProtocol'
import { initialStreamState, streamReducer } from '../lib/streamReducer'

/** Hentningen af selve billedet skal kunne måles — ikke et rigtigt netværk. */
jest.mock('./AuthImage', () => ({
  ...jest.requireActual('./AuthImage'),
  hentTilCache: jest.fn(async () => 'file:///cache/img-analyse.png'),
}))
const hentet = hentTilCache as unknown as jest.Mock

jest.mock('../state/AuthContext', () => {
  const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }
  return {
    ...jest.requireActual('../state/AuthContext'),
    useAuth: () => ({ config }),
    useAuthOptional: () => ({ config }),
  }
})

/**
 * Animationen for `analyze_image` — mobilens halvdel.
 *
 * Målt på CT105 27/9-2026 over fjorten dage: **232 kald, median 8,49 s**,
 * p90 28,6 s, 219 ok. Otte tavse sekunder er rigeligt til at tro turen er
 * gået i stå. `jarvis_browser_screenshot` er målt til 0,02 s og har derfor
 * ingen animation.
 *
 * `read_attachment` er bevidst ikke med: alle 18 målte kald var fejl, så der
 * findes endnu ikke én måling af et vellykket kald.
 */

const analyse = (input: Record<string, unknown>, status = 'running'): ContentBlock =>
  ({ type: 'tool_use', id: 'a1', name: 'analyze_image', input, status } as ContentBlock)

describe('billedKilde', () => {
  it('tager sidste led af stien', () => {
    expect(billedKilde({ image_path: '/home/bs/billeder/kat.png' })).toBe('kat.png')
  })

  it('klarer bagudskråstreger og en sti der ender på skråstreg', () => {
    expect(billedKilde({ image_path: 'C:\\Users\\bs\\kat.png' })).toBe('kat.png')
    expect(billedKilde({ image_path: '/home/bs/billeder/' })).toBe('billeder')
  })

  it('falder tilbage til værten på en URL — uden port og bruger', () => {
    expect(billedKilde({ image_url: 'https://eksempel.dk/a/kat.png?x=1' })).toBe('eksempel.dk')
    expect(billedKilde({ image_url: 'https://bs@eksempel.dk:8443/kat.png' })).toBe('eksempel.dk')
  })

  it('stien vinder over URL\'en', () => {
    expect(billedKilde({ image_path: '/tmp/kat.png', image_url: 'https://eksempel.dk/x.png' })).toBe('kat.png')
  })

  it('noget der ikke er en URL giver tom streng frem for at gætte', () => {
    expect(billedKilde({ image_url: 'ikke en url' })).toBe('')
    expect(billedKilde(undefined)).toBe('')
    expect(billedKilde({ image_path: 42 })).toBe('')
  })

  /** Mens kaldet streames ind ligger argumenterne i `partialJson` som en
   *  streng, ikke i `input` — samme fælde som «+12 −4» faldt i. */
  it('læser argumenterne fra partialJson når input er tomt', () => {
    expect(billedKilde({}, '{"image_path": "/x/skaerm.png"}')).toBe('skaerm.png')
    expect(billedKilde(undefined, '{"image_path": "/x/skae')).toBe('')
  })

  it('input vinder over partialJson når begge er der', () => {
    expect(billedKilde({ image_path: '/a/rigtig.png' }, '{"image_path": "/b/gammel.png"}')).toBe('rigtig.png')
  })
})

describe('billedArbejdeFor', () => {
  it('kender analysen fra genereringen', () => {
    expect(billedArbejdeFor({ name: 'analyze_image', status: 'running', input: { image_path: '/x/k.png' } }))
      .toEqual({ slags: 'analyse', kilde: 'k.png', sti: '/x/k.png' })
    expect(billedArbejdeFor({ name: 'openrouter_image', status: 'running' })).toEqual({ slags: 'generering' })
  })

  it('alle tre billedværktøjer tæller som generering', () => {
    for (const navn of ['openrouter_image', 'openrouter_image_edit', 'pollinations_image']) {
      expect(billedArbejdeFor({ name: navn, status: 'running' })).toEqual({ slags: 'generering' })
    }
  })

  it('et færdigt eller fejlet kald er ikke levende arbejde', () => {
    expect(billedArbejdeFor({ name: 'analyze_image', status: 'done' })).toBeNull()
    expect(billedArbejdeFor({ name: 'analyze_image', status: 'error' })).toBeNull()
  })

  it('uden status er kaldet lige begyndt', () => {
    expect(billedArbejdeFor({ name: 'analyze_image' })).toEqual({ slags: 'analyse', kilde: '', sti: '' })
  })

  it('andre værktøjer giver intet', () => {
    expect(billedArbejdeFor({ name: 'bash', status: 'running' })).toBeNull()
  })
})

describe('kortet i strømmen', () => {
  it('viser scanningen med billedets navn mens analysen kører', async () => {
    const s = await render(<MessageList messages={[]} blocks={[analyse({ image_path: '/home/bs/skaerm.png' })]} working />)
    expect(s.getByTestId('image-analysis-progress')).toBeTruthy()
    expect(s.getByLabelText('Analyserer skaerm.png')).toBeTruthy()
    // Det er ikke generatorens gitter — de to skal kunne kendes fra hinanden.
    expect(s.queryByTestId('image-generation-progress')).toBeNull()
    expect(s.queryByText(/%/)).toBeNull()
  })

  it('uden navn står den stadig — men finder ikke på et', async () => {
    const s = await render(<MessageList messages={[]} blocks={[analyse({})]} working />)
    expect(s.getByLabelText('Analyserer billede')).toBeTruthy()
  })

  it('et færdigt kald animerer ikke', async () => {
    const s = await render(<MessageList messages={[]} blocks={[analyse({ image_path: '/x/k.png' }, 'done')]} working />)
    expect(s.queryByTestId('image-analysis-progress')).toBeNull()
  })

  it('ventefladen forsvinder når Jarvis fortsætter med tekst', async () => {
    const s = await render(<MessageList messages={[]} working blocks={[
      analyse({ image_path: '/x/k.png' }),
      { type: 'text', text: 'Der står «Hej» på billedet.' },
    ]} />)
    expect(s.queryByTestId('image-analysis-progress')).toBeNull()
    expect(s.getByText('Der står «Hej» på billedet.')).toBeTruthy()
  })

  it('henter det billede der kigges på og lægger det under scanneren', async () => {
    hentet.mockClear()
    const s = await render(<MessageList messages={[]} blocks={[analyse({ image_path: '/home/bs/skaerm.png' })]} working />)
    await waitFor(() => expect(s.getByTestId('image-analysis-billede')).toBeTruthy())
    expect(hentet).toHaveBeenCalledWith(
      expect.objectContaining({ apiBaseUrl: 'https://api.srvlab.dk/' }),
      `/visning/billede?sti=${encodeURIComponent('/home/bs/skaerm.png')}`,
      '/home/bs/skaerm.png',
    )
  })

  it('henter intet for en Windows-sti — ruten ville afvise den', async () => {
    hentet.mockClear()
    await render(<MessageList messages={[]} blocks={[analyse({ image_path: 'C:\\Users\\bs\\kat.png' })]} working />)
    expect(hentet).not.toHaveBeenCalled()
  })

  /**
   * SYMPTOMET, fotograferet 28/9-2026: animationen stod uden navn og uden
   * billede. Aarsagen laa i stroemmen, ikke i kortet — serveren sender sin
   * EGEN tool_use-blok (med `image_path`) FOER `working_step`, og reducer'en
   * byggede en tom foreloebig blok af den sidste. To blokke for ét kald, den
   * tomme bagest, og `buildStreamingRows` beholder den SIDSTE venteflade.
   *
   * FRAMES NEDENFOR ER MAALT, ikke antaget. `visible_tool_exec.run_tool_batch`
   * bygger sit `working_step` med `tool_id`, `arguments` og `er_vaerktoej`;
   * den sekvens er koert gennem `visible_runs_sse_v2.translate_to_v2` og det
   * er RESULTATET der staar her — text-blok, tool_use, input_json_delta,
   * derefter system_event(working_step). Min foerste udgave af denne test gav
   * MessageList to haandbyggede blokke og maalte dermed min egen antagelse om
   * raekkefoelgen i stedet for serverens.
   */
  it('hele vejen: serverens MAALTE frames giver ÉT kort — med navn', async () => {
    const sti = '/home/bs/.jarvis-v2/uploads/chat-a/abc123_skaerm.png'
    const frames = [
      { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
      { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Jeg kigger på det nu.' } },
      { type: 'content_block_stop', index: 0 },
      { type: 'content_block_start', index: 1,
        content_block: { type: 'tool_use', id: 'call_00_X', name: 'analyze_image', input: {} } },
      { type: 'content_block_delta', index: 1,
        delta: { type: 'input_json_delta', partial_json: JSON.stringify({ image_path: sti, prompt: 'beskriv' }) } },
      { type: 'content_block_stop', index: 1 },
      { type: 'system_event', kind: 'working_step',
        payload: { type: 'working_step', action: 'analyze_image', detail: 'Analyserer billede',
          step: 1, status: 'running', tool_id: 'call_00_X', er_vaerktoej: true } },
    ]
    let st = initialStreamState()
    for (const f of frames) st = streamReducer(st, f as never)

    // Én blok pr. kald — ingen foreløbig tvilling.
    expect(st.blocks.filter((b) => b && b.type === 'tool_use')).toHaveLength(1)

    const s = await render(<MessageList messages={[]} working blocks={st.blocks as ContentBlock[]} />)
    expect(s.queryAllByTestId('image-analysis-progress')).toHaveLength(1)
    expect(s.getByLabelText('Analyserer abc123_skaerm.png')).toBeTruthy()
    expect(s.queryByLabelText('Analyserer billede')).toBeNull()
  })

  it('generatoren har stadig sit eget kort', async () => {
    const s = await render(<MessageList messages={[]} working blocks={[
      { type: 'tool_use', id: 'g1', name: 'pollinations_image', input: {}, status: 'running' } as ContentBlock,
    ]} />)
    expect(s.getByTestId('image-generation-progress')).toBeTruthy()
    expect(s.queryByTestId('image-analysis-progress')).toBeNull()
  })
})

describe('billedSti', () => {
  it('giver den fulde sti når den er absolut', () => {
    expect(billedSti({ image_path: '/home/bs/skaerm.png' })).toBe('/home/bs/skaerm.png')
  })

  it('giver tom streng for alt andet — ruten tager kun absolutte unix-stier', () => {
    expect(billedSti({ image_path: 'C:\\Users\\bs\\kat.png' })).toBe('')
    expect(billedSti({ image_url: 'https://eksempel.dk/kat.png' })).toBe('')
    expect(billedSti(undefined)).toBe('')
  })

  it('læser stien fra partialJson mens kaldet streames ind', () => {
    expect(billedSti({}, '{"image_path": "/x/skaerm.png"}')).toBe('/x/skaerm.png')
  })
})
