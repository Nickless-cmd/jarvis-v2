import { act, fireEvent, render, within } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import type { ChatMessage } from '../lib/types'
import type { ContentBlock } from '../lib/sseProtocol'

// `MessageAttachments` henter sin konfiguration gennem `useAuth`, som kaster
// uden for en AuthProvider. Samme mock som `MessageAttachments.test.tsx`.
jest.mock('../state/AuthContext', () => {
  const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }
  return {
    ...jest.requireActual('../state/AuthContext'),
    useAuth: () => ({ config }),
    useAuthOptional: () => ({ config }),
  }
})

const msg = (over: Partial<ChatMessage>): ChatMessage => ({
  id: 'm1',
  role: 'user',
  content: 'hej',
  created_at: '2026-09-12T12:00:00Z',
  ...over
})

/**
 * Et billede Jarvis laver MIDT i streamen. Det bærer sin egen `src` (en
 * data-URL), så det kan tegnes med det samme.
 *
 * Uden en gren for det faldt billedet ud af den LEVENDE visning og dukkede
 * først op ved genindlæsning — altså netop mens man venter på det. Bjørn
 * pegede på ChatGPT-appen som facit (27/9-2026): dér kommer billedet ind i
 * samtalen mens det laves.
 */
it('viser et live-billede mens svaret streames', async () => {
  const blocks: ContentBlock[] = [
    { type: 'text', text: 'Her er billedet.' },
    { type: 'image', src: 'data:image/png;base64,AAAA', alt: 'et æble' },
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('attachment-wrap')).toBeTruthy()
  expect(s.getByText('Her er billedet.')).toBeTruthy()
})

it('viser billedgenerering som venteflade uden opdigtet procent', async () => {
  const blocks: ContentBlock[] = [
    { type: 'tool_use', id: 'img-1', name: 'openrouter_image', input: { prompt: 'en kat' }, status: 'running' },
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('image-generation-progress')).toBeTruthy()
  expect(s.queryByText(/%/)).toBeNull()
})

it('fjerner ventefladen når Jarvis fortsætter med tekst', async () => {
  const s = await render(<MessageList messages={[]} blocks={[
    { type: 'tool_use', id: 'img-1', name: 'openrouter_image', input: {}, status: 'running' },
    { type: 'text', text: 'Her er billedet.' },
  ]} working />)
  expect(s.queryByTestId('image-generation-progress')).toBeNull()
})

/**
 * Arbejdslinjens token-tal skal FØRES hele vejen — fra `ChatScreen`s `usage`
 * gennem rækken og ned i linjen. Uden den kobling ville tallet blive regnet,
 * sendt og glemt: husets hyppigste fejl, en prop der aldrig når skærmen.
 *
 * Bjørn 30/9-2026: «lad os give den token country og min/sec tælleren fra
 * runde linjen». MUT: fjern `tokens: arbejdslinjeTokens` fra rækken → linjen
 * faar 0 og skjuler tallet → fanger.
 */
it('fører token-tallet ned i arbejdslinjen', async () => {
  const s = await render(
    <MessageList messages={[]} blocks={[]} working arbejdslinje="Kører npm test" arbejdslinjeTokens={45200} />
  )
  expect(s.getByTestId('arbejdslinje')).toBeTruthy()
  expect(s.getByText('45.2k tokens')).toBeTruthy()
  expect(s.getByText('Kører npm test')).toBeTruthy()
})

it('tegner INGEN arbejdslinje når streamen er slut', async () => {
  // Linjen forsvinder med streamen — den skal ikke stå tilbage som en tom
  // bjælke (Bjørn 29/9-2026). Tallet alene maa ikke holde den i live.
  const s = await render(
    <MessageList messages={[]} blocks={[]} working={false} arbejdslinje="Kører npm test" arbejdslinjeTokens={45200} />
  )
  expect(s.queryByTestId('arbejdslinje')).toBeNull()
})

it('viser turn header fra turen starter, før første blok kommer', async () => {
  const s = await render(<MessageList messages={[]} blocks={[]} working />)
  expect(s.getByTestId('turn-header')).toBeTruthy()
  expect(s.getByText('Working…')).toBeTruthy()
})

