import { render } from '@testing-library/react-native'
import { Arbejdslinje } from './Arbejdslinje'

/**
 * `render` er ASYNKRON i dette bibliotek (samme mønster som
 * `InlineToolGroup.test.tsx` og `MessageList.test.tsx`), så hver test venter.
 */
describe('Arbejdslinje', () => {
  it('viser sætningen med puls og prikker', async () => {
    const s = await render(<Arbejdslinje tekst="Læser useChatScroll.ts" />)
    expect(s.getByTestId('arbejdslinje')).toBeTruthy()
    expect(s.getByText('Læser useChatScroll.ts')).toBeTruthy()
    expect(s.getByTestId('puls-ikon')).toBeTruthy()
    expect(s.getByTestId('prikker', { includeHiddenElements: true })).toBeTruthy()
  })

  it('tegner INTET når der ikke er noget at vise', async () => {
    // Hele pointen med «forsvinder når streamen slutter»: ingen tom bjælke.
    // MUT: fjern null-guarden → en bar linje står tilbage efter svaret → fanger.
    const s = await render(<Arbejdslinje tekst={null} />)
    expect(s.queryByTestId('arbejdslinje')).toBeNull()
    expect(s.queryByTestId('puls-ikon')).toBeNull()
  })

  it('bærer teksten som tilgængeligheds-label — ikke kun som pixels', async () => {
    const s = await render(<Arbejdslinje tekst="Kører npm test" />)
    expect(s.getByLabelText('Kører npm test')).toBeTruthy()
  })
})
