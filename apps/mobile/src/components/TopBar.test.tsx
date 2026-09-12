import { fireEvent, render, within } from '@testing-library/react-native'
import { TopBar } from './TopBar'

const base = {
  mode: 'snak' as const,
  onModeChange: jest.fn(),
  onMenu: jest.fn(),
  onSync: jest.fn()
}

beforeEach(() => jest.clearAllMocks())

it('skifter tilstand via segmented control', async () => {
  const screen = await render(<TopBar {...base} />)
  await fireEvent.press(screen.getByLabelText('Arbejde'))
  expect(base.onModeChange).toHaveBeenCalledWith('arbejde')
})

it('menu og hoejre felt er selvstændige knapper', async () => {
  const screen = await render(<TopBar {...base} />)
  await fireEvent.press(screen.getByLabelText('Menu'))
  await fireEvent.press(screen.getByLabelText('Mere'))
  expect(base.onMenu).toHaveBeenCalledTimes(1)
  expect(base.onSync).toHaveBeenCalledTimes(1)
})

// ÉN render pr. test: to traeer i samme test overlever RNTL's oprydning og
// goer ALT efter den test blindt.
it('baerer INGEN prik paa Arbejde naar intet venter', async () => {
  const screen = await render(<TopBar {...base} />)
  expect(screen.queryByTestId('segment-badge-arbejde')).toBeNull()
})

it('baerer en prik paa Arbejde naar noget venter', async () => {
  const screen = await render(<TopBar {...base} pendingWork />)
  expect(screen.queryByTestId('segment-badge-arbejde')).not.toBeNull()
})

// --- code-fladen ---

it('uden code-tilstand hedder segmentet Snak', async () => {
  const screen = await render(<TopBar {...base} />)
  expect(screen.getByLabelText('Snak')).toBeTruthy()
})

it('i code-tilstand er segmentet VAEK — pladsen er titlens', async () => {
  // «Snak | Arbejde» hoerer til chat-fladen. I code er de to valg allerede
  // truffet, og kontakten er kun stoej paa appens mest vaerdifulde plads.
  const screen = await render(<TopBar {...base} kodeTilstand kodeTitel="Diagnose WLED" />)
  expect(screen.queryByLabelText('Snak')).toBeNull()
  expect(screen.queryByLabelText('Arbejde')).toBeNull()
  expect(screen.getByText('Diagnose WLED')).toBeTruthy()
})

it('i chat-tilstand er titlen VAEK — pladsen er segmentets', async () => {
  const screen = await render(<TopBar {...base} kodeTitel="Diagnose WLED" />)
  expect(screen.queryByTestId('code-titel')).toBeNull()
  expect(screen.getByLabelText('Snak')).toBeTruthy()
})

it('code-titlen baerer repo og vaert naar git svarede', async () => {
  // Den ene oplysning telefonen ikke selv kan regne ud: API'et koerer et
  // andet sted end appen.
  const git = { branch: 'main', dirty: 73, added: 2925, removed: 1407, isGit: true as const,
                repo: 'jarvis-v2', host: 'CheifOne' }
  const screen = await render(<TopBar {...base} kodeTilstand kodeTitel="Diagnose WLED" git={git} />)
  expect(screen.getByText('jarvis-v2')).toBeTruthy()
  expect(screen.getByText('CheifOne')).toBeTruthy()
})

it('UDEN git-svar tegnes kontekstlinjen slet ikke', async () => {
  // En linje med tomme navne og en groen prik ville paastaa en forbindelse
  // der ikke er efterproevet.
  const screen = await render(<TopBar {...base} kodeTilstand kodeTitel="Diagnose WLED" />)
  expect(screen.queryByText('repo')).toBeNull()
  expect(screen.queryByText('vært')).toBeNull()
})

it('venstre felt er ALTID en pil til menuen — ogsaa i code', async () => {
  // Foer skiftede ikonet mellem hamburger og pil, og de to foerte to
  // forskellige steder hen. Samme plads maa ikke goere to ting afhaengigt af
  // en tilstand man ikke kan se paa knappen. Vejen ud af code bor i menuen.
  const screen = await render(<TopBar {...base} kodeTilstand />)
  await fireEvent.press(screen.getByLabelText('Menu'))
  expect(base.onMenu).toHaveBeenCalledTimes(1)
})

it('hoejre felt aabner tre-prik menuen naar den findes — ikke sync direkte', async () => {
  // Opdatér bor INDE i menuen nu. Ramte trykket stadig onSync, ville menuen
  // aldrig kunne aabnes.
  const onMereMenu = jest.fn()
  const screen = await render(<TopBar {...base} onMereMenu={onMereMenu} />)
  await fireEvent.press(screen.getByLabelText('Mere'))
  expect(onMereMenu).toHaveBeenCalledTimes(1)
  expect(base.onSync).not.toHaveBeenCalled()
})

it('ringen staar i SAMME felt som prikkerne', async () => {
  const screen = await render(
    <TopBar {...base} kontekst={{ tokens: 65_000, compactAt: 130_000, compacting: false }} />,
  )
  // Ringen skal findes UNDER feltet, ikke ved siden af det: Bjoern bad om
  // «en context ring lige foer de tre prikker i SAMME badge».
  const felt = screen.getByTestId('topbar-mere')
  expect(within(felt).getByTestId('context-ring')).toBeTruthy()
})

it('uden kontekst er der ingen ring', async () => {
  const screen = await render(<TopBar {...base} />)
  expect(screen.queryByTestId('context-ring')).toBeNull()
})

it('feltet omkring ring og prikker har INGEN fast bredde og RIGELIG luft', async () => {
  // Bjoern: feltet skal «udvides saa den faktisk daekker» ringen og prikkerne.
  // Bredden skal komme fra indholdet, og polstringen skal vaere stor nok til
  // at ringen ikke roerer kanten - ved 9 dp gjorde den.
  const { StyleSheet } = require('react-native')
  const screen = await render(
    <TopBar {...base} kontekst={{ tokens: 65_000, compactAt: 130_000, compacting: false }} />,
  )
  const flad = StyleSheet.flatten(screen.getByTestId('topbar-mere').props.style)
  expect(flad.width).toBeUndefined()
  // ... og der SKAL vaere luft, ellers roerer indholdet kanten.
  expect(flad.paddingHorizontal).toBeGreaterThanOrEqual(12)
  expect(flad.gap).toBeGreaterThanOrEqual(6)
})

it('uden ring er feltet stadig en rund knap', async () => {
  const { StyleSheet } = require('react-native')
  const screen = await render(<TopBar {...base} />)
  const flad = StyleSheet.flatten(screen.getByTestId('topbar-mere').props.style)
  expect(flad.width).toBe(flad.height)
})
