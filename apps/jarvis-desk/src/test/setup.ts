import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/dom'

/**
 * Hvor længe `findBy*` og `waitFor` venter før de giver op.
 *
 * Standard er 1000 ms, og den er målt for kort på CI. 29/10-2026 faldt
 * `ChatView.test.tsx > shows optimistic user msg` på CI med
 * «Unable to find an element with the text: hej» efter 1205 ms, mens samme
 * test svarede på 355 ms lokalt og bestod 8/8 isoleret. Hele suiten tog
 * 187 s på CI mod 75 s her — runneren er ~2,5× langsommere, og en
 * `userEvent.type` på fire tastetryk plus den efterfølgende render kan
 * sagtens krydse et sekund når CPU'en er mættet af 392 parallelle filer.
 *
 * 17/10-2026 blev samme test rettet fra `getByText` (synkron, ventede slet
 * ikke) til `findByText`. Det var den rigtige retning, men utlistrækkelig:
 * den arvede stadig de 1000 ms. Fejlen kom igen med samme besked.
 *
 * 3000 ms er ~2,5× den målte fejlgrænse — nok til CI's last, ikke så meget
 * at en test der venter på noget der ALDRIG kommer kan hænge i minutter.
 * Dette ændrer hvad testene venter på, ikke hvad de påstår.
 *
 * `setup.asyncUtilTimeout.test.ts` fælder det hvis linjen forsvinder.
 */
configure({ asyncUtilTimeout: 3000 })

/**
 * jsdom har ingen ResizeObserver.
 *
 * Jarvis' browser-rude bruger den til at melde hullets rektangel ved ENHVER
 * ændring — et window-resize-lytteord ville misse et sidepanel der folder ud.
 * Manglen er testmiljøets, så den stubbes frem for at svække komponenten.
 *
 * Den stod før lokalt i JarvisBrowserPanel.test.tsx. Da ruden fik plads i BÅDE
 * chat- og code-fladen, betød det at enhver view-test der åbnede den bare så
 * et tomt træ — effekten kastede, og React pillede visningen ned igen uden at
 * sige hvorfor (21/9-2026).
 *
 * Den lokale udgave kaldte `cb()` bart, og det var nok for én komponent der
 * ignorerer argumentet. Som GLOBAL stub er det ikke nok: recharts' egen
 * ResponsiveContainer læser `entries[0].contentRect`, og otte cheap-lane-tests
 * gik ned på `Cannot read properties of undefined (reading '0')`. En stub der
 * gælder alle, skal holde den rigtige kontrakt.
 */
class ResizeObserverStub {
  constructor(private cb: (entries: unknown[], obs: unknown) => void) {}
  observe(target?: Element) {
    const r = target?.getBoundingClientRect?.()
    this.cb([{ target, contentRect: r ?? { width: 0, height: 0, top: 0, left: 0, bottom: 0, right: 0, x: 0, y: 0 } }], this)
  }
  disconnect() {}
  unobserve() {}
}
;(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub
