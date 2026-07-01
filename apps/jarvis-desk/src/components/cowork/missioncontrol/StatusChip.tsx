/** Ét fælles status-farve/ikon-sprog for HELE Mission Control (runs, agenter, planlagt).
 *  Farve = betydning, lært én gang. Ukendt status → neutral grå (aldrig crash). */

type Tone = 'green' | 'red' | 'retry' | 'blue' | 'amber' | 'gray'

const STATUS_TONE: Record<string, { tone: Tone; label: string }> = {
  completed: { tone: 'green', label: 'Færdig' },
  done: { tone: 'green', label: 'Færdig' },
  ok: { tone: 'green', label: 'OK' },
  failed: { tone: 'red', label: 'Fejlet' },
  error: { tone: 'red', label: 'Fejl' },
  cancelled: { tone: 'red', label: 'Afbrudt' },
  canceled: { tone: 'red', label: 'Afbrudt' },
  retrying: { tone: 'retry', label: 'Genkører' },
  running: { tone: 'blue', label: 'Kører' },
  active: { tone: 'blue', label: 'Kører' },
  working: { tone: 'blue', label: 'Kører' },
  pending: { tone: 'amber', label: 'Afventer' },
  waiting: { tone: 'amber', label: 'Venter' },
  planned: { tone: 'amber', label: 'Planlagt' },
  idle: { tone: 'gray', label: 'Inaktiv' },
}

export function StatusChip({ status, label }: { status?: string | null; label?: string }) {
  const key = String(status || '').toLowerCase()
  const hit = STATUS_TONE[key] ?? { tone: 'gray' as Tone, label: status ? String(status) : '—' }
  return <span className={`mc-chip mc-chip--${hit.tone}`}>{label ?? hit.label}</span>
}
