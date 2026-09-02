import { render } from '@testing-library/react-native'
import { ThoughtsList } from './ThoughtsList'

describe('ThoughtsList', () => {
  it('siger aabent naar han ikke har delt noget', async () => {
    const s = await render(<ThoughtsList items={[]} />)
    expect(s.getByText('Han har ikke delt noget af sig selv endnu.')).toBeTruthy()
  })

  it('viser en delt tanke', async () => {
    const s = await render(
      <ThoughtsList items={[{ at: new Date().toISOString(), text: 'jeg tænkte på noget', delivered: true }]} />
    )
    expect(s.getByText('jeg tænkte på noget')).toBeTruthy()
  })

  // Uden de tilbageholdte kan man ikke se OM graenserne er sat rigtigt —
  // kun at der er stille.
  it('viser tilbageholdte tanker med grunden', async () => {
    const s = await render(
      <ThoughtsList
        items={[{ at: new Date().toISOString(), text: 'kl. tre om natten', delivered: false, reason: 'stille timer' }]}
      />
    )
    expect(s.getByText(/holdt tilbage: stille timer/)).toBeTruthy()
  })
})
