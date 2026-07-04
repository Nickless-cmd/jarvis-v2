import { fireEvent, render } from '@testing-library/react-native'
import { ErrorCard } from './ErrorCard'
import type { StreamErrorInfo } from '../state/StreamContext'

function makeError(overrides: Partial<StreamErrorInfo> = {}): StreamErrorInfo {
  return {
    code: 'provider.timeout',
    kind: 'provider.timeout',
    severity: 'error',
    message: 'Udbyderen svarede ikke i tide.',
    fixHint: 'Prøv igen om lidt.',
    retryable: true,
    correlationId: 'run-abcdef123456',
    recoverable: 'retry',
    scope: 'run',
    ...overrides
  }
}

describe('ErrorCard', () => {
  it('viser familie-titel, besked, system-handling og fix_hint', async () => {
    const screen = await render(<ErrorCard error={makeError()} onDismiss={jest.fn()} />)
    expect(screen.getByText('Udbyder-problem')).toBeTruthy()
    expect(screen.getByText('Udbyderen svarede ikke i tide.')).toBeTruthy()
    expect(screen.getByText('Jeg prøvede igen.')).toBeTruthy()
    expect(screen.getByText('Prøv igen om lidt.')).toBeTruthy()
    // correlation_id vist afkortet
    expect(screen.getByText('#run-abcd')).toBeTruthy()
  })

  it('kritisk severity -> "Kritisk fejl"', async () => {
    const screen = await render(
      <ErrorCard error={makeError({ severity: 'critical' })} onDismiss={jest.fn()} />
    )
    expect(screen.getByText('Kritisk fejl')).toBeTruthy()
  })

  it('viser "Prøv igen" kun når retryable + onRetry sat, og kalder den', async () => {
    const onRetry = jest.fn()
    const screen = await render(
      <ErrorCard error={makeError()} onRetry={onRetry} onDismiss={jest.fn()} />
    )
    await fireEvent.press(screen.getByText('Prøv igen'))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('skjuler retry når ikke retryable', async () => {
    const screen = await render(
      <ErrorCard error={makeError({ retryable: false })} onRetry={jest.fn()} onDismiss={jest.fn()} />
    )
    expect(screen.queryByText('Prøv igen')).toBeNull()
  })

  it('luk-knap kalder onDismiss', async () => {
    const onDismiss = jest.fn()
    const screen = await render(<ErrorCard error={makeError()} onDismiss={onDismiss} />)
    await fireEvent.press(screen.getByLabelText('luk'))
    expect(onDismiss).toHaveBeenCalledTimes(1)
  })
})
