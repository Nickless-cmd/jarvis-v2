export function outgoingChatText(text: string, researchMode: boolean): string {
  const trimmed = text.trim()
  if (!researchMode) return trimmed
  return [
    'Research mode: answer with sourced findings where possible, separate facts from inference, and call out uncertainty.',
    '',
    trimmed
  ].join('\n')
}
