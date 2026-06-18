// Dansk relativ dato til session-liste ("i dag", "i går", "3 dage", "12. jun").
const MONTHS = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

export function formatRelativeDate(iso: string | undefined, now: Date): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const days = Math.round((startOfDay(now) - startOfDay(d)) / 86_400_000)
  if (days <= 0) return 'i dag'
  if (days === 1) return 'i går'
  if (days < 7) return `${days} dage`
  return `${d.getDate()}. ${MONTHS[d.getMonth()]}`
}
