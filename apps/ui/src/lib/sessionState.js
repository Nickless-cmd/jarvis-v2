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

export function updateSessionMessage(session, messageId, updater) {
  const nextMessages = session.messages.map((message) =>
    message.id === messageId ? { ...message, ...updater(message) } : message
  )

  return {
    ...session,
    lastMessage: previewText(nextMessages.at(-1)?.content),
    messages: nextMessages,
  }
}

export function upsertSessionMessage(session, message) {
  const normalized = {
    id: String(message?.id || '').trim(),
    role: String(message?.role || '').trim() || 'assistant',
    content: String(message?.content || '').trim(),
    ts: String(message?.ts || '').trim(),
    created_at: String(message?.created_at || '').trim(),
  }
  if (!normalized.id || !normalized.content) {
    return session
  }

  const existingIndex = session.messages.findIndex((item) => item.id === normalized.id)
  const nextMessages =
    existingIndex >= 0
      ? session.messages.map((item, index) => (index === existingIndex ? { ...item, ...normalized, pending: false } : item))
      : [...session.messages, normalized]
  const firstUser = nextMessages.find((item) => item.role === 'user')
  const title = firstUser ? previewText(firstUser.content) : session.title

  return {
    ...session,
    title,
    lastMessage: previewText(nextMessages.at(-1)?.content),
    message_count: nextMessages.length,
    updated_at: normalized.created_at || session.updated_at,
    messages: nextMessages,
  }
}
