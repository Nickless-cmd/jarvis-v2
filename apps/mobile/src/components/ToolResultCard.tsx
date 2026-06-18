import { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { parseToolMessage, toolPreview } from '../lib/toolMessage'
import { tokens } from '../theme/tokens'

// Lille glyf pr. værktøjstype — holder det genkendeligt uden ikon-bibliotek.
function glyphFor(tool: string): string {
  const t = tool.toLowerCase()
  if (t.includes('bash') || t.includes('shell') || t.includes('exec')) return '⌘'
  if (t.includes('search') || t.includes('grep') || t.includes('find')) return '🔍'
  if (t.includes('read') || t.includes('file') || t.includes('cat')) return '📄'
  if (t.includes('edit') || t.includes('write')) return '✏️'
  if (t.includes('web') || t.includes('fetch') || t.includes('http')) return '🌐'
  if (t.includes('mail') || t.includes('gmail')) return '✉️'
  if (t.includes('memory') || t.includes('brain') || t.includes('recall')) return '🧠'
  if (t.includes('calendar') || t.includes('event')) return '📅'
  return '🔧'
}

/**
 * Tool-output som foldet kort i stedet for rå "[tool_result:…]"-tekst.
 *
 * To kilder:
 *  - persisteret tool-besked → `content` (parses).
 *  - LIVE tool_use-blok under streaming → `toolName` + `body` + `running`
 *    (renderes med det samme, så aktivitet vises uden app-genstart).
 */
export function ToolResultCard({
  content,
  toolName,
  body: bodyProp,
  running
}: {
  content?: string
  toolName?: string
  body?: string
  running?: boolean
}) {
  const [open, setOpen] = useState(false)
  const parsed = content != null ? parseToolMessage(content) : null
  const tool = toolName ?? parsed?.tool ?? 'tool'
  const body = bodyProp ?? parsed?.body ?? ''

  return (
    <View style={styles.wrap}>
      <Pressable
        accessibilityRole="button"
        onPress={() => setOpen((o) => !o)}
        style={({ pressed }) => [
          styles.card,
          running ? styles.cardRunning : null,
          pressed ? styles.pressed : null
        ]}
      >
        <View style={styles.header}>
          <Text style={styles.glyph}>{glyphFor(tool)}</Text>
          <Text style={styles.tool} numberOfLines={1}>
            {tool}
          </Text>
          {running ? <Text style={styles.running}>● kører…</Text> : null}
          <Text style={styles.chev}>{open ? '▾' : '▸'}</Text>
        </View>
        {body ? (
          <Text style={styles.preview} numberOfLines={open ? undefined : 2}>
            {open ? body : toolPreview(body)}
          </Text>
        ) : null}
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: {
    marginHorizontal: tokens.spacing.md,
    marginVertical: tokens.spacing.xs,
    marginRight: 48
  },
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.lg,
    borderLeftWidth: 2,
    borderLeftColor: tokens.color.accent,
    padding: tokens.spacing.md,
    // dybde — let svævende skygge (spec §4 "kort der folder sig ud")
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2
  },
  cardRunning: { borderLeftColor: tokens.color.warn },
  pressed: { opacity: 0.8 },
  running: { color: tokens.color.warn, fontSize: 11, fontWeight: '700' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    marginBottom: tokens.spacing.xs
  },
  glyph: { fontSize: 14 },
  tool: {
    color: tokens.color.fg1,
    fontWeight: '700',
    fontSize: 13,
    flex: 1
  },
  chev: { color: tokens.color.fg3, fontSize: 12 },
  preview: {
    color: tokens.color.fg2,
    fontSize: 13,
    lineHeight: 19,
    fontFamily: 'monospace'
  }
})
