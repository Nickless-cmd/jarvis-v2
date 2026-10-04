/**
 * Hvornår bærer Jarvis' browser Bjørns token? (4/10-2026)
 *
 * Reglen er det ene sted der afgør om hans bearer-token forlader maskinen, så
 * den testes direkte frem for gennem en kørende Electron-session. Lå den inde
 * i `onBeforeSendHeaders`, kunne den kun måles ved at starte en rigtig
 * session — og så ville netop det sted være det ene uden test.
 */
import { describe, it, expect, vi } from 'vitest'

vi.mock('electron', () => ({
  WebContentsView: class {},
  BrowserWindow: class {},
  shell: { openExternal: vi.fn() },
  session: { defaultSession: { webRequest: { onBeforeSendHeaders: vi.fn() } } },
}))

import { skalBaereToken, oprindelseAf } from './jarvisBrowser'

const API = 'https://api.srvlab.dk'
const TOKEN = 'et-token'

describe('token-afgrænsningen', () => {
  it('bærer tokenet mod vores eget API', () => {
    expect(skalBaereToken(`${API}/files/rapport.pdf`, API, TOKEN)).toBe(true)
    expect(skalBaereToken(`${API}/chat/history?x=1`, API, TOKEN)).toBe(true)
  })

  it('bærer det ALDRIG mod nogen anden vært', () => {
    // Det er hele grunden til at injektionen er forsvarlig: en browser er
    // til hele internettet, og en ubetinget header ville sende Bjørns token
    // til hver side Jarvis åbner.
    for (const fremmed of [
      'https://google.com/search?q=x',
      'https://github.com/a/b',
      'http://localhost:3000/',
      'https://duckduckgo.com/?q=hvad+er+en+webcontentsview',
    ]) {
      expect(skalBaereToken(fremmed, API, TOKEN)).toBe(false)
    }
  })

  it('lader sig IKKE narre af et værtsnavn der starter med vores', () => {
    // `https://api.srvlab.dk.angriber.dk` har vores vært som PRÆFIKS. Havde
    // reglen brugt startsWith, ville tokenet gå til angriberen.
    for (const snyd of [
      'https://api.srvlab.dk.angriber.dk/stjael',
      'https://api.srvlab.dk@angriber.dk/stjael',
      'https://notapi.srvlab.dk/x',
      'http://api.srvlab.dk/x',           // andet skema = anden oprindelse
      'https://api.srvlab.dk:8443/x',     // anden port = anden oprindelse
    ]) {
      expect(skalBaereToken(snyd, API, TOKEN)).toBe(false)
    }
  })

  it('bærer intet uden token, og intet uden kendt oprindelse', () => {
    expect(skalBaereToken(`${API}/files/x`, API, null)).toBe(false)
    expect(skalBaereToken(`${API}/files/x`, API, '')).toBe(false)
    expect(skalBaereToken(`${API}/files/x`, '', TOKEN)).toBe(false)
  })

  it('bærer intet på en URL der ikke kan læses', () => {
    for (const skrald of ['', '   ', 'ikke en url', 'about:blank', 'javascript:alert(1)']) {
      expect(skalBaereToken(skrald, API, TOKEN)).toBe(false)
    }
  })

  it('oprindelsen er helheden, ikke en streng', () => {
    expect(oprindelseAf('https://api.srvlab.dk/files/x?y=1#z')).toBe(API)
    expect(oprindelseAf('ikke en url')).toBe('')
  })
})
