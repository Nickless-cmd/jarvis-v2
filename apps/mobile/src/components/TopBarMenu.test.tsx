import { fireEvent, render } from '@testing-library/react-native'
import { TopBarMenu } from './TopBarMenu'

const base = () => ({
  aaben: true, onClose: jest.fn(), onSync: jest.fn(),
})

it('opdatér bor i menuen nu, ikke som sit eget ikon i bjaelken', async () => {
  const p = base()
  const screen = await render(<TopBarMenu {...p} />)
  fireEvent.press(screen.getByText('Opdatér'))
  expect(p.onSync).toHaveBeenCalledTimes(1)
})

it('menuen lukker sig selv naar man har valgt noget', async () => {
  // Ellers staar den aaben oven paa det man netop bad om at se.
  const p = base()
  const screen = await render(<TopBarMenu {...p} />)
  fireEvent.press(screen.getByText('Opdatér'))
  expect(p.onClose).toHaveBeenCalledTimes(1)
})

it('UDEN en ring er der intet komprimér-punkt', async () => {
  // Et punkt der ikke kan gøre noget er vaerre end et der ikke er der.
  const p = base()
  const screen = await render(<TopBarMenu {...p} />)
  expect(screen.queryByText('Komprimér kontekst')).toBeNull()
})

it('MED en ring kan man komprimere', async () => {
  // Ringen advarer om at komprimering naermer sig; det her er den eneste
  // handling den advarsel inviterer til.
  const onCompact = jest.fn()
  const p = base()
  const screen = await render(<TopBarMenu {...p} onCompact={onCompact} />)
  fireEvent.press(screen.getByText('Komprimér kontekst'))
  expect(onCompact).toHaveBeenCalledTimes(1)
})

it('tilbage-til-chat vises KUN i code-tilstand', async () => {
  const p = base()
  const screen = await render(<TopBarMenu {...p} onTilbageTilChat={jest.fn()} />)
  expect(screen.queryByText('Tilbage til chat')).toBeNull()
})

it('i code-tilstand fører tilbage-til-chat ud', async () => {
  const onTilbage = jest.fn()
  const p = base()
  const screen = await render(
    <TopBarMenu {...p} kodeTilstand onTilbageTilChat={onTilbage} />,
  )
  fireEvent.press(screen.getByText('Tilbage til chat'))
  expect(onTilbage).toHaveBeenCalledTimes(1)
})

it('er lukket naar aaben er falsk', async () => {
  const p = base()
  const screen = await render(<TopBarMenu {...p} aaben={false} />)
  expect(screen.queryByText('Opdatér')).toBeNull()
})
