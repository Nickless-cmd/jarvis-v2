import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getKontekst, type KontekstResume } from '../../lib/coworkApi'

/**
 * «Hvad Jarvis brugte i sidste tur» — filer, kilder, størrelse.
 *
 * Codex' punkt 3 (6/9-2026): brugeren skulle kunne se hvilke filer, memories
 * og regler der er i spil, uden at grave i indstillinger. Tallene er MÅLTE, ikke
 * estimerede: de kommer fra sidste turs faktiske prompt-sammensætning. Derfor
 * står der «sidste tur» og ikke «denne tur».
 *
 * Bor i Miljø-feltet under Kontekst-rækken (19/9-2026). Den lå som en egen
 * linje mellem liveness-linjen og skrivefeltet, helt ude til venstre — Bjørn:
 * «det ser dumt ud … burde den ikke ligge i miljøfeltet?». Den hentede også
 * uden session, så den viste sidste tur i ENHVER samtale, ikke den man stod i.
 * Hentes først når rækken foldes ud.
 */
export function KontekstDetaljer({
  config, sessionId,
}: { config: ApiConfig | undefined; sessionId?: string | null }) {
  const [data, setData] = useState<KontekstResume | null | undefined>(undefined)

  useEffect(() => {
    if (!config) return
    let levende = true
    getKontekst(config, sessionId ?? undefined)
      .then((d) => { if (levende) setData(d) })
      .catch(() => { if (levende) setData(null) })
    return () => { levende = false }
  }, [config?.apiBaseUrl, config?.authToken, sessionId])

  if (data === undefined) return <p className="ctx-note">Henter…</p>
  if (!data?.har_data) return <p className="ctx-note">Ingen målt tur i denne samtale endnu.</p>

  const kTokens = Math.round(data.tegn / 4 / 100) / 10
  return (
    <div className="ctx-krop">
      <p className="ctx-note">
        {data.filer.length} filer · {data.kilder.length} kilder · ~{kTokens}k tokens — målt på sidste tur.
      </p>
      <Gruppe titel="Filer" ting={data.filer} />
      <Gruppe titel="Kilder" ting={data.kilder} maks={18} />
      {data.udeladt.length > 0 && <Gruppe titel="Udeladt (plads)" ting={data.udeladt} maks={8} />}
    </div>
  )
}

function Gruppe({ titel, ting, maks = 12 }: { titel: string; ting: string[]; maks?: number }) {
  if (ting.length === 0) return null
  return (
    <div className="ctx-gruppe">
      <span className="ctx-gruppe-titel">{titel}</span>
      <div className="ctx-chips">
        {ting.slice(0, maks).map((t) => (
          <span key={t} className="ctx-chip" title={t}>{t}</span>
        ))}
        {ting.length > maks && <span className="ctx-mere">+{ting.length - maks}</span>}
      </div>
    </div>
  )
}
