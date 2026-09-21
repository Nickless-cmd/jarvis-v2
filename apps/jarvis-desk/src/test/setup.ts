import '@testing-library/jest-dom/vitest'

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
