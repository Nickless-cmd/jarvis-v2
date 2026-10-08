/** Toaster fra notifikations-feeden (Bjørn 7/10-2026).
 *
 * BAGGRUND. Indtil nu var det eneste der indikerede en ny notifikation at
 * klokken i sidebaren rystede — og prikken lyste. Det er diskret, men det
 * betyder ogsaa at man skal KOLLE PAA KLOKKEN for at se hvad der skete, og
 * man opdager det kun hvis man tilfaeldigvis kigger derhen.
 *
 * DETTE er det manglende led: en toast der glider ind, viser posten, og
 * lader brugeren AABNE den eller AFVISE den — og som forsvinder af sig selv
 * hvis man ikke goer noget. Klokken og prikken bliver uaendret; toasten
 * laegger sig ovenpaa som et engangs-varsel.
 *
 * HVORFOR DET ER BILLIGT. Klokken henter ALLEREDE hele listen
 * (`hentNotifikationer`) og bruger den kun til tallet og ringningen.
 * Felterne er der (`titel`, `tekst`, `slags`, `kan_afgoere`), og
 * handlingerne findes: `afgoerNotifikation`, `setNotifikation`,
 * `markNotificationsRead`. Ingen ny server-kode.
 *
 * HVORFOR `run_done` GODT MAA VISES HER — og ikke i klokken.
 * Klokken springer bevidst `run_done` over: maalt 4/10-2026 laa der 1152
 * aabne, og en klokke der altid ringer, ringer aldrig. En toast er noget
 * andet — den viser noget ÉN gang og forsvinder. Det er hele forskellen
 * mellem et badge og et felt, og derfor filtrerer denne komponent IKKE
 * `run_done` fra.
 *
 * BASELINE. Foerste hentning saetter baseline og viser INGEN toasts. Uden
 * det ville et opstart med 40 aabne poster give 40 toasts i traek. Derefter
 * er det kun id'er vi ikke har set foer der giver en toast.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AtSign, Bell, CircleAlert, CircleCheck, Flag, Key, MessageCircle,
  Package, Radar, ShieldAlert, ShieldX, X,
} from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { openEventSocket } from '../../lib/api'
import {
  afgoerNotifikation, hentNotifikationer, setNotifikation, type Notifikation,
} from '../../lib/notifikationerApi'
import { maaPolle } from '../../lib/ro'
import { markNotificationsRead } from '../../lib/notificationAttention'
import { spilToastKlang } from '../../lib/toastLyd'

/** Samme mapping som NotifikationsFeed — en post skal se ens ud i listen og
 *  i toasten. Ukendte slags faar klokken, saa en ny router-slags aldrig
 *  ender med et tomt felt. */
const IKON: Record<string, typeof Bell> = {
  approval: ShieldAlert, question: ShieldAlert,
  run_failed: CircleAlert, run_done: CircleCheck,
  release: Package,
  reach_out: MessageCircle,
  central_flag: Flag,
  membrane_breach: ShieldX,
  infra_security: Radar,
  keymaker_key_earned: Key,
  moltbook_mention: AtSign,
}

/** Tonen pr. slags — fejl skal lyde som fejl, ikke som «alt er fint». */
const TONE: Record<string, 'fejl' | 'ok' | 'neutral'> = {
  run_failed: 'fejl', membrane_breach: 'fejl', infra_security: 'fejl',
  run_done: 'ok', release: 'ok', keymaker_key_earned: 'ok',
}

/** Hvor laenge en toast lever, og hvor mange der maa staa paa skaermen. */
export const LEVETID_MS = 7000
const MAKS_SAMTIDIGE = 3

