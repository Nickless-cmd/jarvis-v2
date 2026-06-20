import { useEffect } from 'react'
import { ActivityIndicator, StatusBar, StyleSheet, Text, View } from 'react-native'
import { SafeAreaProvider, SafeAreaView, initialWindowMetrics } from 'react-native-safe-area-context'
import { MessageList } from '../components/MessageList'
import { Composer } from '../components/Composer'
import { AuthProvider, useAuth } from '../state/AuthContext'
import { SessionProvider, useSessions } from '../state/SessionContext'
import { StreamProvider, useStream } from '../state/StreamContext'
import { tokens } from '../theme/tokens'

/** Kompakt 1-session-chat. Henter sessionen, viser beskeder + composer,
 *  sender via samme stream som hovedappen (server-autoritativ session). */
function BubbleChat({ sessionId, title }: { sessionId: string; title: string }) {
  const { config } = useAuth()
  const sessions = useSessions()
  const stream = useStream()

  useEffect(() => {
    if (config && sessionId) void sessions.select(config, sessionId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.authToken, sessionId])

  const onSend = (text: string) => {
    if (config && sessionId) stream.send(config, sessionId, text)
  }

  return (
    <View style={styles.chat}>
      <Text style={styles.title} numberOfLines={1}>
        {title || 'Jarvis'}
      </Text>
      <View style={styles.list}>
        <MessageList messages={sessions.messages} blocks={stream.state.blocks} />
      </View>
      <Composer
        onSend={onSend}
        working={stream.state.status === 'working'}
        onStop={() => {
          if (config) void stream.stop(config)
        }}
      />
    </View>
  )
}

function BubbleBody({ sessionId, title }: { sessionId: string; title: string }) {
  const { config, loading } = useAuth()
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={tokens.color.accent} />
      </View>
    )
  }
  if (!config) {
    return (
      <View style={styles.center}>
        <Text style={styles.hint}>Åbn appen og log ind for at chatte i boblen.</Text>
      </View>
    )
  }
  return (
    <SessionProvider key={JSON.stringify([config.apiBaseUrl, config.authToken])}>
      <StreamProvider>
        <BubbleChat sessionId={sessionId} title={title} />
      </StreamProvider>
    </SessionProvider>
  )
}

/** Root-komponent registreret som "JarvisBubble". Modtager initialProps
 *  {sessionId, title} fra BubbleActivity. */
export function BubbleChatRoot(props: { sessionId?: string; title?: string }) {
  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <AuthProvider>
        <SafeAreaView style={styles.root}>
          <StatusBar barStyle="light-content" />
          <BubbleBody sessionId={props.sessionId ?? ''} title={props.title ?? ''} />
        </SafeAreaView>
      </AuthProvider>
    </SafeAreaProvider>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  chat: { flex: 1 },
  title: {
    color: tokens.color.fg1,
    fontWeight: '700',
    fontSize: 15,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  list: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: tokens.spacing.lg },
  hint: { color: tokens.color.fg2, textAlign: 'center' }
})