it('en ny tur starter åben, selv hvis forrige live tur blev lukket', async () => {
  const blocks: ContentBlock[] = [{ type: 'thinking', thinking: 'Undersøger.' }]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  await act(async () => { fireEvent.press(s.getByTestId('turn-header')) })
  expect(s.queryByTestId('thinking-summary')).toBeNull()
  await act(async () => { s.rerender(<MessageList messages={[]} blocks={[]} working={false} />) })
  await act(async () => { s.rerender(<MessageList messages={[]} blocks={blocks} working />) })
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
})

it('samler gemt arbejde bag én turn header og lader slutsvaret stå synligt', async () => {
  const s = await render(<MessageList messages={[msg({
    id: 'a1', role: 'assistant', content: 'Det er løst.',
    content_json: [
      { type: 'text', text: 'Jeg undersøger filen.' },
      { type: 'tool_use', id: 't1', name: 'read_file', input: { path: 'app.py' } },
      { type: 'text', text: 'Det er løst.' },
    ],
  })]} blocks={[]} />)
  expect(s.getByTestId('turn-header')).toBeTruthy()
  expect(s.getByText('Det er løst.')).toBeTruthy()
  expect(s.queryByText('Jeg undersøger filen.')).toBeNull()
  expect(s.queryByTestId('tool-group')).toBeNull()
  await fireEvent.press(s.getByTestId('turn-header'))
  expect(s.getByText('Jeg undersøger filen.')).toBeTruthy()
  expect(s.getByTestId('tool-group')).toBeTruthy()
})

it('åbner live arbejde ned under turn headeren og lader svaret stå synligt', async () => {
  const blocks: ContentBlock[] = [
    { type: 'thinking', thinking: 'Jeg lægger en plan.' },
    { type: 'text', text: 'Jeg finder filen.' },
    { type: 'tool_use', id: 't1', name: 'read_file', input: { path: 'app.py' }, status: 'done' },
    { type: 'text', text: 'Her er svaret.' },
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('turn-header').props.accessibilityState.expanded).toBe(true)
  expect(s.getByText('Her er svaret.')).toBeTruthy()
  expect(s.getByText('Jeg finder filen.')).toBeTruthy()
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  await act(async () => { fireEvent.press(s.getByTestId('turn-header')) })
  expect(s.queryByTestId('thinking-summary')).toBeNull()
  expect(s.getByText('Her er svaret.')).toBeTruthy()
})

it('folder arbejdet sammen ved skiftet fra stream til gemt slutsvar', async () => {
  const blocks: ContentBlock[] = [
    { type: 'thinking', thinking: 'Finder årsagen.' },
    { type: 'text', text: 'Rettet.' },
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('turn-header').props.accessibilityState.expanded).toBe(true)
  expect(s.getByTestId('thinking-summary')).toBeTruthy()

  const saved = msg({
    id: 'a1', role: 'assistant', content: 'Rettet.',
    content_json: [
      { type: 'thinking', text: 'Finder årsagen.', seconds: 2 },
      { type: 'text', text: 'Rettet.' },
    ],
  })
  await act(async () => { s.rerender(<MessageList messages={[saved]} blocks={[]} working={false} />) })
  expect(s.getByTestId('turn-header').props.accessibilityState.expanded).toBe(false)
  expect(s.queryByTestId('thinking-summary')).toBeNull()
  expect(s.getByText('Rettet.')).toBeTruthy()
})

it('en bruger-upload tegnes STRAKS — også før serveren har persisteret beskeden', async () => {
  // Den optimistiske besked bærer sine vedhæftninger som blokke. Uden dem stod
  // den tom, og billedet dukkede først op da serverens persisterede kopi
  // overtog den — altså ved run-slut (målt 27/9-2026, samme fejl i mobil og
  // desk).
  //
  // Persisteret form: kun en REFERENCE. Hentningen går derfor gennem
  // token-ruten (`AuthImage`), ikke direkte i `<Image>`.
  const s = await render(<MessageList messages={[msg({
    id: 'local-1',
    role: 'user',
    content: 'her ser du',
    content_json: [
      { type: 'image', attachment_id: '6a048f50', filename: 'skærm.png', mime_type: 'image/png' },
    ],
  })]} blocks={[]} />)

  expect(s.getByTestId('attachment-wrap')).toBeTruthy()
  expect(s.getByTestId('attachment-image-6a048f50')).toBeTruthy()
})

