export function formatFreshness(value) {
  const ts = Date.parse(String(value || ''))
  if (!Number.isFinite(ts)) return 'unknown'
  const delta = Math.max(0, Date.now() - ts)
  const sec = Math.floor(delta / 1000)
  if (sec < 10) return 'just now'
  if (sec < 60) return `${sec}s ago`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  const day = Math.floor(hr / 24)
  return `${day}d ago`
}

export function mcUpdateModeLabel(tabId) {
  if (tabId === 'overview') return 'entry + 30s + event assist'
  if (tabId === 'operations') return 'entry + 20s + event assist'
  if (tabId === 'observability') return 'ws feed + 60s summaries'
  if (tabId === 'jarvis') return 'entry + 30s + heartbeat events'
  return 'snapshot'
}

export function sectionTitleWithMeta({ source = '', fetchedAt = '', mode = '' } = {}) {
  const freshness = formatFreshness(fetchedAt)
  const parts = []
  if (mode) parts.push(`Mode: ${mode}`)
  if (source) parts.push(`Source: ${source}`)
  if (freshness) parts.push(`Freshness: ${freshness}`)
  return parts.join(' | ')
}
