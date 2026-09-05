import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { NewWorkTaskSheet, buildNewWorkTaskPrompt } from './NewWorkTaskSheet'

it('bygger en konkret work-prompt med projekt og branch når de findes', () => {
  const prompt = buildNewWorkTaskPrompt({
    instruction: 'Ret review-tabben',
    project: '/media/projects/jarvis-v2',
    branch: 'codex/mobile',
    mode: 'code'
  })

  expect(prompt).toContain('Project: /media/projects/jarvis-v2')
  expect(prompt).toContain('Branch: codex/mobile')
  expect(prompt).toContain('Ret review-tabben')
})

it('sender ikke uden instruks', async () => {
  const onSubmit = jest.fn()
  const screen = await render(<NewWorkTaskSheet onSubmit={onSubmit} busy={false} />)

  await act(async () => {
    fireEvent.press(screen.getByTestId('new-work-submit'))
  })

  expect(onSubmit).not.toHaveBeenCalled()
})

it('sender prompt og mode som code som default', async () => {
  const onSubmit = jest.fn()
  const screen = await render(<NewWorkTaskSheet onSubmit={onSubmit} busy={false} />)

  await act(async () => {
    screen.getByTestId('new-work-instruction').props.onChangeText('Lav artifacts-flade')
  })
  await waitFor(() => expect(screen.getByTestId('new-work-instruction').props.value).toBe('Lav artifacts-flade'))
  await act(async () => {
    fireEvent.press(screen.getByTestId('new-work-submit'))
  })

  expect(onSubmit).toHaveBeenCalledWith({
    prompt: expect.stringContaining('Lav artifacts-flade'),
    mode: 'code'
  })
})