/**
 * Målt 12/9-2026: markøren faldt i default-grenen og blev tegnet som en
 * almindelig boble med HELE den serialiserede transcript som indhold (111k
 * tegn: `[Bjørn] …`, `[tool:tool] …`, «Use read_tool_result with result_id=…»).
 * Bjørn fandt den på sin telefon. Serveren trimmer nu indholdet; grenen her
 * sørger for at det også ser ud som det det er: intern bogholderi, ikke en
 * samtale-besked.
 */
it('kompakterings-markøren tegnes som én diskret linje — ikke en boble', async () => {
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'hej' }),
        msg({
          id: 'c1',
          role: 'compact_marker',
          content: 'Samtalen blev komprimeret — 111.507 tegn arkiveret'
        })
      ]}
      blocks={[]}
    />
  )

  expect(s.getByTestId('compact-marker')).toBeTruthy()
  expect(
    s.getByText('Samtalen blev komprimeret — 111.507 tegn arkiveret')
  ).toBeTruthy()
})

it('markøren får ingen handlingsrække — den er ikke et svar', async () => {
  // Uden grenen ville rollen lande i MessageBubble, og et «svar» får
  // kopiér/oplæs. En intern markør skal ikke kunne kopieres som om den var
  // Jarvis' ord.
  const s = await render(
    <MessageList
      messages={[
        msg({
          id: 'c1',
          role: 'compact_marker',
          content: 'Samtalen blev komprimeret — 111.507 tegn arkiveret'
        })
      ]}
      blocks={[]}
    />
  )

  expect(s.queryByLabelText('Kopiér')).toBeNull()
})

/**
 * Målt 12/9-2026: buildStreamingRows smeltede thinking-blokke sammen med
 * text-blokke i én boble (`textBuf += b.thinking`). Bjørn så rå CoT flyde
 * ind i svaret mens det streames. Nu skal thinking få sin egen række —
 * samme mønster som InlineToolGroup: én foldbar linje over svaret.
 */
it('thinking-blokke i stream får egen række — ikke smeltet ind i svaret', async () => {
  const blocks: ContentBlock[] = [
    { type: 'thinking', thinking: 'jeg overvejer om 2+2 er 4' },
    { type: 'text', text: 'Svaret er 4' }
  ]

  const s = await render(
    <MessageList
      messages={[msg({ id: 'u1', role: 'user', content: 'hvad er 2+2?' })]}
      blocks={blocks}
    />
  )

  // Thinking ligger under den åbne turn header, ikke inde i selve svaret.
  expect(s.getByTestId('turn-header')).toBeTruthy()
  expect(s.getByTestId('thinking-summary')).toBeTruthy()
  // Og teksten skal være en separat boble
  expect(s.getByText('Svaret er 4')).toBeTruthy()

  // LINJEN OVER KOMPONISTEN FINDES IKKE LAENGERE (Bjørn 21/9-2026). Den bar
  // taenke-fragmenterne nederst i traaden, og desk har ingen saadan linje.
  expect(s.queryByTestId('thinking-label')).toBeNull()
})

/**
 * Bjørn 21/9-2026: «vi har en linje over composer der viser tænke fragmenter og
 * forsvinder igen efter streamen.. tænke fragmenter bør vises I tænke linjen i
 * chatview og linjen over composer væk».
 *
 * Fragmentet står nu PÅ tænke-linjen selv — samme sted som desk viser det
 * («Tænker · 4 s · Lad mig se hvor værnet sidder…»). Mobilen har intet løbende
 * ur, så kun fragmentet følger med ordet.
 */
