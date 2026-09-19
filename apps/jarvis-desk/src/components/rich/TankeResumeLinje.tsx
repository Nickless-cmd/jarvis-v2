import { Brain } from 'lucide-react'

/**
 * Resuméet af tænkningen over en værktøjsgruppe — visningen «Tænkning»
 * (Claude Desktop: «a one-line recap of Claude's thinking above each tool
 * group»). Samme 20 px-celle og indrykning som linjerne under den, men
 * dæmpet og kursiv: det er optakten til gruppen, ikke en handling.
 */
export function TankeResumeLinje({ tekst }: { tekst: string }) {
  return (
    <div className="tanke-resume" data-testid="tanke-resume">
      <span className="toolgroup-spark" aria-hidden="true">
        <Brain size={15} className="toolgroup-icon" strokeWidth={1.8} />
      </span>
      <span className="tanke-resume-tekst">{tekst}</span>
    </div>
  )
}
