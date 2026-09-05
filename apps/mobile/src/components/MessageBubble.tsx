import { Check, Copy, MoreHorizontal, RotateCw, Share2, Square, ThumbsDown, ThumbsUp, Volume2 } from 'lucide-react-native'
import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-native-markdown-display'
import MarkdownIt from 'markdown-it'
import * as Clipboard from 'expo-clipboard'
import { readAloud as readAloudText, stopReading } from '../lib/readAloud'
import { useAuthOptional } from '../state/AuthContext'
import { Animated, Platform, Pressable, Share, StyleSheet, Text, View } from 'react-native'
import { CodeBlock } from './CodeBlock'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

// breaks:true → enkelt \n bliver et linjeskift (Jarvis emitterer inkonsistente
// newlines; uden dette kollapser markdown dem til mellemrum = én lang smøre).
const markdownItInstance = MarkdownIt({ typographer: true, linkify: true, breaks: true })

const MONO = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' })
const SOURCE_RE = /https?:\/\/([^\s/)\]]+)/gi

export function sourceDomains(text: string): string[] {
  const seen = new Set<string>()
  for (const match of text.matchAll(SOURCE_RE)) {
    const domain = match[1]?.replace(/^www\./, '').toLowerCase()
    if (domain) seen.add(domain)
  }
  return [...seen].slice(0, 4)
}

export function MessageBubble({
  message,
  onResend,
  onRegenerate,
  hideActions
}: {
  message: ChatMessage
  onResend?: (text: string) => void
  /** Menu-ikonet i handlingsrækken. Uden handler er det blot inaktivt. */
  onRegenerate?: () => void
  /**
   * Skjul handlingsrækken.
   *
   * En tur udfoldes nu i flere afsnit (fortælling → værktøj → fortælling), og
   * uden dette fik HVERT afsnit sin egen kopiér/oplæs-række. ChatGPT viser
   * dem én gang, under turens sidste afsnit — resten er støj.
   */
  hideActions?: boolean
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const markdownStyles = useStyles(makemarkdownStyles)
  const { config } = useAuthOptional()
  const isUser = message.role === 'user'
  const [speaking, setSpeaking] = useState(false)
  const [copied, setCopied] = useState(false)
  // Tommelen er indtil videre KUN lokal markering. Der er ingen feedback-kanal
  // til serveren endnu, og en knap der lader som om den sender noget, er værre
  // end ingen knap. Når kanalen findes, sendes den herfra.
  const [vote, setVote] = useState<'up' | 'down' | null>(null)
  const streaming = message.id.startsWith('stream-')
  const sources = isUser ? [] : sourceDomains(message.content)

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

  // Kodeblokke tegnes af CodeBlock (afrundet flade, syntaksfarver, kopiér-knap)
  // i stedet for markdown-bibliotekets flade <Text>. Reglerne ligger her frem
  // for i `style`, fordi det ikke er en STIL-forskel men en anden komponent.
  const markdownRules = {
    fence: (node: { key: string; content: string; sourceInfo?: string }) => (
      <CodeBlock key={node.key} code={node.content} language={node.sourceInfo} />
    ),
    code_block: (node: { key: string; content: string; sourceInfo?: string }) => (
      <CodeBlock key={node.key} code={node.content} language={node.sourceInfo} />
    )
  }

  const share = async () => {
    try {
      await Share.share({ message: message.content })
    } catch {
      // Brugeren lukkede dele-arket — ikke en fejl.
    }
  }

  const readAloud = () => {
    if (speaking) {
      stopReading()
      setSpeaking(false)
      return
    }
    setSpeaking(true)
    // Jarvis' egen stemme, og på RENSET tekst — ikke rå markdown. Se
    // lib/readAloud.ts for hvorfor telefonens stemme kun er rede.
    void readAloudText(config, message.content, () => setSpeaking(false))
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
        <Markdown markdownit={markdownItInstance} style={markdownStyles} rules={markdownRules}>
          {message.content}
        </Markdown>
      )}

      {sources.length ? (
        <View style={styles.sources}>
          <Text style={styles.sourcesLabel}>Kilder</Text>
          <View style={styles.sourceChips}>
            {sources.map((source) => (
              <Text key={source} style={styles.sourceChip}>{source}</Text>
            ))}
          </View>
        </View>
      ) : null}

      {/* Handlingsrække — KUN ikoner, og kun under assistentens svar.
          Målt i ChatGPT-appen: en vandret række lysegrå omrids-ikoner
          (kopiér, tommel op/ned, oplæsning, del, menu) uden tidsstempel.
          Tidsstemplet er fjernet bevidst: i referencen står der ingenting
          dér, og hver linje man IKKE skriver, er en linje mindre støj. */}
      {!streaming && !isUser && !hideActions ? (
        <View style={styles.actions}>
          <Pressable accessibilityLabel="Kopiér" hitSlop={10} onPress={copy}>
            {copied ? (
              <Check size={ICON} color={tokens.color.fg2} strokeWidth={1.8} />
            ) : (
              <Copy size={ICON} color={tokens.color.fg2} strokeWidth={1.8} />
            )}
          </Pressable>
          <Pressable
            accessibilityLabel="God besvarelse"
            hitSlop={10}
            onPress={() => setVote((v) => (v === 'up' ? null : 'up'))}
          >
            <ThumbsUp
              size={ICON}
              color={vote === 'up' ? tokens.color.accent : tokens.color.fg2}
              strokeWidth={1.8}
            />
          </Pressable>
          <Pressable
            accessibilityLabel="Dårlig besvarelse"
            hitSlop={10}
            onPress={() => setVote((v) => (v === 'down' ? null : 'down'))}
          >
            <ThumbsDown
              size={ICON}
              color={vote === 'down' ? tokens.color.error : tokens.color.fg2}
              strokeWidth={1.8}
            />
          </Pressable>
          <Pressable accessibilityLabel="Læs op" hitSlop={10} onPress={readAloud}>
            {speaking ? (
              <Square size={ICON} color={tokens.color.fg2} strokeWidth={1.8} />
            ) : (
              <Volume2 size={ICON} color={tokens.color.fg2} strokeWidth={1.8} />
            )}
          </Pressable>
          <Pressable accessibilityLabel="Del" hitSlop={10} onPress={share}>
            <Share2 size={ICON} color={tokens.color.fg2} strokeWidth={1.8} />
          </Pressable>
          <Pressable accessibilityLabel="Send igen" hitSlop={10} onPress={() => onRegenerate?.()}>
            <MoreHorizontal size={ICON} color={tokens.color.fg2} strokeWidth={1.8} />
          </Pressable>
        </View>
      ) : null}
      {!streaming && isUser && onResend ? (
        <View style={styles.userActions}>
          <Pressable
            accessibilityLabel="Send igen"
            hitSlop={10}
            onPress={() => onResend(message.content)}
          >
            <RotateCw size={ICON} color={tokens.color.fg2} strokeWidth={1.8} />
          </Pressable>
        </View>
      ) : null}
    </Animated.View>
  )
}

