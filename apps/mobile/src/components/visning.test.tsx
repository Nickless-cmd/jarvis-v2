import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { FlatList } from 'react-native'
import { MessageList } from './MessageList'
import { TopBarMenu } from './TopBarMenu'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { streamReducer, initialStreamState } from '../lib/streamReducer'
import type { StreamEvent } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'

/** Claude Desktops tre visninger (cc-desktop-chatview.md §1-2), Bjørn 19/9-2026. */
const tur = {
  id: 'a1', role: 'assistant', content: 'Fundet.', created_at: '2026-09-19T00:00:00Z',
  content_json: [
    { type: 'thinking', text: 'Hvor sidder værnet mon?', seconds: 4 },  // gemt form: `text` (målt på CT105)
    { type: 'tool_use', id: 't1', name: 'read_file', input: { path: '/a.py' } },
    { type: 'tool_use', id: 't2', name: 'read_file', input: { path: '/b.py' } },
    { type: 'tool_use_summary', summary: 'Læste værnet', preceding_tool_use_ids: ['t1', 't2'], thinking_summary: 'Ville finde værnet i ruten' },
    { type: 'text', text: 'Fundet.' },
  ],
} as unknown as ChatMessage

describe('visningerne', () => {
  it('normal: intet resumé, gruppen foldet', async () => {
    const s = await render(<MessageList messages={[tur]} blocks={[]} visning="normal" />)
    expect(s.queryByTestId('tanke-resume')).toBeNull()
    expect(s.queryByTestId('tool-group-details')).toBeNull()
  })
  it('Tænkning: det gemte resumé står over gruppen', async () => {
    const s = await render(<MessageList messages={[tur]} blocks={[]} visning="thinking" />)
    await fireEvent.press(s.getByTestId('turn-header'))
    expect(s.getByText('Ville finde værnet i ruten')).toBeTruthy()
  })
  it('Tænkning: et live resumé vinder', async () => {
    const s = await render(<MessageList messages={[tur]} blocks={[]} visning="thinking" tankeResumeer={{ t1: 'Live-resumé' }} />)
    await fireEvent.press(s.getByTestId('turn-header'))
    expect(s.getByText('Live-resumé')).toBeTruthy()
  })
  it('Alt: gruppen og tanken står åbne fra start', async () => {
    const s = await render(<MessageList messages={[tur]} blocks={[]} visning="verbose" />)
    expect(s.getByTestId('tool-group-details')).toBeTruthy()
    expect(s.getByText('Hvor sidder værnet mon?')).toBeTruthy()
  })

  it('aabner turen UDEN at skaermen rykker sig — offset kompenseres for ny hoejde', async () => {
    // Maalt 6/10-2026 (Bjoern): den gamle udgave kaldte
    // `scrollToIndex({viewPosition: 0.3})` og REV skaermen et nyt sted hen.
    // Kravet er at den staar bomstille: hovedet bliver hvor det er, og
    // arbejdet folder ned under det.
    const hop = jest.spyOn(FlatList.prototype, 'scrollToIndex').mockImplementation(() => undefined)
    const skub = jest.spyOn(FlatList.prototype, 'scrollToOffset').mockImplementation(() => undefined)
    try {
      const s = await render(<MessageList messages={[tur]} blocks={[]} visning="normal" />)
      // Skaermen staar 250 px oppe i historikken, og indholdet er 600 px hoejt.
      await act(async () => { fireEvent(s.getByTestId('traad'), 'scroll', { nativeEvent: {
        contentOffset: { x: 0, y: 250 },
        layoutMeasurement: { width: 400, height: 800 },
        contentSize: { width: 400, height: 600 },
      } }) })
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 600) })
      await act(async () => { fireEvent.press(s.getByTestId('turn-header')) })
      // Arbejdsraekkerne folder ud: indholdet vokser 600 -> 1000.
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 1000) })
      await waitFor(() => expect(skub).toHaveBeenCalledWith({ offset: 650, animated: false }))
      // Intet hop til en raekke: skaermen skal staa stille, ikke flyttes hen.
      expect(hop).not.toHaveBeenCalled()
    } finally {
      hop.mockRestore()
      skub.mockRestore()
    }
  })

  it('hopper IKKE til bunds: en maaling i den forkerte retning bruges ikke', async () => {
    // Maalt 6/10-2026 (Bjoern): efter den foerste rettelse foer skaermen til
    // BUNDS ved fold-ud og naesten til TOPS ved fold-ind. Aarsagen var at den
    // FOERSTE stoerrelsesaendring efter trykket blev brugt, uanset fortegn: kom
    // der en maaling den anden vej foerst (600 -> 560), blev skaermen skubbet
    // den vej, og den aegte aendring (-> 1000) stod ukompenseret tilbage.
    // Kravet er at skaermen staar bomstille — ogsaa naar maalingerne kommer i
    // flere bidder.
    const skub = jest.spyOn(FlatList.prototype, 'scrollToOffset').mockImplementation(() => undefined)
    try {
      const s = await render(<MessageList messages={[tur]} blocks={[]} visning="normal" />)
      await act(async () => { fireEvent(s.getByTestId('traad'), 'scroll', { nativeEvent: {
        contentOffset: { x: 0, y: 250 },
        layoutMeasurement: { width: 400, height: 800 },
        contentSize: { width: 400, height: 600 },
      } }) })
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 600) })
      await act(async () => { fireEvent.press(s.getByTestId('turn-header')) })
      // Foerst en maaling den FORKERTE vej — den maa ikke flytte skaermen.
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 560) })
      expect(skub).not.toHaveBeenCalled()
      // Saa den aegte: arbejdsraekkerne folder ud. Maalet er udgangs-offsettet
      // plus HELE aendringen siden trykket (250 + 400), ikke 250 + 440.
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 1000) })
      await waitFor(() => expect(skub).toHaveBeenCalledWith({ offset: 650, animated: false }))
    } finally {
      skub.mockRestore()
    }
  })

  it('folder sammen uden at fare til tops — samme faste maal den anden vej', async () => {
    // Modstykket til bund-hoppet: fold-ind melder en KORTERE hoejde, og skaermen
    // skal loeftes praecis lige saa meget som hovedet flytter sig.
    const skub = jest.spyOn(FlatList.prototype, 'scrollToOffset').mockImplementation(() => undefined)
    try {
      const s = await render(<MessageList messages={[tur]} blocks={[]} visning="verbose" />)
      // Aabnet tur: skaermen staar 650 px oppe, indholdet er 1000 px hoejt.
      await act(async () => { fireEvent(s.getByTestId('traad'), 'scroll', { nativeEvent: {
        contentOffset: { x: 0, y: 650 },
        layoutMeasurement: { width: 400, height: 800 },
        contentSize: { width: 400, height: 1000 },
      } }) })
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 1000) })
      // Luk turen (den er aaben i 'verbose', saa et tryk folder sammen).
      await act(async () => { fireEvent.press(s.getByTestId('turn-header')) })
      // En sen maaling der VOKSER maa ikke bruges her.
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 1040) })
      expect(skub).not.toHaveBeenCalled()
      // Den aegte: arbejdsraekkerne foldes ind, 1000 -> 600.
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 600) })
      await waitFor(() => expect(skub).toHaveBeenCalledWith({ offset: 250, animated: false }))
    } finally {
      skub.mockRestore()
    }
  })

  it('kompenserer IKKE naar intet tur-hoved blev foldet', async () => {
    const skub = jest.spyOn(FlatList.prototype, 'scrollToOffset').mockImplementation(() => undefined)
    try {
      const s = await render(<MessageList messages={[tur]} blocks={[]} visning="normal" />)
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 600) })
      await act(async () => { fireEvent(s.getByTestId('traad'), 'contentSizeChange', 400, 900) })
      expect(skub).not.toHaveBeenCalled()
    } finally {
      skub.mockRestore()
    }
  })
})

it('reduceren bærer resuméet — også uden etiket', () => {
  let st = initialStreamState()
  st = streamReducer(st, { type: 'system_event', kind: 'tool_round_label', payload: { etiket: '', tool_use_ids: ['t1'], tanke_resume: 'Ville læse testen' } } as unknown as StreamEvent)
  expect(st.tankeResumeer).toEqual({ t1: 'Ville læse testen' })
})

it('menuen: tre radiopunkter, valget sendes og menuen lukker', async () => {
  const onVisning = jest.fn()
  const onClose = jest.fn()
  const s = await render(
    <SafeAreaProvider initialMetrics={{ frame: { x: 0, y: 0, width: 400, height: 800 }, insets: { top: 0, left: 0, right: 0, bottom: 0 } }}>
      <TopBarMenu aaben onClose={onClose} onSync={() => {}} visning="normal" onVisning={onVisning} />
    </SafeAreaProvider>,
  )
  expect(s.getByTestId('visning-normal').props.accessibilityState).toEqual({ checked: true })
  await act(async () => { fireEvent.press(s.getByTestId('visning-thinking')) })
  expect(onVisning).toHaveBeenCalledWith('thinking')
  expect(onClose).toHaveBeenCalled()
})