export function NotifikationsToast({ config, aktivSession, onAabenSession }: {
  config: ApiConfig | null
  /** Samtalen brugeren sidder i nu — svar fra den springes over paa serveren. */
  aktivSession?: string | null
  /** Kaldes naar brugeren trykker «Aabn». Session-id kan vaere null. */
  onAabenSession?: (sessionId: string | null) => void
}) {
  const [koe, setKoe] = useState<Notifikation[]>([])
  const [synlig, setSynlig] = useState(() => document.visibilityState !== 'hidden')
  const apiBaseUrl = config?.apiBaseUrl ?? ''
  const authToken = config?.authToken ?? null

  // `null` = vi har ikke sat baseline endnu. Foerste svar saetter den og
  // viser intet; derefter er forskellen mod dette saet de nye poster.
  const kendte = useRef<Set<string> | null>(null)
  const alive = useRef(true)
  const requestVersion = useRef(0)

  // `hentNu` gaar UDEN OM ro-loftet (`maaPolle`). Det er ikke en detalje:
  // klokken har haft samme skel siden 20/9, og uden det her er toasten den
  // eneste kanal der bliver slugt af ro-mekanismen.
  //
  // Maalt 8/10-2026: Bjørn hørte klokken ringe hver gang, men toasten kom kun
  // «en sjælden gang imellem». Aarsagen er praecis denne: begge komponenter
  // henter den SAMME liste, men naar WS-signalet «notifikation.ny» lander,
  // kalder klokken `hentNu` (altid igennem) mens toasten kaldte `hent` — som
  // foerst spoerger `maaPolle('notifikationer', 8000)`. Er der gaaet under
  // otte sekunder siden SIDSTE poll (klokken og toasten deler noeglen!), svarer
  // den nej, og toasten springer den nye post over. Klokken ringer altsaa,
  // lyden kommer — og toasten udebliver. Naar ro-faktoren saa gaar i gang
  // (8x efter tre minutter uden livstegn), bliver vinduet endnu bredere.
  //
  // En haendelse ER signalet. Den maa ikke sluges af et ro-loft — det er
  // samme regel som klokkens WS-lytter foelger.
  const hentNu = useCallback(() => {
    if (!apiBaseUrl) return
    const version = ++requestVersion.current
    hentNotifikationer({ apiBaseUrl, authToken }, aktivSession)
      .then((f) => {
        if (!alive.current || version !== requestVersion.current) return
        const aabne = f.poster.filter((p) => !p.foraeldet)

        if (kendte.current === null) {
          // Foerste svar: baseline. Ingen toasts — ellers ville et opstart
          // med mange aabne poster dumpe dem alle i hovedet paa brugeren.
          kendte.current = new Set(aabne.map((p) => p.id))
          return
        }

        const nye = aabne.filter((p) => !kendte.current!.has(p.id))
        if (!nye.length) return
        nye.forEach((p) => kendte.current!.add(p.id))

        // Lyden foelger den FOERSTE nye post — en lyd pr. post ville blive
        // en lydsalve naar flere lander i samme hentning.
        const foerste = nye[0]
        if (foerste) spilToastKlang(TONE[foerste.slags] ?? 'neutral')

        setKoe((k) => [...k, ...nye].slice(-MAKS_SAMTIDIGE))
      })
      .catch(() => { /* pollet/WS daekker; en fejlet hentning maa ikke stoeje */ })
  }, [apiBaseUrl, authToken, aktivSession])

  // Pollet — det er SIKKERHEDSNETTET, og her er ro-loftet rigtigt: ingen
  // grund til at spoerge hvert ottende sekund naar ingen kigger.
  const hent = useCallback(() => {
    if (!maaPolle('notifikationer', 8000)) return
    hentNu()
  }, [hentNu])

  useEffect(() => {
    alive.current = true
    const versions = requestVersion
    hent()
    const id = window.setInterval(hent, 8000)
    return () => { alive.current = false; versions.current++; window.clearInterval(id) }
  }, [hent])

  // Live-vejen — samme bus og samme filter som Klokke. Pollingen er
  // sikkerhedsnettet; DETTE er grunden til at en ny post dukker op med det
  // samme i stedet for op til otte sekunder senere.
  useEffect(() => {
    if (!apiBaseUrl) return
    let ws: WebSocket | null = null
    try {
      ws = openEventSocket({ apiBaseUrl, authToken })
      ws.onmessage = (e) => {
        try {
          const kind = String(JSON.parse(String(e.data))?.kind || '')
          if (kind.startsWith('notifikation.')) hentNu()
        } catch { /* ikke-JSON paa bussen er ikke vores */ }
      }
      ws.onerror = () => { /* pollet daekker */ }
    } catch { /* pollet daekker */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
  }, [apiBaseUrl, authToken, hentNu])

  useEffect(() => {
    const opdaterSynlighed = () => {
      const erSynlig = document.visibilityState !== 'hidden'
      setSynlig(erSynlig)
      if (erSynlig) hentNu()
    }
    document.addEventListener('visibilitychange', opdaterSynlighed)
    return () => document.removeEventListener('visibilitychange', opdaterSynlighed)
  }, [hentNu])

  const luk = useCallback((id: string) => {
    setKoe((k) => k.filter((p) => p.id !== id))
  }, [])

  const aabn = useCallback((p: Notifikation) => {
    markNotificationsRead([p.id])
    onAabenSession?.(p.session_id)
    luk(p.id)
  }, [luk, onAabenSession])

  const afvis = useCallback((p: Notifikation) => {
    if (!config) return
    // To slags poster, to veje — og forskellen er `kan_afgoere`:
    //   en post der KRAEVER et svar afgoeres (approved=false = afvist),
    //   en ren orientering lukkes.
    const kald = p.kan_afgoere
      ? afgoerNotifikation(config, p.id, false)
      : setNotifikation(config, p.id)
    // Optimistisk: feltet forsvinder straks. Fejler kaldet, kommer posten
    // tilbage ved naeste hentning — den forsvinder ikke af sig selv af den
    // grund, og serveren er stadig kilden.
    luk(p.id)
    void kald.catch(() => { /* naeste hentning genopretter sandheden */ })
  }, [config, luk])

  if (!koe.length) return null

  return (
    <div className="notif-toast-lag" role="status" aria-live="polite">
      {koe.map((p) => (
        <ToastKort key={p.id} post={p}
                   synlig={synlig}
                   onAabn={() => aabn(p)}
                   onAfvis={() => afvis(p)}
                   onLuk={() => luk(p.id)} />
      ))}
    </div>
  )
}

function ToastKort({ post, synlig, onAabn, onAfvis, onLuk }: {
  post: Notifikation
  synlig: boolean
  onAabn: () => void
  onAfvis: () => void
  /** Fjern feltet UDEN at afvise posten — den bliver saa liggende i feedet. */
  onLuk: () => void
}) {
  const [ude, setUde] = useState(false)
  const [ind, setInd] = useState(false)

  // Glider ind i naeste frame — uden det springer overgangen over, fordi
  // elementet ikke har haft en «foer»-tilstand at animere fra.
  useEffect(() => {
    const id = requestAnimationFrame(() => setInd(true))
    return () => cancelAnimationFrame(id)
  }, [])

  // Nedtaellingen er en CSS-animation, ikke en JS-taeler. Det er ikke en
  // smagssag: hover-pause bliver da én regel (`animation-play-state`) i
  // stedet for bogfoering af forloeben tid, og `animationend` er det praecise
  // signal om at tiden er loebet — en ramme-taeler kunne drive fra den linje
  // brugeren faktisk ser.
  //
  // Naar den loeber ud, forsvinder FELTET — posten afvises IKKE. Det er hele
  // forskellen: at lade et felt ligge i syv sekunder er ikke det samme som at
  // sige nej til en godkendelse. Ref, ikke afhaengighed — en ny `onLuk`-
  // reference maa ikke nulstille den igangvaerende fade.
  const lukRef = useRef(onLuk)
  lukRef.current = onLuk
  useEffect(() => {
    if (!ude) return
    const id = window.setTimeout(() => lukRef.current(), 520)
    return () => window.clearTimeout(id)
  }, [ude])

  const Ikon = IKON[post.slags] ?? Bell
  const tone = TONE[post.slags]
  const klasse = [
    'notif-toast',
    ind ? 'er-ind' : '',
    ude ? 'er-ude' : '',
    tone === 'fejl' ? 'er-fejl' : tone === 'ok' ? 'er-ok' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={klasse}
         onClick={onAabn}
         role="button" tabIndex={0}
         onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onAabn() } }}>
      <span className="notif-toast-ikon" aria-hidden="true"><Ikon size={13} /></span>
      <div className="notif-toast-indhold">
        <div className="notif-toast-slags">{post.slags.replace(/_/g, ' ')}</div>
        <div className="notif-toast-titel">{post.titel}</div>
        {post.tekst && <p className="notif-toast-tekst">{post.tekst}</p>}
        <div className="notif-toast-knapper">
          <button type="button" className="primaer"
                  onClick={(e) => { e.stopPropagation(); onAabn() }}>Åbn</button>
          <button type="button"
                  onClick={(e) => { e.stopPropagation(); onAfvis() }}>
            {post.kan_afgoere ? 'Afvis' : 'Luk'}
          </button>
        </div>
      </div>
      <button type="button" className="notif-toast-luk" aria-label="Luk feltet"
              onClick={(e) => { e.stopPropagation(); onLuk() }}>
        <X size={12} />
      </button>
      <span className="notif-toast-nedtaelling" aria-hidden="true"
            style={{ animationDuration: `${LEVETID_MS}ms`, animationPlayState: synlig ? undefined : 'paused' }}
            onAnimationEnd={() => { if (synlig) setUde(true) }} />
    </div>
  )
}
