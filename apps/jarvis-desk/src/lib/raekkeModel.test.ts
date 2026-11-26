import { describe, it, expect } from 'vitest'
import { opdel, opdelArbejdsrunder, turFortalt, turHoved } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'
import { erBilledVaerktoej } from '../components/rich/ImageGeneration'

/**
 * Opdelingen er hele rækkevisningen.
 *
 * Fejler den, ser man enten et svar der forsvinder ind bag en foldet gruppe,
 * eller en narrationslinje der bliver stående som om den var svaret. Begge
 * dele er tavse: der kastes intet, og alle blokke er der stadig.
 */

const tekst = (t: string): ContentBlock => ({ type: 'text', text: t })
const kald = (navn: string): ContentBlock => ({ type: 'tool_use', id: navn, name: navn, input: {} })
const tanke = (s: number): ContentBlock => ({ type: 'thinking', thinking: '…', seconds: s })

describe('opdel', () => {
  it('viser løbende tekst efter et værktøj som mellemsyntese indtil slutsvaret er bekræftet', () => {
    const blocks = [kald('bash'), tekst('Næste runde undersøges nu.')]
    expect(opdel(blocks, true).arbejde.map((e) => e.slags)).toEqual(['blok', 'mellemsvar'])
    expect(opdel(blocks, true).svar).toEqual([])
    expect(opdel(blocks, false).svar).toEqual([tekst('Næste runde undersøges nu.')])
  })

  it('lægger tekst MELLEM to kald i arbejdet, ikke i svaret', () => {
    const { arbejde, svar } = opdel([
      kald('bash'),
      tekst('Den svarer 200. Nu henter jeg kataloget.'),
      kald('bash'),
      tekst('Færdig.'),
    ])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'mellemsvar', 'blok'])
    expect(arbejde[1]).toEqual({ slags: 'mellemsvar', tekst: 'Den svarer 200. Nu henter jeg kataloget.' })
    expect(svar).toEqual([tekst('Færdig.')])
  })

  it('bevarer rækkefølgen — en syntese skal stå mellem DE kald den stod imellem', () => {
    const { arbejde } = opdel([
      kald('search'), tekst('A'), kald('fetch'), tekst('B'), kald('read'),
    ])
    expect(arbejde.map((e) => {
      if (e.slags === 'mellemsvar') return e.tekst
      if (e.slags === 'spor') return 'spor'
      return (e.blok as { name: string }).name
    }))
      .toEqual(['search', 'A', 'fetch', 'B', 'read'])
  })

  it('en besked UDEN kald er rent svar — intet tomt arbejdsområde', () => {
    // Faelden: havde reglen vaeret «sidste tekstblok er svaret», ville det
    // foerste afsnit her lande i en gruppe, og der ville staa
    // «Thought for 0s · 0 tool calls» over en almindelig replik.
    const { arbejde, svar, kald: n } = opdel([tekst('Første afsnit.'), tekst('Andet afsnit.')])
    expect(arbejde).toEqual([])
    expect(svar).toHaveLength(2)
    expect(n).toBe(0)
  })

  it('lader alt efter det sidste kald være svar — også flere afsnit', () => {
    const { svar } = opdel([kald('bash'), tekst('Et.'), tekst('To.')])
    expect(svar.map((b) => (b as { text: string }).text)).toEqual(['Et.', 'To.'])
  })

  it('springer tomme tekstblokke over — de opstår før første delta', () => {
    const { arbejde } = opdel([kald('bash'), tekst('   '), kald('bash')])
    expect(arbejde.filter((e) => e.slags === 'mellemsvar')).toEqual([])
  })

  it('samler sammenhængende progress-blokke til ÉT spor', () => {
    // Bjoern 23/9-2026: ni «Koerer kommando: python» under hinanden er stoej.
    // Én linje der opdaterer sig, med hele forloebet i kroppen.
    const p = (m: string): ContentBlock => ({
      type: 'progress', tool_use_id: 't', parent_tool_use_id: null, message: m, status: 'running',
    })
    const { arbejde } = opdel([kald('bash'), p('et'), p('to'), p('tre'), tekst('svar')])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'spor'])
    const spor = arbejde[1]
    if (spor?.slags !== 'spor') throw new Error('forventede et spor')
    expect(spor.trin.map((t) => t.message)).toEqual(['et', 'to', 'tre'])
  })

  it('bryder sporet når der kommer noget imellem', () => {
    const p = (m: string): ContentBlock => ({
      type: 'progress', tool_use_id: 't', parent_tool_use_id: null, message: m, status: 'running',
    })
    const { arbejde } = opdel([kald('a'), p('et'), kald('b'), p('to'), tekst('svar')])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'spor', 'blok', 'spor'])
  })

  it('tæller kald og lægger tænketiden sammen', () => {
    const o = opdel([tanke(12), kald('a'), tanke(9), kald('b'), tekst('svar')])
    expect(o.kald).toBe(2)
    expect(o.sekunder).toBe(21)
  })

  it('holder en afsluttende tanke i ARBEJDET — ikke i svaret', () => {
    // Skillelinjen gaelder TEKST. En tanke er arbejde uanset hvor den staar:
    // lagde vi den i svaret, ville raa tankestroem blive tegnet som replik,
    // med tænke-raekkens indhold spredt ud som brodtekst.
    const { arbejde, svar } = opdel([kald('a'), tanke(3)])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'blok'])
    expect(svar).toEqual([])
  })

  it('løfter et billede UD af arbejdet — det er en leverance, ikke arbejde', () => {
    // Målt 27/9-2026 i Bjørns tråd: et genereret billede lå MIDT i beskeden
    // (efter sit eget værktøj, før de senere kald) og faldt derfor i arbejdet —
    // hvor rækkevisningen folder det væk bag turens hoved. Det samme billede
    // stod frit i mobilen. En leverance skal ses; den hører i svaret.
    const billede: ContentBlock = { type: 'image', filename: 'x.png', attachment_id: 'a1' }
    const { arbejde, svar } = opdel([
      kald('openrouter_image'), billede, kald('analyze_image'), tekst('Færdig.'),
    ])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'blok'])
    expect(svar).toEqual([billede, tekst('Færdig.')])
  })

  it('gør det samme for en udgivet fil', () => {
    const fil: ContentBlock = { type: 'file', filename: 'rapport.csv', url: '/files/rapport.csv' }
    const { arbejde, svar } = opdel([kald('publish_file'), fil, kald('bash'), tekst('Klar.')])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'blok'])
    expect(svar).toEqual([fil, tekst('Klar.')])
  })

  it('beholder slutteksten som svar naar et kald kommer EFTER den', () => {
    // MÅLT 21/11-2026 (Bjørn: «du kalder en extra runde efter din slut besked
    // og det forvirre hovede.. og giver de tomme skærme efter foldet og dump»).
    //
    // Skillelinjen laa efter det SIDSTE værktøjskald — ogsaa et kald der kom
    // efter svaret var skrevet. Saa faldt slutteksten ned i arbejdet, som
    // ligger inde i folden: tom skærm, og teksten «dumpet» bagefter.
    // Siden 26/11-2026 bærer testen den fase serveren FAKTISK sender på en
    // sluttekst: `final_answer` via `text_phase_update` i
    // `_flush_pending_text(final=True)`. Grænsen læses af den, ikke af hvor
    // teksten tilfældigvis ligger i forhold til kaldene.
    const sluttekst: ContentBlock = {
      type: 'text', text: 'Slutteksten som brugeren skal laese.', phase: 'final_answer',
    }
    const blocks = [
      kald('bash'),
      sluttekst,
      kald('remember_this'),
    ]
    const { arbejde, svar } = opdel(blocks, false, true)
    expect(svar).toEqual([sluttekst])
    expect(arbejde.map((e) => e.slags)).toEqual(['blok', 'blok'])
  })

  it('flytter ikke graensen naar svaret IKKE er begyndt', () => {
    // Uden `svarLaast` er et kald efter teksten stadig et led i arbejdet.
    const blocks = [kald('bash'), tekst('Næste runde undersøges nu.'), kald('bash')]
    expect(opdel(blocks, false).svar).toEqual([])
  })

  it('lader IKKE en sen syntese skubbe det allerede viste svar ind i folden', () => {
    // MÅLT 26/11-2026 (Bjørn: «blinket sker fordi hoved først folder ved din
    // sidste syntese og så merger vi syntese og slut besked»).
    //
    // `svarLaast` går BAGLÆNS fra sidste kald og stopper ved første grænse
    // med tekst efter sig. Men den kører forfra ved HVER render, så grænsen
    // har ingen hukommelse: lander der en syntese efter svaret, finder
    // gennemløbet nu tekst efter det NYE sidste kald — og grænsen rykker
    // FREM. Slutbeskeden bliver dermed arbejde, mens brugeren læser den.
    //
    // Sekvensen er Bjørns egen: svar A, kald, svar B, kald, svar C.
    // A var en leverance da den blev skrevet, og serveren stemplede den
    // `final_answer`. B og C kommer bagefter uden eget stempel — men de
    // ligger EFTER grænsen, og efter foldet streamer teksten frit.
    const a: ContentBlock = {
      type: 'text', text: 'Fund 1: forbindelsen blev afvist af pihole.', phase: 'final_answer',
    }
    const b = tekst('Fund 2: reglen stod i den forkerte tabel.')
    const c = tekst('Det bekræfter konklusionen.')
    const blocks = [a, kald('bash'), b, kald('bash'), c]

    const { arbejde, svar } = opdel(blocks, false, true)

    // Det viste svar bliver stående — det er hele pointen.
    expect(svar).toContain(a)
    expect(svar).toContain(b)
    // Den sene syntese er stadig svar; den må ikke blive det ENESTE svar.
    expect(svar).toContain(c)
    // Kaldene er arbejde uanset hvor grænsen ligger.
    expect(arbejde.every((e) => e.slags === 'blok')).toBe(true)
  })

  it('holder graensen laast naar den foerst har tekst efter sig', () => {
    // Samme sekvens som ovenfor, men maalt som et SPOERGSMAAL: flytter
    // graensen sig naar listen vokser? Det er den egenskab der fejler —
    // ikke om teksten tilfaeldigtvis lander rigtigt i én bestemt laengde.
    const a: ContentBlock = { type: 'text', text: 'Fund 1.', phase: 'final_answer' }
    const b = tekst('Fund 2.')
    const foer = [a, kald('bash'), b]
    const efter = [...foer, kald('bash'), tekst('Det bekræfter konklusionen.')]

    const svarFoer = opdel(foer, false, true).svar
    const svarEfter = opdel(efter, false, true).svar

    // Alt der var svar foer, skal stadig vaere svar efter. En laast graense
    // er monoton: den maa gaa baglaens, aldrig frem.
    for (const blok of svarFoer) expect(svarEfter).toContain(blok)
  })

  it('bevarer indledende narration som arbejde — fasen afgoer, ikke placeringen', () => {
    // Bjørn 26/11-2026: «Bevar den eksisterende klassificering før første
    // foldning. Tekst før første værktøjskald skal ikke automatisk betragtes
    // som leverance eller narration alene på baggrund af dens placering.»
    //
    // Her er narrationslinjen ikke stemplet, og svaret er. Grænsen lægges ved
    // det sidste kald FØR den stemplede blok — den trækker ikke den
    // uafklarede tekst med ud.
    const narration = tekst('Lad mig se på det.')
    const svarblok: ContentBlock = {
      type: 'text', text: 'Her er resultatet.', phase: 'final_answer',
    }
    const blocks = [narration, kald('read_file'), svarblok]

    const { arbejde, svar } = opdel(blocks, false, true)

    expect(svar).toEqual([svarblok])
    expect(arbejde.some((e) => e.slags === 'mellemsvar')).toBe(true)
  })

  it('gaetter ikke naar serveren ikke har stemplet nogen final_answer', () => {
    // Bjørn 26/11-2026: «Vi accepterer midlertidigt begrænsningen i serverens
    // eksisterende klassificering. Den semantiske kilde løses separat og må
    // ikke blokere præsentationsopgaven.»
    //
    // Uden et stempel er der ingen kilde. Klienten lader grænsen stå ved det
    // sidste kald frem for at opfinde en heuristik — også selv om det betyder
    // at en leverance kan blive klassificeret som arbejde. Det er den kendte
    // begrænsning, ikke en ny fejl.
    const blocks = [kald('bash'), tekst('Et svar uden fase.'), kald('remember_this')]

    expect(opdel(blocks, false, true).svar).toEqual([])
  })

  it('loefter IKKE en blok serveren selv har stemplet commentary', () => {
    // MÅLT 26/11-2026: låsen hev en tidlig syntese ud af folden, fordi den
    // kun så på om der var tekst efter grænsen. Men blokken var allerede
    // mærket `commentary` af serveren — den er en mellemregning, og klienten
    // må ikke gætte imod en fase den har fået. Kun blokke UDEN fase er
    // uafklarede og må løftes.
    const mellemregning: ContentBlock = {
      type: 'text', text: 'God idé — jeg undersøger det.', phase: 'commentary',
    }
    const blocks = [mellemregning, kald('read_file'), tekst('Her er resultatet.')]

    const { arbejde, svar } = opdel(blocks, false, true)

    expect(svar).toEqual([tekst('Her er resultatet.')])
    expect(arbejde.some((e) => e.slags === 'mellemsvar')).toBe(true)
  })

  it('er tom for en tom besked', () => {
    expect(opdel([])).toEqual({ arbejde: [], svar: [], kald: 0, sekunder: 0 })
  })
})

