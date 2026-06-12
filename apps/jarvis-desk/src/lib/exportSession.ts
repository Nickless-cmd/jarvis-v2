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
  const markdown = lines.join('\n')
  const filename = `${title.replace(/[^a-z0-9æøå ]/gi, '').replace(/\s+/g, '_') || 'samtale'}.md`

  // I Electron er renderer-side blob-download upålidelig — brug native gem-dialog
  // via IPC. Falder tilbage til blob-download i browser/dev hvor broen ikke findes.
  const desk = (window as unknown as {
    jarvisDesk?: { exportMarkdown?: (md: string, name: string) => Promise<boolean> }
  }).jarvisDesk
  if (desk?.exportMarkdown) {
    await desk.exportMarkdown(markdown, filename)
    return
  }
  const blob = new Blob([markdown], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