it('tænke-fragmentet står på trådens linje mens den tænker', async () => {
  const s = await render(
    <MessageList
      messages={[msg({ id: 'u1', role: 'user', content: 'hvad er 2+2?' })]}
      // Tanken er den SIDSTE blok → rækken er live og bærer fragmentet.
      blocks={[{ type: 'thinking', thinking: 'jeg overvejer om 2+2 er 4' }]}
    />
  )
  expect(
    within(s.getByTestId('thinking-summary')).getByText(/jeg overvejer om 2\+2 er 4/)
  ).toBeTruthy()
})

/**
 * Bjørn 12/9-2026: «det er kun den første tænkte der bliver i chatview, dem der
 * er under forsvinder efter streamen».
 *
 * Netop EFTER streamen: den levende visning bygger rækkerne af blokkene i
 * rækkefølge og har derfor altid vist dem alle. Den gemte visning hentede
 * tænkningen med `thinkingBlock` — som er `.find()` — og filtrerede resten væk
 * i `threadBlocks`. De to visninger var uenige om den samme tur.
 */
it('en gemt tur med flere tanker beholder dem alle, på deres plads', async () => {
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'kør noget' }),
        msg({
          id: 'a1',
          role: 'assistant',
          content: 'færdig',
          content_json: [
            { type: 'thinking', text: 'først overvejer jeg planen', seconds: 3 },
            { type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 't1' },
            { type: 'tool_result', tool_use_id: 't1', content: 'fil.txt', status: 'ok' },
            { type: 'thinking', text: 'så ser jeg på resultatet', seconds: 9 },
            { type: 'text', text: 'færdig' }
          ]
        } as Partial<ChatMessage>)
      ]}
      blocks={[]}
    />
  )
  await fireEvent.press(s.getByTestId('turn-header'))
  // BEGGE tanker hører til runden: den ene kom før kaldet, den anden efter det.
  // Desk lukker kun runden på et mellemsvar — ikke på en tanke
  // (`opdelArbejdsrunder`, raekkeModel.ts:71).
  expect(s.queryAllByText(/Tænkte/).length).toBe(0)
  await fireEvent.press(s.getByTestId('tool-group'))
  const taenkte = s.queryAllByText(/Tænkte/)
  expect(taenkte.length).toBe(2)
  // Og de baerer hver sin maalte tid — ikke den foerstes for dem begge.
  expect(s.queryAllByText(/Tænkte i 3s/).length).toBe(1)
  expect(s.queryAllByText(/Tænkte i 9s/).length).toBe(1)
})

/**
 * Prikkerne skal danne et 16×16-KVADRAT — ikke én lang stribe.
 *
 * Målt 27/9-2026 på mobilen: den flade `flexWrap`-liste wrappede ved
 * CONTAINERBREDDEN (64 prikker à 4 px) i stedet for ved 16, så kvadratet blev
 * 4 rækker à 16 px høj i en 256 px høj boks — en tynd vandret bjælke, og
 * opacity-gradienten pegede på prikker der lå helt andre steder. Desk slap,
 * fordi CSS grid med `repeat(16, 1fr)` TILLADER 16 kolonner. Rækkerne er nu
 * eksplicitte, så formen ikke afhænger af containerbredden.
 */
it('tegner prikkerne som 16 rækker — ikke én flad stribe', async () => {
  const s = await render(<MessageList messages={[]} blocks={[
    { type: 'tool_use', id: 'img-1', name: 'openrouter_image', input: {}, status: 'running' },
  ]} working />)
  expect(s.getAllByTestId('image-generation-raekke')).toHaveLength(16)
})

/**
 * Billedet i streamen bærer sin REFERENCE (27/9-2026).
 *
 * Er billedet for stort til en data-URL, sender serveren `attachment_id`
 * alene — attachment'en er allerede registreret, så adressen findes. Gav
 * streaming-rækken kun `src` videre, fik `tegnBillede` hverken src eller
 * adresse og tegnede INTET, præcis for de største billeder.
 *
 * Testet gennem den rigtige visning, ikke mod hjælperen: det er koblingen
 * fra blok til tegnet billede der kunne knække.
 */
