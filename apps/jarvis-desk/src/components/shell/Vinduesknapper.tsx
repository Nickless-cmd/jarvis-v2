import { useEffect, useState } from 'react'

/**
 * Vinduets egne knapper — minimer, forstør/gendan, luk.
 *
 * Bjørn 16/9-2026: «vindues rammen den med luk miniere og forstør inttegreret
 * lige som i cc». Vinduet er derfor uden OS-ramme (frame: false).
 *
 * Tre ting er bevidst:
 *
 *  1. Den sidder FAST i hjørnet af vinduet, ikke i en fladens header. Desk
 *     har ingen header der findes på alle flader (.main-head er død CSS —
 *     ingen komponent bruger den). Sad knapperne i en header, ville de
 *     forsvinde på den første flade der ikke har en, og så kan vinduet ikke
 *     lukkes uden at dræbe processen.
 *
 *  2. Den viser INTET uden broen. I browseren (npm run dev) findes
 *     window.jarvisDesk ikke — tre knapper der ikke gør noget er værre end
 *     ingen knapper.
 *
 *  3. Den viser intet på macOS. Dér er lyskurven systemets egen, og vinduet
 *     beholder den (titleBarStyle: hiddenInset). To sæt knapper i samme
 *     hjørne ville være en fejl, ikke en dobbeltsikring.
 */
interface VinduesBro {
  minimer: () => Promise<void>
  vekselMaksimer: () => Promise<boolean>
  luk: () => Promise<void>
  erMaksimeret: () => Promise<boolean>
  paaMaksimeretAendret: (cb: (maksimeret: boolean) => void) => () => void
}

function hentBro(): { vindue?: VinduesBro; platform?: string } | undefined {
  return (window as unknown as { jarvisDesk?: { vindue?: VinduesBro; platform?: string } }).jarvisDesk
}

export function Vinduesknapper() {
  const desk = hentBro()
  const bro = desk?.vindue
  const [maksimeret, setMaksimeret] = useState(false)

  const egenRamme = !!bro && desk?.platform !== 'darwin'

  // Traek-omraader og pladsen til knapperne hoerer til RAMMEN, ikke til
  // fladerne. Uden klassen ville en browser-fane faa 152 px tom plads i
  // headeren til knapper der ikke findes.
  useEffect(() => {
    document.body.classList.toggle('egen-ramme', egenRamme)
    return () => document.body.classList.remove('egen-ramme')
  }, [egenRamme])

  useEffect(() => {
    if (!bro) return
    let levende = true
    void bro.erMaksimeret().then((m) => { if (levende) setMaksimeret(m) })
    // Tilstanden kan også ændre sig uden om knappen: dobbeltklik på bjælken,
    // en genvej, vindueshåndteringen. Uden dette ville ikonet lyve.
    const stop = bro.paaMaksimeretAendret((m) => setMaksimeret(m))
    return () => { levende = false; stop() }
  }, [bro])

  if (!egenRamme) return null

  return (
    <>
      {/* Nod-bjaelke: uden OS-ramme kan vinduet kun flyttes af et traek-omraade.
          Skallens egne bjaelker (.sidebar-top, .chatview-head) er traekbare —
          men paa setup-skaermen, mens indstillinger hentes, og i
          ErrorBoundary findes skallen ikke, og saa sad vinduet fast.
          CSS'en viser den KUN naar .window mangler, saa den aldrig spiser
          klik fra en flade der selv har en bjaelke. */}
      <div className="vinduesbjaelke" aria-hidden="true" />
    <div className="vinduesknapper" role="group" aria-label="Vindue">
      <button type="button" aria-label="Minimer" title="Minimer" onClick={() => void bro.minimer()}>
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <path d="M1 5h8" stroke="currentColor" strokeWidth="1" />
        </svg>
      </button>
      <button
        type="button"
        aria-label={maksimeret ? 'Gendan' : 'Forstør'}
        title={maksimeret ? 'Gendan' : 'Forstør'}
        onClick={() => void bro.vekselMaksimer().then(setMaksimeret)}
      >
        {maksimeret ? (
          /* Forreste firkant nederst til venstre, den bagerste bag den.
             Foerste udgave lod den bagerstes underkant loebe INDEN I den
             forreste — to streger i en 10 px firkant er nok til at ikonet
             ser i stykker ud. */
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
            <path d="M1.5 3.5h5v5h-5z M3.5 3.5V1.5h5v5h-2" fill="none" stroke="currentColor" strokeWidth="1" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
            <rect x="1.5" y="1.5" width="7" height="7" fill="none" stroke="currentColor" strokeWidth="1" />
          </svg>
        )}
      </button>
      <button type="button" className="er-luk" aria-label="Luk" title="Luk" onClick={() => void bro.luk()}>
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
          <path d="M1.5 1.5l7 7M8.5 1.5l-7 7" stroke="currentColor" strokeWidth="1" />
        </svg>
      </button>
    </div>
    </>
  )
}