describe('turHoved', () => {
  it('skriver sekunder, ikke «a while» (Bjørn 22/9-2026)', () => {
    expect(turHoved(9, 90)).toBe('Thought for 90s · 9 tool calls')
  })
  it('bøjer ental', () => {
    expect(turHoved(1, 7)).toBe('Thought for 7s · 1 tool call')
  })
  it('siger ikke «0s» når der ikke blev tænkt', () => {
    expect(turHoved(2, 0)).toBe('Worked · 2 tool calls')
  })
  it('lader «0 tool calls» være — en tur der kun tænkte har ikke et kald at tælle', () => {
    expect(turHoved(0, 12)).toBe('Thought for 12s')
  })
})

describe('turFortalt', () => {
  it('siger Arbejdet og turen — ikke en opremsning af værktøjer', () => {
    // Bjørn 15/11-2026: «denne generiske dele af hoved når det er foldet skal
    // væk, skiftet til Arbejdet eller Worked efterfulgt af turens tid».
    const f = [...Array(6).fill('fil'), ...Array(3).fill('terminal')]
    expect(turFortalt(f, 9, 90)).toBe('Arbejdet · 90s')
  })
  it('dropper tiden når der ikke blev tænkt', () => {
    expect(turFortalt(['diff', 'diff'], 2, 0)).toBe('Arbejdet')
  })
  it('er den samme sætning uanset hvilke familier turen brugte', () => {
    // Formen må ikke afhænge af værktøjsnavne: en ny familie skal ikke kunne
    // ændre hvad hovedet hedder.
    const a = turFortalt(['fil'], 1, 7)
    const b = turFortalt(['terminal', 'web', 'diff'], 3, 7)
    expect(a).toBe(b)
    expect(a).toBe('Arbejdet · 7s')
  })
  it('falder tilbage til Arbejdet når der slet ikke blev brugt værktøjer', () => {
    expect(turFortalt([], 0, 12)).toBe('Arbejdet · 12s')
  })
})