it('et streamet billede UDEN src tegnes stadig — via sin attachment_id', async () => {
  const blocks: ContentBlock[] = [
    { type: 'image', attachment_id: 'att-9', filename: 'stor.png',
      mime_type: 'image/png', kilde: 'generated', tool_use_id: 'tu-1' } as ContentBlock,
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('attachment-open-att-9')).toBeTruthy()
})

it('et streamet billede MED data-URL tegnes direkte', async () => {
  const blocks: ContentBlock[] = [
    { type: 'image', src: 'data:image/png;base64,AAA', filename: 'k.png' } as ContentBlock,
  ]
  const s = await render(<MessageList messages={[]} blocks={blocks} working />)
  expect(s.getByTestId('attachment-open-k.png')).toBeTruthy()
})

// ── Trådens top-clearance (28/9-2026) ───────────────────────────────────
//
// Bjørn: «Der sker et eller andet ved header … men kun når streamen står
// stille.» Den øverste boble blev klippet fladt foroven.
//
// Årsagen var at clearance var et FAST tal (72 dp) målt fra skærmens top,
// mens header'en fylder `insets.top + BADGE_H + polstring` — ca. 74 dp på
// hans enhed. Tråden begyndte derfor 2 dp inde UNDER header'ens underkant.
// I hvile lander tråden på sin faste plads; mens der streames skubbes den op,
// og derfor sås fejlen kun i hvile.
//
// Vagten holder at tallet kommer UDEFRA. Sætter nogen det faste tal tilbage,
// fejler den her — og ikke først på hans telefon.
it('lægger headerens højde oveni top-clearance — den er ikke et fast tal', async () => {
  const s = await render(<MessageList messages={[msg({})]} blocks={[]} topInset={74} />)
  const liste = s.getByTestId('traad')
  const stil = liste.props.contentContainerStyle
  const flad = Array.isArray(stil) ? Object.assign({}, ...stil.filter(Boolean)) : stil
  // 12 (TOP_CLEARANCE) + 74 (header) = 86. Med det gamle faste tal ville
  // paddingBottom vaere 72 uanset hvad der blev sendt ind.
  expect(flad.paddingBottom).toBe(86)
})

it('uden topInset er der stadig luft — men kun den faste margin', async () => {
  const s = await render(<MessageList messages={[msg({})]} blocks={[]} />)
  const liste = s.getByTestId('traad')
  const stil = liste.props.contentContainerStyle
  const flad = Array.isArray(stil) ? Object.assign({}, ...stil.filter(Boolean)) : stil
  expect(flad.paddingBottom).toBe(12)
})

/** Alle testID'er og accessibility-labels i render-rækkefølge — samme hjælper
 *  som `MessageBubble.test.tsx` bruger til at måle hvad der står over hvad. */
const raekkefoelge = (node: unknown, ud: string[] = []): string[] => {
  if (Array.isArray(node)) {
    node.forEach((n) => raekkefoelge(n, ud))
    return ud
  }
  if (!node || typeof node !== 'object') return ud
  const n = node as { props?: Record<string, unknown>; children?: unknown }
  const p = n.props ?? {}
  if (typeof p.testID === 'string') ud.push(p.testID)
  if (typeof p.accessibilityLabel === 'string') ud.push(p.accessibilityLabel)
  raekkefoelge(n.children, ud)
  return ud
}

/**
 * Tænkelinjen skal ligge INDE i runde-linjens fold (Bjørn 29/9-2026:
 * «tænke-linjen ind i runde-linjen efter foldet.. det er det tætteste på
 * chatview I desk»).
 *
 * Første forsøg lagde den som en søskenderække UNDER linjen. Desk gør mere end
 * det: tænke-blokken er et ELEMENT i `rv-arbejdsdetaljer` — inde bag rundens
 * chevron (`RaekkeTranskript.tsx:324`), tegnet som sin egen foldbare række.
 * Tråden mister en linje pr. runde, og tanken er ét tryk væk.
 *
 * Derfor skal chevronen også frem når runden kun havde ÉT kald: uden den ville
 * tanken ikke kunne nås, og vi havde byttet en synlig linje for en skjult.
 */
