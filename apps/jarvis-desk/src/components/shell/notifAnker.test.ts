/**
 * Ankeret for toast-stakken — ren beregning, ingen DOM.
 *
 * BAGGRUND (1/11-2026). Bjørn: «toastbeskederne burde komme i bunden af appen
 * i hjørnet, men trækkes op over composer-højden». Målt på hans skærmbillede:
 * toasten svævede ~50 px over skrivefeltets overkant, med HELT TOMT mørkt rum
 * mellem sig og feltet. Årsagen var at ankeret blev sat fra composerens TOP:
 *
 *     bottom = window.innerHeight - composerRect.top + 10
 *
 * Det er korrekt når toasten står oven på skrivefeltet — men forkert når den
 * slet ikke er i nærheden af det. Skrivefeltet er `max-width: 820px` og
 * centreret; en 268 px toast i højre kant ligger ved siden af det, ikke over
 * det, og så skal den ned i bunden i stedet for at hænge i luften.
 *
 * TESTEN ER REN MED VILJE. jsdom har ingen layout-motor: `getBoundingClientRect`
 * svarer nuller, så en test der «måler i DOM'en» ville bestå af den forkerte
 * grund — den ville bare genfinde de nuller den selv satte ind. Tallene her er
 * Bjoerns faktiske skaermbillede-Geometri, skrevet ind som konstanter.
 */

import { describe, expect, it } from 'vitest'
import { beregnNotifBund } from './notifAnker'

// Bjørns skærmbillede 1/11-2026 (1920x1080, skaleret til 1000x1000):
//   composer-area: top 900, bund 1050 (statusbar under)
//   toast: 268 px bred, right: 22px
const SKAERM = { innerHeight: 1080, innerWidth: 1920 }

describe('beregnNotifBund — toasten skal i bunden, ikke hænge i luften', () => {
  it('lægger toasten i bunden når der er plads til højre for skrivefeltet', () => {
    // Skrivefeltet er 820px centreret: 550..1370. Toasten 268px ved right:22
    // fylder 1630..1898 — den ligger HELT til højre for feltet.
    const bund = beregnNotifBund({
      ...SKAERM,
      composer: { left: 550, right: 1370, top: 900 },
      toastBredde: 268,
      hoejreMargin: 22,
      bundGulv: 14,
    })
    expect(bund).toBe(14)
  })

  it('hæver toasten over skrivefeltet når den ville dække det', () => {
    // Smal skærm: skrivefeltet fylder 40..920, toasten 630..898 — overlap.
    const bund = beregnNotifBund({
      innerHeight: 900,
      innerWidth: 960,
      composer: { left: 40, right: 920, top: 760 },
      toastBredde: 268,
      hoejreMargin: 22,
      bundGulv: 14,
    })
    // 900 - 760 + 10 = 150 — over feltets overkant, som før.
    expect(bund).toBe(150)
  })

  it('regner IKKE overlap naar toasten praecis rører feltets hoejre kant', () => {
    // toastLeft = 1370 = composer.right → ingen overlap, den ligger ved siden af.
    const bund = beregnNotifBund({
      ...SKAERM,
      composer: { left: 550, right: 1370, top: 900 },
      toastBredde: 268,
      hoejreMargin: 22,
      bundGulv: 14,
    })
    expect(bund).toBe(14)
  })

  it('regner overlap naar toasten er 1px inde over feltet', () => {
    // composer.right = 1631, toastLeft = 1630 → 1px overlap = overlap.
    const bund = beregnNotifBund({
      ...SKAERM,
      composer: { left: 550, right: 1631, top: 900 },
      toastBredde: 268,
      hoejreMargin: 22,
      bundGulv: 14,
    })
    expect(bund).toBe(190) // 1080 - 900 + 10
  })

  it('falder tilbage til CSS-gulvet naar der ingen skriveflade findes', () => {
    expect(
      beregnNotifBund({ ...SKAERM, composer: null, toastBredde: 268, hoejreMargin: 22, bundGulv: 14 }),
    ).toBe(14)
  })

  it('holder et gulv saa et felt aldrig kan ligge halvt uden for skaermen', () => {
    // Composerens top ligger UNDER bunden (fx midt i en animation).
    const bund = beregnNotifBund({
      innerHeight: 800,
      innerWidth: 960,
      composer: { left: 40, right: 920, top: 795 },
      toastBredde: 268,
      hoejreMargin: 22,
      bundGulv: 14,
    })
    // 800 - 795 + 10 = 15. Gulvet (14) er lavere, saa 15 vinder.
    expect(bund).toBe(15)
  })

  it('lægger sig OVER opmærksomhedslinjen naar den staar i samme hjørne', () => {
    // `.opm-vaert` ligger bottom:14 right:18. Uden dette ville toasten
    // male hen over den — samme fejl som skinnen havde 16/9.
    const bund = beregnNotifBund({
      ...SKAERM,
      composer: { left: 550, right: 1370, top: 900 },
      toastBredde: 268,
      hoejreMargin: 22,
      bundGulv: 14,
      opmHoejde: 34,
    })
    expect(bund).toBe(56) // 14 + 34 + 8
  })
})
