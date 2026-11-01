/**
 * Ankeret for toast-stakken — REN beregning, ingen DOM.
 *
 * ── HVORFOR DEN ER TRUKKET UD (1/11-2026) ─────────────────────────────────
 *
 * Bjørn: «toastbeskederne burde komme i bunden af appen i hjørnet, men trækkes
 * op over composer-højden». Målt på hans skærmbillede: toasten svævede ~50 px
 * over skrivefeltets overkant, og området mellem dem var HELT TOMT mørkt rum.
 *
 * Årsagen var at ankeret blev sat fra composerens TOP, ubetinget:
 *
 *     bottom = window.innerHeight - composerRect.top + 10
 *
 * Det tal er rigtigt når toasten står oven på skrivefeltet. Men skrivefeltet er
 * `max-width: 820px` og centreret — en 268 px toast i højre kant ligger ved
 * SIDEN AF det, ikke oven på det, og så er der ingen grund til at løfte den.
 * Den skal ned i bunden, hvor Bjørn bad om at have den.
 *
 * ── HVORFOR EN REN FUNKTION ───────────────────────────────────────────────
 *
 * jsdom har ingen layout-motor: `getBoundingClientRect` svarer nuller. En test
 * der «måler i DOM'en» ville derfor bestå af den forkerte grund — den ville
 * bare genfinde de nuller den selv lagde ind, og en død gren ville se levende
 * ud. Tallene i testen er Bjørns faktiske skærmbillede-geometri, skrevet ind
 * som konstanter.
 */

/** Rektangel-formatet vi har brug for — ikke hele DOMRect. */
export interface AnkerRektangel {
  left: number
  right: number
  top: number
}

export interface AnkerInput {
  innerHeight: number
  innerWidth: number
  /** Den synlige, nederste skriveflade — eller `null` hvis fladen ingen har. */
  composer: AnkerRektangel | null
  /** Toastens bredde i px (CSS: 268). */
  toastBredde: number
  /** Afstand fra viewportens højre kant (CSS: 22). */
  hoejreMargin: number
  /** Bund i bunden af vinduet når intet er i vejen (CSS-fallback: 14). */
  bundGulv: number
  /**
   * Højden af en synlig opmærksomhedslinje i SAMME hjørne (`.opm-vaert`,
   * `bottom: 14px; right: 18px`). 0 = ingen. Uden dette ville de to ligge
   * oven i hinanden i bunden — den ene ville skjule den anden.
   */
  opmHoejde?: number
}

/** Hvor mange px luft der skal være over skrivefeltet når vi løfter. */
const LUFT_OVER_FELT = 10
/** Afstand mellem opmærksomhedslinjen og toast-stakken når de deler hjørne. */
const AFSTAND_TIL_OPM = 8

/**
 * Beregn `--notif-bund` i px.
 *
 * Reglen, i den rækkefølge den afgøres:
 *
 *  1. Er der ingen skriveflade (PWA, første render)? → bundgulvet.
 *  2. Ligger toasten HELT til højre for skrivefladen? → bundgulvet.
 *     (Berøring tæller som «ved siden af»: `toastLeft >= composer.right`.)
 *  3. Ellers ville den dække skrivefeltet → løft den til feltets overkant + 10.
 *
 * Står der en opmærksomhedslinje i samme hjørne, lægges gulvet oven på den i
 * stedet for at de to maler hen over hinanden.
 */
export function beregnNotifBund(o: AnkerInput): number {
  const opm = Math.max(0, Math.round(o.opmHoejde ?? 0))
  const gulv = o.bundGulv + (opm > 0 ? opm + AFSTAND_TIL_OPM : 0)

  if (!o.composer) return gulv

  const toastLeft = o.innerWidth - o.hoejreMargin - o.toastBredde
  if (toastLeft >= o.composer.right) return gulv

  return Math.max(gulv, Math.round(o.innerHeight - o.composer.top) + LUFT_OVER_FELT)
}