it('tænkelinjen ligger INDE i runde-linjens fold — som i desk', async () => {
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'kør noget' }),
        msg({
          id: 'a1',
          role: 'assistant',
          content: 'færdig',
          content_json: [
            { type: 'thinking', text: 'først overvejer jeg planen', seconds: 3 },
            { type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 't1' },
            { type: 'tool_result', tool_use_id: 't1', content: 'fil.txt', status: 'ok' },
            { type: 'text', text: 'færdig' }
          ]
        } as Partial<ChatMessage>)
      ]}
      blocks={[]}
    />
  )
  await fireEvent.press(s.getByTestId('turn-header'))
  // Foldet: tænke-linjen er ikke sin egen række i tråden.
  expect(s.queryByTestId('thinking-summary')).toBeNull()
  // Chevronen står frem selvom runden kun havde ét kald.
  expect(s.getByTestId('tool-status-caret')).toBeTruthy()
  // Åbn runden: tanken står nu inde i dens detaljer.
  await fireEvent.press(s.getByTestId('tool-group'))
  const detaljer = within(s.getByTestId('tool-group-details'))
  expect(detaljer.getByTestId('thinking-summary')).toBeTruthy()
})

/**
 * Tur-hovedet skal stadig bære tænketiden — også nu hvor tanken bor INDE i
 * runde-linjens fold.
 *
 * `medTurHoveder` regnede sekunderne fra tænke-RÆKKER. Da tanken flyttede ind i
 * gruppen, faldt den ud af den optælling, og hovedet ville tie om sine sekunder
 * uden at nogen fejl blev rejst. Målt: mutation M5 (tællingen fjernet fra
 * gruppen) slap gennem HELE suiten — derfor denne test.
 */
it('tur-hovedet tæller tænketiden med, selvom tanken ligger i folden', async () => {
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'kør noget' }),
        msg({
          id: 'a1',
          role: 'assistant',
          content: 'færdig',
          content_json: [
            { type: 'thinking', text: 'først overvejer jeg planen', seconds: 3 },
            { type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 't1' },
            { type: 'tool_result', tool_use_id: 't1', content: 'fil.txt', status: 'ok' },
            { type: 'text', text: 'færdig' }
          ]
        } as Partial<ChatMessage>)
      ]}
      blocks={[]}
    />
  )
  // Hovedet står uden at folde ud — det er dér tallet skal læses.
  expect(s.getByText(/· 3s/)).toBeTruthy()
})

it('en tanke UDEN et kald efter sig bliver hvor den er', async () => {
  // Flytningen gælder kun når der faktisk ER en linje at ligge under. En tanke
  // der ender turen (eller går direkte over i svaret) har ingen værktøjs-linje.
  const s = await render(
    <MessageList
      messages={[msg({
        id: 'a2', role: 'assistant', content: 'færdig',
        content_json: [
          { type: 'thinking', text: 'jeg tænker mig om', seconds: 4 },
          { type: 'text', text: 'færdig' }
        ]
      } as Partial<ChatMessage>)]}
      blocks={[]}
    />
  )
  await fireEvent.press(s.getByTestId('turn-header'))
  const orden = raekkefoelge(s.toJSON())
  expect(orden.indexOf('thinking-summary')).toBeGreaterThan(-1)
  expect(orden.indexOf('tool-group')).toBe(-1)
})

/**
 * Bjørns faktiske blok-rækkefølge — målt 30/9-2026 i besked 153522:
 *
 *   thinking → text → tool_use → thinking → text → tool_use → thinking → text
 *
 * Den gamle `groupToolRounds` LUKKEDE runden i det øjeblik den så en tanke, så
 * tanke 2 og 3 blev skubbet ud som deres EGNE rækker — og stod derfor under den
 * foregående runde-linje. Det var netop dét Bjørn så: «Tænkte linjen står stadig
 * under tool result linjen».
 *
 * Desk lukker kun på et mellemsvar (`opdelArbejdsrunder`, raekkeModel.ts:71), så
 * tanken bliver liggende i den runde den hørte til.
 */
