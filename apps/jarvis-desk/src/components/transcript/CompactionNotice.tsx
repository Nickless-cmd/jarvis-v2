import { Minimize2 } from 'lucide-react'
import type { CompactionStats } from '../../lib/api'

/** Persistent transcript event. Savings are an estimate of freed context space. */
export function CompactionNotice({ stats }: { stats?: CompactionStats }) {
  const freed = stats?.freed_tokens ?? 0
  const amount = freed > 0 ? ` · ca. ${new Intl.NumberFormat('da-DK').format(freed)} konteksttokens frigjort` : ''
  return (
    <div className="komprimeringslinje" aria-label={`Samtalen blev komprimeret${amount}`}>
      <Minimize2 size={13} aria-hidden="true" />
      <span>Samtalen blev komprimeret{amount}</span>
    </div>
  )
}
