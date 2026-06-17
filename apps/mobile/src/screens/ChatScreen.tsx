import { useEffect } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { ApprovalCard } from '../components/ApprovalCard'
import { Composer } from '../components/Composer'
import { ConnectionPill } from '../components/ConnectionPill'
import { ErrorBanner } from '../components/ErrorBanner'
import { JarvisRing } from '../components/JarvisRing'
import { MessageList } from '../components/MessageList'
import { useAuth } from '../state/AuthContext'
import { useSessions } from '../state/SessionContext'
import { useStream } from '../state/StreamContext'
import { tokens } from '../theme/tokens'

export function ChatScreen() {
  const { config } = useAuth()
  const sessions = useSessions()
  const stream = useStream()

  useEffect(() => {
    if (!config) return
    sessions.refresh(config).catch(() => undefined)
  }, [config])

  const ensureSessionAndSend = async (text: string) => {
    if (!config) return
    const sessionId = sessions.activeId ?? (await sessions.create(config)).id
    stream.send(config, sessionId, text)
  }

  const lastUserMessage = [...sessions.messages].reverse().find((message) => message.role === 'user')
  const canRetry =
    !!lastUserMessage && (stream.state.status === 'interrupted' || stream.state.status === 'error')

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <View style={styles.headerTitle}>
          <JarvisRing />
          <Text style={styles.title}>Jarvis</Text>
        </View>
        <ConnectionPill label={stream.state.status} />
      </View>
      <MessageList messages={sessions.messages} blocks={stream.state.blocks} />
      {canRetry ? (
        <ErrorBanner
          title={stream.state.status === 'error' ? 'Stream fejlede' : 'Svar stoppet'}
          detail="Du kan prøve den seneste besked igen."
          actionLabel="Retry"
          onAction={() => void ensureSessionAndSend(lastUserMessage.content)}
        />
      ) : null}
      {stream.approval && config ? (
        <ApprovalCard
          approval={stream.approval}
          onApprove={() => void stream.approve(config)}
          onDeny={() => void stream.deny(config)}
        />
      ) : null}
      <Composer
        disabled={!config}
        working={stream.state.status === 'working'}
        onSend={ensureSessionAndSend}
        onStop={() => (config ? stream.stop(config) : undefined)}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0
  },
  header: {
    height: 56,
    paddingHorizontal: tokens.spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  headerTitle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 18,
    fontWeight: '700'
  }
})
