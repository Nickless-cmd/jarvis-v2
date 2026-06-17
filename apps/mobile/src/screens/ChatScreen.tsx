import { useEffect, useState } from 'react'
import { KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native'
import { ApprovalCard } from '../components/ApprovalCard'
import { Composer } from '../components/Composer'
import { ConnectionPill } from '../components/ConnectionPill'
import { ErrorBanner } from '../components/ErrorBanner'
import { JarvisRing } from '../components/JarvisRing'
import { MessageList } from '../components/MessageList'
import { SidePanel } from '../components/SidePanel'
import { whoami } from '../lib/apiClient'
import { useAuth } from '../state/AuthContext'
import { useSessions } from '../state/SessionContext'
import { useStream } from '../state/StreamContext'
import { tokens } from '../theme/tokens'

export function ChatScreen() {
  const { config, signOut } = useAuth()
  const sessions = useSessions()
  const stream = useStream()
  const [panelOpen, setPanelOpen] = useState(false)
  const [displayName, setDisplayName] = useState('Jarvis')

  useEffect(() => {
    if (!config) return
    sessions.refresh(config).catch(() => undefined)
    whoami(config)
      .then((me) => setDisplayName(me.display_name || 'Jarvis'))
      .catch(() => undefined)
  }, [config])

  const ensureSessionAndSend = async (text: string) => {
    if (!config) return
    const sessionId = sessions.activeId ?? (await sessions.create(config)).id
    stream.send(config, sessionId, text)
  }

  const handleSelectSession = (sessionId: string) => {
    setPanelOpen(false)
    if (config) sessions.select(config, sessionId).catch(() => undefined)
  }

  const handleNewSession = () => {
    setPanelOpen(false)
    if (config) sessions.create(config).catch(() => undefined)
  }

  const lastUserMessage = [...sessions.messages].reverse().find((message) => message.role === 'user')
  const canRetry =
    !!lastUserMessage && (stream.state.status === 'interrupted' || stream.state.status === 'error')

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Åbn sessioner og plugins"
          onPress={() => setPanelOpen((open) => !open)}
          style={styles.headerTitle}
          hitSlop={8}
        >
          <JarvisRing />
          <Text style={styles.title} numberOfLines={1}>
            {displayName}
          </Text>
        </Pressable>
        <ConnectionPill label={stream.state.status} />
      </View>

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
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
      </KeyboardAvoidingView>

      {config ? (
        <SidePanel
          open={panelOpen}
          onClose={() => setPanelOpen(false)}
          config={config}
          displayName={displayName}
          sessions={sessions.sessions}
          activeId={sessions.activeId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          onSignOut={() => {
            setPanelOpen(false)
            void signOut()
          }}
        />
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0
  },
  flex: {
    flex: 1
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
    gap: tokens.spacing.sm,
    flexShrink: 1
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 18,
    fontWeight: '700',
    flexShrink: 1
  }
})