describe('opdelArbejdsrunder', () => {
  it('bevarer synteser mellem foldbare værktøjsrunder', () => {
    const { arbejde } = opdel([
      tekst('Jeg finder filen.'), kald('read_file'), kald('grep'),
      tekst('Jeg retter fejlen.'), kald('edit_file'),
      tekst('Rettet.'),
    ])
    const sektioner = opdelArbejdsrunder(arbejde)
    expect(sektioner.map((s) => s.slags)).toEqual(['syntese', 'runde', 'syntese', 'runde'])
    expect(sektioner[0]).toEqual({ slags: 'syntese', tekst: 'Jeg finder filen.' })
    expect(sektioner[1]).toMatchObject({ slags: 'runde' })
    expect(sektioner[2]).toEqual({ slags: 'syntese', tekst: 'Jeg retter fejlen.' })
    expect(sektioner[3]).toMatchObject({ slags: 'runde' })
    expect(sektioner.filter((s) => s.slags === 'runde').map((s) => s.elementer.length)).toEqual([2, 1])
  })

  it('bruger en neutral fallback når Jarvis ikke selv skrev en arbejdslinje', () => {
    const { arbejde } = opdel([kald('read_file'), kald('bash'), tekst('Færdig.')])
    expect(opdelArbejdsrunder(arbejde)).toEqual([{
      slags: 'runde',
      elementer: arbejde,
    }])
  })

  it('bevarer tanke og progress i den værktøjsrunde de tilhører', () => {
    const p: ContentBlock = { type: 'progress', tool_use_id: 'read_file', parent_tool_use_id: null, message: 'Læser', status: 'running' }
    const { arbejde } = opdel([tekst('Jeg læser.'), tanke(2), kald('read_file'), p, tekst('Svar.')])
    const runde = opdelArbejdsrunder(arbejde)[1]
    expect(runde?.slags).toBe('runde')
    if (runde?.slags !== 'runde') throw new Error('forventede en arbejdsrunde')
    expect(runde.elementer.map((e) => e.slags)).toEqual(['blok', 'blok', 'spor'])
  })

  it('laver ikke en tom arbejdsrunde af en tanke uden værktøjskald', () => {
    const { arbejde } = opdel([tanke(3), tekst('Jeg læser filen.'), kald('read_file'), tekst('Svar.')])
    expect(opdelArbejdsrunder(arbejde).map((s) => s.slags)).toEqual(['enkelt', 'syntese', 'runde'])
  })
})

