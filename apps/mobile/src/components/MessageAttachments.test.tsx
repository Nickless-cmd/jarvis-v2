import { act, fireEvent, render } from '@testing-library/react-native'
import { MessageAttachments, formatSize } from './MessageAttachments'

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config: { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' } })
}))

describe('formatSize', () => {
  it('viser bytes under 1 kB', () => {
    expect(formatSize(512)).toBe('512 B')
  })

  it('bruger dansk komma og skjuler tom decimal', () => {
    expect(formatSize(1536)).toBe('1,5 kB')
    expect(formatSize(2048)).toBe('2 kB')
  })

  it('gaar op i MB og GB', () => {
    expect(formatSize(5 * 1024 * 1024)).toBe('5 MB')
    expect(formatSize(3 * 1024 * 1024 * 1024)).toBe('3 GB')
  })
})

it('åbner billedvedhæftninger i fullscreen preview ved tryk', async () => {
  const screen = await render(
    <MessageAttachments
      items={[{ type: 'image', attachment_id: 'img1', filename: 'køkken.png' }]}
    />
  )

  await act(async () => {
    fireEvent.press(screen.getByTestId('attachment-open-img1'))
  })

  expect(screen.getByText('køkken.png')).toBeTruthy()
  expect(screen.getByTestId('attachment-fullscreen-image')).toBeTruthy()
})
