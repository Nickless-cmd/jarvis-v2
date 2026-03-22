function nowId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

function previewText(text) {
  const value = String(text || '').trim()
  if (!value) return 'No messages yet'
  return value.length > 48 ? `${value.slice(0, 48)}…` : value
}

export function createChatSession({ title, subtitle, bootstrapMessages = [] }) {
  const sessionTitle = String(title || '').trim() || 'New chat'
  return {
    id: nowId('session'),
    title: sessionTitle,
    subtitle: String(subtitle || '').trim(),
    lastMessage: bootstrapMessages.length > 0 ? previewText(bootstrapMessages.at(-1)?.content) : 'Ready',
    messages: [...bootstrapMessages],
  }
}

export function appendMessagesToSession(session, ...messages) {
  const nextMessages = [...session.messages, ...messages]
  const firstUser = nextMessages.find((message) => message.role === 'user')
  const title = firstUser ? previewText(firstUser.content) : session.title

  return {
    ...session,
    title,
    lastMessage: previewText(nextMessages.at(-1)?.content),
    messages: nextMessages,
  }
}