it('tanker efter et kald bliver i DEN runde — ikke skubbet ud som egne rækker', async () => {
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'kør noget' }),
        msg({
          id: 'a1',
          role: 'assistant',
          content: 'færdig',
          content_json: [
            { type: 'thinking', text: 'først overvejer jeg', seconds: 3 },
            { type: 'text', text: 'nu kalder jeg' },
            { type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 't1' },
            { type: 'tool_result', tool_use_id: 't1', content: 'a.txt', status: 'ok' },
            { type: 'thinking', text: 'så ser jeg på det', seconds: 4 },
            { type: 'text', text: 'så kalder jeg igen' },
            { type: 'tool_use', name: 'bash', input: { command: 'pwd' }, tool_use_id: 't2' },
            { type: 'tool_result', tool_use_id: 't2', content: '/tmp', status: 'ok' },
            { type: 'thinking', text: 'til sidst konkluderer jeg', seconds: 5 },
            { type: 'text', text: 'færdig' }
          ]
        } as Partial<ChatMessage>)
      ]}
      blocks={[]}
    />
  )
  await fireEvent.press(s.getByTestId('turn-header'))
  // Kun den FØRSTE tanke står selv: den kom før det første kald, og der var
  // ingen runde at lægge den i. Desk gør præcis det samme (enkeltræk).
  expect(s.queryAllByText(/Tænkte/).length).toBe(1)
  expect(s.queryAllByText(/Tænkte i 3s/).length).toBe(1)
  const grupper = s.getAllByTestId('tool-group')
  expect(grupper.length).toBe(2)
  // Ingen af de to tanker der HØRTE til en runde står løst i tråden.
  expect(s.queryAllByText(/Tænkte i 4s/).length).toBe(0)
  expect(s.queryAllByText(/Tænkte i 5s/).length).toBe(0)
  // Åbn begge runder. Listen er inverteret, så træets index 0 er den NYESTE
  // runde — derfor spørges der efter begge, ikke efter «den første».
  await fireEvent.press(s.getAllByTestId('tool-group')[0]!)
  await fireEvent.press(s.getAllByTestId('tool-group')[1]!)
  expect(s.queryAllByText(/Tænkte i 4s/).length).toBe(1)
  expect(s.queryAllByText(/Tænkte i 5s/).length).toBe(1)
})

it('tanken ligger EFTER sit eget kald i folden — ikke samlet øverst', async () => {
  // `foerKald` bærer tankens plads i runden. Uden den blev ALLE tanker tegnet
  // før alle kald, og en tanke der kom efter et kald stod foran det.
  const s = await render(
    <MessageList
      messages={[
        msg({ id: 'u1', role: 'user', content: 'kør noget' }),
        msg({
          id: 'a1',
          role: 'assistant',
          content: 'færdig',
          content_json: [
            { type: 'thinking', text: 'først overvejer jeg', seconds: 3 },
            { type: 'text', text: 'nu kalder jeg' },
            { type: 'tool_use', name: 'bash', input: { command: 'ls' }, tool_use_id: 't1' },
            { type: 'tool_result', tool_use_id: 't1', content: 'a.txt', status: 'ok' },
            { type: 'thinking', text: 'så ser jeg på det', seconds: 4 },
            { type: 'text', text: 'færdig' }
          ]
        } as Partial<ChatMessage>)
      ]}
      blocks={[]}
    />
  )
  await fireEvent.press(s.getByTestId('turn-header'))
  await fireEvent.press(s.getByTestId('tool-group'))
  const r = raekkefoelge(s.toJSON())
  const kald = r.indexOf('Kørte ls')
  // Vagt: et forkert label-navn ville give -1, og så målte testen ingenting.
  expect(kald).toBeGreaterThan(-1)
  expect(r.indexOf('thinking-summary')).toBeGreaterThan(-1)
  expect(kald).toBeLessThan(r.indexOf('thinking-summary'))
})