/**
 * Boble-geometrien er målt i ChatGPT-appen på enheden 2026-09-02.
 *
 * Den vigtigste enkeltdetalje: ASSISTENTEN HAR INGEN BOBLE. Svaret står som
 * ren tekst på den sorte flade, venstrejusteret, med luft omkring. Kun
 * brugerens besked får en boble — dyb grøn (#14402F), højrejusteret, fuldt
 * afrundet, og aldrig bredere end ~80 % af skærmen.
 *
 * Det er dét der giver ChatGPT-tråden sin ro: én talende part fylder fladen,
 * den anden markerer sig kort. To bobler over for hinanden ville støje.
 */
/** Handlingsrækkens ikoner. Bjørn bad om et nummer mindre end de målte 19. */
const ICON = 17

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: {
    marginHorizontal: tokens.spacing.lg,
    marginVertical: tokens.spacing.sm,
    paddingHorizontal: 0,
    paddingVertical: 0
  },
  assistant: {
    // Ingen flade, ingen ramme, ingen radius — kun tekst.
    marginRight: 0,
    backgroundColor: 'transparent'
  },
  user: {
    alignSelf: 'flex-end',
    maxWidth: '82%',
    backgroundColor: tokens.color.userBubble,
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.md,
    borderRadius: 26
  },
  userText: { color: tokens.color.fg1, fontSize: 16.5, lineHeight: 24 },
  actions: {
    flexDirection: 'row',
    gap: 26,
    marginTop: tokens.spacing.md
  },
  sources: { marginTop: tokens.spacing.sm, gap: tokens.spacing.xs },
  sourcesLabel: { color: tokens.color.fg3, fontSize: 11, fontWeight: '800', textTransform: 'uppercase' },
  sourceChips: { flexDirection: 'row', flexWrap: 'wrap', gap: tokens.spacing.xs },
  sourceChip: {
    color: tokens.color.accentText,
    fontSize: 12,
    fontWeight: '700',
    backgroundColor: tokens.color.accentGhost,
    borderRadius: tokens.radius.pill,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 4,
    overflow: 'hidden'
  },
  userActions: {
    flexDirection: 'row',
    alignSelf: 'flex-end',
    gap: tokens.spacing.lg,
    marginTop: tokens.spacing.xs
  },
  icon: { color: tokens.color.fg2, fontSize: 18 }

})

// Fuld mørk-tema markdown-styling. Uden dette defaulter kode-blokke til lys
// baggrund (= hvid boks med næsten-hvid tekst) og afsnit klistrer sammen.
const makemarkdownStyles = (tokens: Theme) => StyleSheet.create({
  body: { color: tokens.color.fg1, fontSize: 16.5, lineHeight: 26 },
  paragraph: { marginTop: 0, marginBottom: tokens.spacing.sm },
  text: { color: tokens.color.fg1 },
  strong: { color: tokens.color.fg1, fontWeight: '700' },
  em: { fontStyle: 'italic' },
  link: { color: tokens.color.accentText, textDecorationLine: 'underline' },
  heading1: { color: tokens.color.fg1, fontSize: 22, fontWeight: '700', marginTop: tokens.spacing.sm, marginBottom: tokens.spacing.xs },
  heading2: { color: tokens.color.fg1, fontSize: 19, fontWeight: '700', marginTop: tokens.spacing.sm, marginBottom: tokens.spacing.xs },
  heading3: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700', marginTop: tokens.spacing.sm, marginBottom: tokens.spacing.xs },
  bullet_list: { marginBottom: tokens.spacing.sm },
  ordered_list: { marginBottom: tokens.spacing.sm },
  list_item: { marginBottom: tokens.spacing.xs },
  bullet_list_icon: { color: tokens.color.accentText },
  ordered_list_icon: { color: tokens.color.accentText },
  code_inline: {
    backgroundColor: tokens.color.codeBg,
    color: tokens.color.accentText,
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
