import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-native-markdown-display'
import MarkdownIt from 'markdown-it'
import * as Clipboard from 'expo-clipboard'
import * as Speech from 'expo-speech'
import { Animated, Platform, Pressable, StyleSheet, Text, View } from 'react-native'
import { formatRelativeTime } from '../lib/relativeDate'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'

// breaks:true → enkelt \n bliver et linjeskift (Jarvis emitterer inkonsistente
// newlines; uden dette kollapser markdown dem til mellemrum = én lang smøre).
const markdownItInstance = MarkdownIt({ typographer: true, linkify: true, breaks: true })

const MONO = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' })

export function MessageBubble({
  message,
  onResend
}: {
  message: ChatMessage
  onResend?: (text: string) => void
}) {
  const isUser = message.role === 'user'
  const [speaking, setSpeaking] = useState(false)
  const [copied, setCopied] = useState(false)
  const streaming = message.id.startsWith('stream-')

  // Blød spring-ind ved mount (§3.3): scale 0.96→1 + opacity 0→1.
  const enter = useRef(new Animated.Value(0)).current
  useEffect(() => {
    Animated.spring(enter, { toValue: 1, useNativeDriver: true, speed: 16, bounciness: 6 }).start()
  }, [enter])
  const enterScale = enter.interpolate({ inputRange: [0, 1], outputRange: [0.96, 1] })

  const copy = async () => {
    await Clipboard.setStringAsync(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const readAloud = () => {
    if (speaking) {
      Speech.stop()
      setSpeaking(false)
      return
    }
    setSpeaking(true)
    Speech.speak(message.content, {
      language: 'da-DK',
      onDone: () => setSpeaking(false),
      onStopped: () => setSpeaking(false),
      onError: () => setSpeaking(false)
    })
  }

  return (
    <Animated.View
      style={[
        styles.root,
        isUser ? styles.user : styles.assistant,
        { opacity: enter, transform: [{ scale: enterScale }] }
      ]}
    >
      {isUser ? (
        <Text style={styles.userText}>{message.content}</Text>
      ) : (
        <Markdown markdownit={markdownItInstance} style={markdownStyles}>
          {message.content}
        </Markdown>
      )}

      {/* Tidsstempel + handlinger — skjult under live-streaming (intet at kopiere endnu). */}
      {!streaming ? (
        <View style={styles.meta}>
          <Text style={styles.time}>{formatRelativeTime(message.created_at, new Date())}</Text>
          <View style={styles.actions}>
            <Pressable accessibilityLabel="Kopiér" hitSlop={8} onPress={copy}>
              <Text style={styles.action}>{copied ? '✓ kopieret' : 'Kopiér'}</Text>
            </Pressable>
            {!isUser ? (
              <Pressable accessibilityLabel="Læs op" hitSlop={8} onPress={readAloud}>
                <Text style={styles.action}>{speaking ? '■ stop' : '🔊 Læs op'}</Text>
              </Pressable>
            ) : null}
            {isUser && onResend ? (
              <Pressable accessibilityLabel="Send igen" hitSlop={8} onPress={() => onResend(message.content)}>
                <Text style={styles.action}>↻ Send igen</Text>
              </Pressable>
            ) : null}
          </View>
        </View>
      ) : null}
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  root: {
    marginHorizontal: tokens.spacing.md,
    marginVertical: tokens.spacing.xs,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.md
  },
  assistant: { marginRight: 40, backgroundColor: tokens.color.depth2 },
  user: {
    marginLeft: 40,
    backgroundColor: tokens.color.glassFill,
    borderWidth: 1,
    borderColor: tokens.color.glassLine,
    borderRadius: tokens.radius.lg
  },
  userText: { color: tokens.color.fg1, fontSize: 16, lineHeight: 23 },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: tokens.spacing.xs,
    gap: tokens.spacing.sm
  },
  time: { color: tokens.color.fg3, fontSize: 11 },
  actions: { flexDirection: 'row', gap: tokens.spacing.md },
  action: { color: tokens.color.fg2, fontSize: 12, fontWeight: '600' }
})

// Fuld mørk-tema markdown-styling. Uden dette defaulter kode-blokke til lys
// baggrund (= hvid boks med næsten-hvid tekst) og afsnit klistrer sammen.
const markdownStyles = StyleSheet.create({
  body: { color: tokens.color.fg1, fontSize: 16, lineHeight: 23 },
  paragraph: { marginTop: 0, marginBottom: tokens.spacing.sm },
  text: { color: tokens.color.fg1 },
  strong: { color: tokens.color.fg1, fontWeight: '700' },
  em: { fontStyle: 'italic' },
  link: { color: tokens.color.accent, textDecorationLine: 'underline' },
  heading1: { color: tokens.color.fg1, fontSize: 22, fontWeight: '700', marginTop: tokens.spacing.sm, marginBottom: tokens.spacing.xs },
  heading2: { color: tokens.color.fg1, fontSize: 19, fontWeight: '700', marginTop: tokens.spacing.sm, marginBottom: tokens.spacing.xs },
  heading3: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700', marginTop: tokens.spacing.sm, marginBottom: tokens.spacing.xs },
  bullet_list: { marginBottom: tokens.spacing.sm },
  ordered_list: { marginBottom: tokens.spacing.sm },
  list_item: { marginBottom: tokens.spacing.xs },
  bullet_list_icon: { color: tokens.color.accent },
  ordered_list_icon: { color: tokens.color.accent },
  code_inline: {
    backgroundColor: tokens.color.codeBg,
    color: tokens.color.accent,
    fontFamily: MONO,
    fontSize: 14,
    borderRadius: tokens.radius.sm,
    paddingHorizontal: 4,
    paddingVertical: 1
  },
  code_block: {
    backgroundColor: tokens.color.codeBg,
    color: tokens.color.fg1,
    fontFamily: MONO,
    fontSize: 14,
    borderRadius: tokens.radius.md,
    borderColor: tokens.color.line,
    borderWidth: 1,
    padding: tokens.spacing.md,
    marginBottom: tokens.spacing.sm
  },
  fence: {
    backgroundColor: tokens.color.codeBg,
    color: tokens.color.fg1,
    fontFamily: MONO,
    fontSize: 14,
    borderRadius: tokens.radius.md,
    borderColor: tokens.color.line,
    borderWidth: 1,
    padding: tokens.spacing.md,
    marginBottom: tokens.spacing.sm
  },
  blockquote: {
    backgroundColor: tokens.color.bg2,
    borderLeftColor: tokens.color.accent,
    borderLeftWidth: 3,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    marginBottom: tokens.spacing.sm
  },
  hr: { backgroundColor: tokens.color.line, height: 1, marginVertical: tokens.spacing.sm },
  table: { borderColor: tokens.color.line, borderWidth: 1, borderRadius: tokens.radius.sm, marginBottom: tokens.spacing.sm },
  thead: { backgroundColor: tokens.color.bg2 },
  th: { color: tokens.color.fg1, padding: tokens.spacing.xs, fontWeight: '700' },
  td: { color: tokens.color.fg1, padding: tokens.spacing.xs },
  tr: { borderColor: tokens.color.line, borderBottomWidth: 1 }
})
