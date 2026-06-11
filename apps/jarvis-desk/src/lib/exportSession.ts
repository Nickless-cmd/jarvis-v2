import { getSession, type ApiConfig } from './api'
import { blocksToPlainText } from './formatTime'

/** Eksportér en samtale som markdown-fil (klient-side download). */
export async function exportSessionMarkdown(config: ApiConfig, sessionId: string, title: string): Promise<void> {
  const { messages } = await getSession(config, sessionId)
  const lines: string[] = [`# ${title}`, '']
  for (const m of messages) {
    if (m.role !== 'user' && m.role !== 'assistant') continue
    lines.push(`## ${m.role === 'user' ? 'Bjørn' : 'Jarvis'}`)
    lines.push(blocksToPlainText(m.content as { type: string; text?: string }[]))
    lines.push('')
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title.replace(/[^a-z0-9æøå ]/gi, '').replace(/\s+/g, '_') || 'samtale'}.md`
  a.click()
  URL.revokeObjectURL(url)
}
