import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { ApprovalCard } from './ApprovalCard'

it('renders approval details and calls explicit decisions', async () => {
  const onApprove = jest.fn()
  const onDeny = jest.fn()
  const screen = await render(
    <ApprovalCard
      approval={{
        approvalId: 'approval-1',
        tool: 'shell',
        message: 'Jarvis vil køre en kommando.',
        detail: 'ls -la'
      }}
      onApprove={onApprove}
      onDeny={onDeny}
    />
  )

  await waitFor(() => expect(screen.getByText('shell')).toBeTruthy())
  expect(screen.getByText('Jarvis vil køre en kommando.')).toBeTruthy()
  expect(screen.getByText('ls -la')).toBeTruthy()

  await fireEvent.press(screen.getByText('Afvis'))
  await fireEvent.press(screen.getByText('Tillad'))

  expect(onDeny).toHaveBeenCalledTimes(1)
  expect(onApprove).toHaveBeenCalledTimes(1)
})
