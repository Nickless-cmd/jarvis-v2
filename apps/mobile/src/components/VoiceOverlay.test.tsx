import { fireEvent, render } from '@testing-library/react-native'
import { VoiceOverlay } from './VoiceOverlay'

const base = {
  active: true,
  state: 'idle' as const,
  mode: 'hands-free' as const,
  lastProvider: '',
  setMode: jest.fn(),
  startListening: jest.fn(),
  stopListening: jest.fn(),
  interrupt: jest.fn(),
  exit: jest.fn(),
}

const wrap = (props: Partial<React.ComponentProps<typeof VoiceOverlay>> = {}) =>
  render(<VoiceOverlay {...base} {...props} />)

describe('VoiceOverlay', () => {
  // Samtalen er FULDSKÆRM. Et godkendelses-kort der kun bor i chatten er
  // usynligt herinde: man skulle lukke samtalen for at opdage at der
  // overhovedet blev spurgt, og imens stod runnet stille og ventede.
  it('viser en ventende godkendelse inde i samtalen', async () => {
    const onApprove = jest.fn()
    const { getByText } = await wrap({
      approval: { approvalId: 'a1', tool: 'bash', message: 'Må jeg køre den?', detail: 'ls -la' },
      onApprove,
      onDeny: jest.fn(),
    })

    getByText('bash')
    getByText('Jeg venter på dit svar')
    fireEvent.press(getByText('Tillad'))
    expect(onApprove).toHaveBeenCalled()
  })

  it('viser intet kort når der ikke er noget at godkende', async () => {
    const { queryByText } = await wrap()
    expect(queryByText('Tillad')).toBeNull()
    expect(queryByText('Jeg venter på dit svar')).toBeNull()
  })

  // Uden en godkendelse må knapperne ikke kunne kaldes ved et uheld.
  it('afbryder ham når man trykker mens han taler', async () => {
    const interrupt = jest.fn()
    const { getByLabelText } = await wrap({ state: 'speaking', interrupt })
    fireEvent.press(getByLabelText('Afbryd Jarvis'))
    expect(interrupt).toHaveBeenCalled()
  })

  it('kan sende brugeren videre til kamera-kontekst uden at kalde det live vision', async () => {
    const onCameraContext = jest.fn()
    const { getByText, queryByText } = await wrap({ onCameraContext })

    fireEvent.press(getByText('Kamera'))

    expect(onCameraContext).toHaveBeenCalledTimes(1)
    expect(queryByText('Live vision')).toBeNull()
  })
})
