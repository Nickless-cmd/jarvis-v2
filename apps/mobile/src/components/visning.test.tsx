import { act, fireEvent, render } from '@testing-library/react-native'
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
