import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * TO FLADER, ÉT UDVALG (14/10-2026).
 *
 * Kortet over composeren og toasten spurgte hver for sig om det samme: hvilke
 * agent-godkendelser venter — og hvilken haster. Kortet hentede
 * `/agents/approvals` og tog den ældste; toasten hentede hele feedet og tog
 * alle nye. Begge endte i `afgoerAgentApproval`, så AFGØRELSEN var fælles — men
 * UDVALGET var delt, og det er to steder at glemme noget den dag en tredje
 * flade kommer til.
 *
 * De to kilder læste i virkeligheden samme rækker: `feed()` kalder selv
 * `list_for_owner(status="pending")`. Forskellen var ruten, ikke dataene.
 *
 * ANDEN RUNDE, samme figur: feedet selv filtrerede sine tre sektioner inline
 * (`venter`/`svar`/`aktiv`) — fire steder i alt, når toastens filter tælles med.
 * Primitiven `kortISektion` ligger nu i API-laget, og `ventendeKort` og
 * `ventendeGodkendelser` er to navne på henholdsvis den brede og den snævre
 * udvælgelse ovenpå den.
 *
 * Kilden læses frem for at rende hele komponenterne op: det der skal pinnes er
 * ikke hvordan fladerne tegner, men at de ikke kan VÆLGE forskelligt. Det er
 * samme mønster som `agentGodkendelseRuter.test.ts` og
 * `godkendelseskortetTegnesEtSted.test.ts` — et navn i en import-linje er ikke
 * et kald, og et filter i en komponent er ikke et udvalgs-lag.
 */
const SRC = resolve(__dirname, '..')
const api = readFileSync(resolve(SRC, 'lib/agentContractApi.ts'), 'utf-8')
const toast = readFileSync(resolve(SRC, 'components/shell/NotifikationsToast.tsx'), 'utf-8')
const feed = readFileSync(resolve(SRC, 'components/shell/NotifikationsFeed.tsx'), 'utf-8')

describe('godkendelses-udvalget bor ét sted', () => {
  it('API-laget ejer udvalget — baade «hvilke» og «hvilken»', () => {
    expect(api).toContain('export function ventendeGodkendelser')
    expect(api).toContain('export function aeldsteVentende')
  })

  it('sektions-filteret er en primitiv, og de to udvalg bygger paa den', () => {
    expect(api).toContain('export function kortISektion')
    expect(api).toContain('export function ventendeKort')
    // Den snævre er en delmængde af den brede — ikke en kopi af filteret.
    expect(api).toContain('return ventendeKort(cards).filter((k) => k.approval?.approval_id)')
  })

  it('kortet over composeren læser den ældste fra feedet', () => {
    expect(api).toContain('aeldsteVentende(f?.cards || [])')
  })

  it('toasten læser det samme udvalg — ikke sit eget filter', () => {
    expect(toast).toContain('ventendeGodkendelser(f.cards)')
    // Regressionen: kom filteret tilbage her, kunne de to flader igen vælge
    // hver for sig, og fejlen fra 14/10 ville være usynlig indtil nogen
    // tilføjede en tredje flade.
    expect(toast).not.toContain("k.section === 'venter' && k.approval")
  })

  it('feedet viser alle sektioner i én tidslinje — udvalget bor stadig ét sted', () => {
    // 25/10-2026: feedet blev ét rent feed uden faner. Det filtrerer derfor
    // ikke længere paa sektion — men det maa heller ikke begynde at goere det
    // selv igen. Udvalget (hvad der ER en godkendelse) bor fortsat i API-laget.
    expect(feed).not.toContain("kortISektion(kortListe, 'venter')")
    expect(feed).not.toContain("kortISektion(kortListe, 'svar')")
    expect(feed).not.toContain("kortISektion(kortListe, 'aktiv')")
    // Kun FILTER-formen rammes: `k.section === 'svar'` bruges stadig legitimt
    // til at vælge CSS-klassen `er-svar` — det er tegning, ikke udvalg.
    expect(feed).not.toContain('.filter((k) => k.section ===')
    // Tidslinjen sorterer paa tid, nyeste først — det er den ene akse nu.
    expect(feed).toContain('elementer.sort((a, b) => b.tid - a.tid)')
  })

  it('kortet spørger ikke længere approvals-ruten selv om udvalget', () => {
    // Ruten bruges STADIG til selve afgørelsen (`…/decision`). Det er kun
    // OPSLAGET der er flyttet til feedet, så de to flader ikke læser hver sin.
    expect(api).not.toContain("'/agents/approvals?status=pending'")
  })
})
