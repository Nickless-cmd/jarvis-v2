import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { aspektCss } from '../../lib/medieVaerktoejer'
import {
  BILLED_FLISE_MAX_BREDDE,
  BILLED_FLISE_MIN_BREDDE,
  fordelBilledRaekker,
} from '../../lib/billedGrid'

export interface BilledGridFlise {
  key: string
  indhold: ReactNode
  aspekt?: string
  pladsholder?: boolean
}

export function BilledGrid({ fliser }: { fliser: BilledGridFlise[] }) {
  const rod = useRef<HTMLDivElement | null>(null)
  const [bredde, setBredde] = useState(320)

  useLayoutEffect(() => {
    const element = rod.current
    if (!element) return
    if (element.clientWidth > 0) setBredde(element.clientWidth)
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(([entry]) => {
      const naeste = entry?.contentRect.width
      if (naeste && Number.isFinite(naeste)) setBredde(naeste)
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const fordeling = fordelBilledRaekker(fliser.length, bredde)
  let start = 0

  return (
    <div ref={rod} className="billed-grid" data-layout="pack">
      {fordeling.map((antal, raekke) => {
        const raekkeFliser = fliser.slice(start, start + antal)
        start += antal
        return (
          <div className="billed-grid-raekke" key={`raekke-${raekke}`}>
            {raekkeFliser.map((flise) => (
              <div
                className={`billed-grid-flise${flise.pladsholder ? ' billed-grid-pladsholder' : ''}`}
                data-aspekt={flise.aspekt ?? 'ukendt'}
                key={flise.key}
                style={{
                  aspectRatio: aspektCss(flise.aspekt),
                  minWidth: BILLED_FLISE_MIN_BREDDE,
                  maxWidth: BILLED_FLISE_MAX_BREDDE,
                }}
              >
                {flise.indhold}
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