describe('forløbet Bjørn bad om (27/9-2026)', () => {
  // «generér billede (animationen) → vis billede → streamen fortsætter →
  //  streamen slutter (billedet står i det foldede hoveds svar, som nu)»
  //
  // Animationen tegnes af `RaekkeTranskript` mellem arbejdet og svaret, og
  // kun mens billedværktøjets `tool_use` har status `running`. Svaret tegnes
  // uanset om turens hoved er foldet ud. Så i samme øjeblik blokken lander,
  // står billedet dér hvor animationen lige stod.
  //
  // Det er IKKE fordi hovedet er foldet ud at billedet manglede — `erLeverance`
  // har løftet billeder ud af arbejdet siden c1428a7da. Der fandtes bare ingen
  // billedblok i streamen at løfte.
  const kald = (status: 'running' | 'done'): ContentBlock =>
    ({ type: 'tool_use', id: 'tu-1', name: 'openrouter_image', input: {}, status } as ContentBlock)
  const billede: ContentBlock =
    { type: 'image', src: 'data:image/png;base64,AAA', tool_use_id: 'tu-1' } as ContentBlock

  it('1) mens værktøjet kører: intet billede endnu, kaldet er arbejde', () => {
    const { arbejde, svar } = opdel([kald('running')])
    expect(svar).toHaveLength(0)
    expect(arbejde).toHaveLength(1)
  })

  it('2) blokken lander: billedet står i SVARET, ikke bag turens hoved', () => {
    const { arbejde, svar } = opdel([kald('done'), billede])
    expect(svar).toEqual([billede])
    expect(arbejde.some((e) => e.slags === 'blok' && e.blok.type === 'image')).toBe(false)
  })

  it('3) streamen fortsætter: senere kald skubber ikke billedet tilbage i arbejdet', () => {
    // Skillelinjen er det SIDSTE tool_use. Uden `erLeverance` ville billedet
    // her falde i arbejdet og forsvinde bag hovedet — præcis fejlen fra 27/9.
    const senere = { type: 'tool_use', id: 'tu-2', name: 'remember_this', input: {}, status: 'done' } as ContentBlock
    const { svar } = opdel([kald('done'), billede, senere])
    expect(svar).toEqual([billede])
  })

  it('4) turen slutter: billedet står sammen med den endelige tekst', () => {
    const tekst = { type: 'text', text: 'Her er billedet.' } as ContentBlock
    const senere = { type: 'tool_use', id: 'tu-2', name: 'remember_this', input: {}, status: 'done' } as ContentBlock
    const { svar } = opdel([kald('done'), billede, senere, tekst])
    expect(svar).toEqual([billede, tekst])
  })

  it('alle tre billedværktøjer udløser animationen — ikke kun genereringen', () => {
    for (const n of ['openrouter_image', 'openrouter_image_edit', 'pollinations_image']) {
      expect(erBilledVaerktoej(n)).toBe(true)
    }
    expect(erBilledVaerktoej('remember_this')).toBe(false)
  })
})
