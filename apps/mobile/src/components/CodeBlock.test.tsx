import { act, fireEvent, render } from '@testing-library/react-native'
import * as Clipboard from 'expo-clipboard'
import { CodeBlock } from './CodeBlock'

jest.mock('expo-clipboard', () => ({ setStringAsync: jest.fn().mockResolvedValue(undefined) }))

describe('CodeBlock', () => {
  it('viser sprogets navn og koden', async () => {
    const screen = await render(<CodeBlock code={'const x = 1\n'} language="TypeScript" />)
    expect(screen.getByText('typescript')).toBeTruthy()
  })

  it('kopierer koden UDEN den afsluttende newline', async () => {
    const screen = await render(<CodeBlock code={'echo hej\n'} language="bash" />)
    await act(async () => {
      fireEvent.press(screen.getByTestId('code-copy'))
    })
    expect(Clipboard.setStringAsync).toHaveBeenCalledWith('echo hej')
  })
})
