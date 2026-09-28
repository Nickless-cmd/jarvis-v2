import { fireEvent, render } from '@testing-library/react-native'
import { GenoptagelsesBanner } from './GenoptagelsesBanner'

/**
 * Banneret om arbejde der aldrig blev færdigt.
 *
 * Målt 28/9-2026: NUL forekomster af «recovery» i hele mobil-kildekoden, mens
 * andelen af kørsler der ikke når «completed» gik fra 2-8 % til 13-21 %. På
 * telefonen stoppede en kørsel i genoptagelse bare — med den tekst den nåede,
 * og ingen forklaring.
 */

const varsel = (o: Partial<{ reason: string; message: string; continuing: boolean }> = {}) => ({
  reason: 'pending-tool-intent',
  message: 'Jarvis havde stadig et vaerktoejskald klar.',
  continuing: true,
  ...o,
})

it('viser beskeden serveren sendte — ordret', async () => {
  const s = await render(<GenoptagelsesBanner varsel={varsel()} onLuk={() => {}} />)
  expect(s.getByTestId('genoptagelses-banner')).toBeTruthy()
  expect(s.getByText('Jarvis havde stadig et vaerktoejskald klar.')).toBeTruthy()
})

it('intet varsel — intet banner', async () => {
  const s = await render(<GenoptagelsesBanner varsel={null} onLuk={() => {}} />)
  expect(s.queryByTestId('genoptagelses-banner')).toBeNull()
})

it('et varsel uden besked tegnes ikke som et tomt banner', async () => {
  const s = await render(<GenoptagelsesBanner varsel={varsel({ message: '' })} onLuk={() => {}} />)
  expect(s.queryByTestId('genoptagelses-banner')).toBeNull()
})

/**
 * De to udgaver betyder noget FORSKELLIGT, og det er hele grunden til at
 * `continuing` bæres helt herud: «den er på vej igen» må ikke se ud som «den
 * blev opgivet». Et dødt run der ligner et levende er værre end intet banner.
 */
it('i gang og opgivet kan kendes fra hinanden', async () => {
  const igang = await render(<GenoptagelsesBanner varsel={varsel({ continuing: true })} onLuk={() => {}} />)
  expect(igang.getByTestId('genoptagelses-prik-igang')).toBeTruthy()
  expect(igang.queryByTestId('genoptagelses-prik-stille')).toBeNull()

  const opgivet = await render(<GenoptagelsesBanner varsel={varsel({ continuing: false })} onLuk={() => {}} />)
  expect(opgivet.getByTestId('genoptagelses-prik-stille')).toBeTruthy()
  expect(opgivet.queryByTestId('genoptagelses-prik-igang')).toBeNull()
})

it('kan lukkes', async () => {
  const luk = jest.fn()
  const s = await render(<GenoptagelsesBanner varsel={varsel()} onLuk={luk} />)
  fireEvent.press(s.getByLabelText('Luk'))
  expect(luk).toHaveBeenCalledTimes(1)
})

it('beskeden læses op — den er en advarsel, ikke pynt', async () => {
  const s = await render(<GenoptagelsesBanner varsel={varsel()} onLuk={() => {}} />)
  expect(s.getByLabelText('Jarvis havde stadig et vaerktoejskald klar.')).toBeTruthy()
})
