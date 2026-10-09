import { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View, useWindowDimensions } from 'react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import type { PauseAsk } from '../lib/pauseAsk'

export function PauseAndAskCard({ ask, onAnswer }: { ask: PauseAsk; onAnswer: (answer: string) => void | Promise<void> }) {
  const theme = useTheme()
  const styles = useStyles(makeStyles)
  const { height } = useWindowDimensions()
  const [selected, setSelected] = useState<string[]>([])
  const [ownAnswer, setOwnAnswer] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const identity = JSON.stringify([ask.question, ask.options, ask.allowMultiple])

  useEffect(() => {
    setSelected([])
    setOwnAnswer('')
    setSubmitted(false)
    setError('')
  }, [identity])

  const select = (option: string) => {
    if (submitted) return
    setSelected((current) => ask.allowMultiple
      ? current.includes(option) ? current.filter((item) => item !== option) : [...current, option]
      : [option])
  }

  const send = async () => {
    if (submitted) return
    const own = ownAnswer.trim()
    const answer = own || (ask.allowMultiple
      ? selected.length ? `Jeg vælger:\n${ask.options.filter((o) => selected.includes(o)).map((o) => `- ${o}`).join('\n')}` : ''
      : selected[0] || '')
    if (!answer) return
    setSubmitted(true)
    setError('')
    try {
      await onAnswer(answer)
    } catch {
      setSubmitted(false)
      setError('Svaret kunne ikke sendes. Prøv igen.')
    }
  }

  return (
    <ScrollView style={{ maxHeight: Math.min(420, height * 0.46) }} keyboardShouldPersistTaps="always">
    <View style={styles.card} accessibilityLabel="Spørgsmål fra Jarvis">
      <View style={styles.head}>
        <View style={[styles.dot, { backgroundColor: ask.urgency === 'high' ? theme.color.warn : theme.color.accent }]} />
        <Text style={styles.status}>JARVIS VENTER PÅ DIG</Text>
      </View>
      <Text style={styles.question}>{ask.question}</Text>
      {ask.context ? <Text style={styles.context}>{ask.context}</Text> : null}
      {ask.options.map((option, index) => {
        const checked = selected.includes(option)
        return (
          <Pressable key={option} accessibilityRole="button" accessibilityState={{ selected: checked, disabled: submitted }}
            onPress={() => select(option)} disabled={submitted}
            style={[styles.option, index > 0 && styles.divider]}>
            {ask.allowMultiple ? (
              <View testID="pauseask-circle" style={[styles.circle, checked && styles.circleSelected]}>
                {checked ? <View style={styles.circleDot} /> : null}
              </View>
            ) : null}
            <Text style={[styles.optionText, checked && styles.optionSelected]}>{option}</Text>
          </Pressable>
        )
      })}
      <Text style={styles.ownLabel}>Skriv dit eget svar</Text>
      <TextInput accessibilityLabel="Skriv dit eget svar" value={ownAnswer} onChangeText={setOwnAnswer}
        editable={!submitted} placeholder="Dit svar…" placeholderTextColor={theme.color.fg3}
        style={styles.input} />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" onPress={() => { void send() }}
          disabled={submitted || (!ownAnswer.trim() && selected.length === 0)}
          style={[styles.send, (submitted || (!ownAnswer.trim() && selected.length === 0)) && styles.sendDisabled]}>
          <Text style={styles.sendText}>{submitted ? 'Sender…' : 'Send svar'}</Text>
        </Pressable>
      </View>
    </View>
    </ScrollView>
  )
}

const makeStyles = (theme: Theme) => StyleSheet.create({
  card: { backgroundColor: theme.color.bg2, borderRadius: theme.radius.lg, padding: theme.spacing.lg, gap: 0 },
  head: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 13 },
  dot: { width: 7, height: 7, borderRadius: 4 },
  status: { color: theme.color.accentText, fontSize: 11, fontWeight: '700', letterSpacing: 1 },
  question: { color: theme.color.fg1, fontSize: 16, fontWeight: '600', lineHeight: 23 },
  context: { color: theme.color.fg2, fontSize: 13, lineHeight: 19, marginTop: 5 },
  option: { flexDirection: 'row', alignItems: 'center', minHeight: 46, gap: 11, paddingVertical: 10 },
  divider: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: theme.color.line },
  circle: { width: 18, height: 18, borderRadius: 9, borderWidth: 1, borderColor: theme.color.fg3, alignItems: 'center', justifyContent: 'center' },
  circleSelected: { borderColor: theme.color.accent },
  circleDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: theme.color.accent },
  optionText: { color: theme.color.fg1, fontSize: 14, flex: 1 },
  optionSelected: { color: theme.color.accentText },
  ownLabel: { color: theme.color.fg2, fontSize: 12, marginTop: 12, marginBottom: 6 },
  input: { color: theme.color.fg1, backgroundColor: theme.color.bg3, borderRadius: theme.radius.md, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16 },
  actions: { alignItems: 'flex-end', marginTop: 12 },
  send: { backgroundColor: theme.color.accent, borderRadius: theme.radius.md, paddingHorizontal: 16, paddingVertical: 10 },
  sendDisabled: { opacity: 0.45 },
  sendText: { color: theme.color.onAccent, fontWeight: '700', fontSize: 14 },
  error: { color: theme.color.error, fontSize: 12, marginTop: 7 }
})
