/**
 * Shimmeren på runde-linjerne — KOBLINGEN, ikke komponenten.
 *
 * Målt 4/10-2026: shimmeren forsvandt HELT i 0.2.171. Årsagen sad ikke i
 * `InlineToolGroup` (den var testet og grøn), men i kæden før den: flaget
 * `sidsteRunde` blev sat i `buildStreamingRows`, som kun bygger
 * `live-tool`-rækker — `tool-group` opstår først i `groupToolRounds`. Flaget
 * ramte derfor en rækketype der ikke findes i arrayet, `sidste` var altid
 * `undefined`, og `visShimmer` blev aldrig sand.
 *
 * Netop derfor testes her GENNEM `MessageList`. En isoleret komponent-test
 * der sender `sidste={true}` direkte ville være grøn hele tiden — den måler
 * komponenten, ikke om nogen nogensinde sætter flaget.
 */
import { render } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import type { ContentBlock } from '../lib/sseProtocol'

jest.mock('../state/AuthContext', () => {
  const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }
  return {
    ...jest.requireActual('../state/AuthContext'),
    useAuth: () => ({ config }),
    useAuthOptional: () => ({ config }),
  }
})

/** Ét værktøjskald — `status` afgør om runden stadig arbejder. */
const værktøj = (status: string): ContentBlock =>
  ({ type: 'tool_use', id: 't1', name: 'read_file', input: { path: 'a.py' }, status } as ContentBlock)

/**
 * Runde-linjens shimmer — målt på `linje-titel`, den FÆRDIGE gren i
 * `LabelSkift`. Er den der, kører shimmeren ikke.
 *
 * `glidende-tekst` duer IKKE som probe: `TurnHeader`, `ThinkingSummary`,
 * `SkillLinje` og `LabelSkift` deler alle samme testID, så en tælling ramte
 * turn-headerens shimmer i stedet for runde-linjens (målt 4/10-2026).
 */
const shimmerer = (s: Awaited<ReturnType<typeof render>>): boolean =>
  s.queryAllByTestId('linje-titel').length === 0

it('shimmeren kører mens den sidste runde arbejder', async () => {
  const s = await render(<MessageList messages={[]} blocks={[værktøj('running')]} working />)
  expect(shimmerer(s)).toBe(true)
})

it('shimmeren lever videre i hullet — værktøjet er færdigt, slutsvaret ikke begyndt', async () => {
  // Det er hele rettelsen: `running` alene slukkede i samme sekund sidste kald
  // fik sit resultat, og præcis dér tænker modellen på den næste.
  const s = await render(<MessageList messages={[]} blocks={[værktøj('done')]} working />)
  expect(shimmerer(s)).toBe(true)
})

it('shimmeren slukker når serveren bekræfter at slutsvaret er begyndt', async () => {
  const s = await render(
    <MessageList messages={[]} blocks={[værktøj('done')]} working finalAnswerStarted />,
  )
  expect(shimmerer(s)).toBe(false)
})
