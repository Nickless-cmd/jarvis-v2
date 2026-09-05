import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { Code2, MessagesSquare } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export type NewWorkMode = 'code' | 'cowork'

export interface NewWorkTaskDraft {
  instruction: string
  project: string
  branch: string
  mode: NewWorkMode
}

export function buildNewWorkTaskPrompt(draft: NewWorkTaskDraft): string {
  const lines = [
    'Start this as a mobile-created Jarvis Work task.',
    `Mode: ${draft.mode}`,
    draft.project.trim() ? `Project: ${draft.project.trim()}` : '',
    draft.branch.trim() ? `Branch: ${draft.branch.trim()}` : '',
    '',
    draft.instruction.trim()
  ].filter((line) => line !== '')
  return lines.join('\n')
}

export function NewWorkTaskSheet({
  busy,
  onSubmit
}: {
  busy?: boolean
  onSubmit: (next: { prompt: string; mode: NewWorkMode }) => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [mode, setMode] = useState<NewWorkMode>('code')
  const [project, setProject] = useState('')
  const [branch, setBranch] = useState('')
  const [instruction, setInstruction] = useState('')
  const canSubmit = instruction.trim().length > 0 && !busy

  const submit = () => {
    if (!canSubmit) return
    onSubmit({
      mode,
      prompt: buildNewWorkTaskPrompt({ instruction, project, branch, mode })
    })
    setInstruction('')
  }

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Ny opgave</Text>
      <View style={styles.modeRow}>
        <Pressable
          accessibilityRole="button"
          onPress={() => setMode('code')}
          style={[styles.mode, mode === 'code' && styles.modeOn]}
        >
          <Code2 size={15} color={mode === 'code' ? tokens.color.bg0 : tokens.color.fg2} strokeWidth={2} />
          <Text style={[styles.modeText, mode === 'code' && styles.modeTextOn]}>Code</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={() => setMode('cowork')}
          style={[styles.mode, mode === 'cowork' && styles.modeOn]}
        >
          <MessagesSquare size={15} color={mode === 'cowork' ? tokens.color.bg0 : tokens.color.fg2} strokeWidth={2} />
          <Text style={[styles.modeText, mode === 'cowork' && styles.modeTextOn]}>Cowork</Text>
        </Pressable>
      </View>
      <TextInput
        testID="new-work-project"
        value={project}
        onChangeText={setProject}
        placeholder="Projektsti"
        placeholderTextColor={tokens.color.fg3}
        autoCapitalize="none"
        style={styles.input}
      />
      <TextInput
        testID="new-work-branch"
        value={branch}
        onChangeText={setBranch}
        placeholder="Branch"
        placeholderTextColor={tokens.color.fg3}
        autoCapitalize="none"
        style={styles.input}
      />
      <TextInput
        testID="new-work-instruction"
        value={instruction}
        onChangeText={setInstruction}
        placeholder="Hvad skal Jarvis arbejde på?"
        placeholderTextColor={tokens.color.fg3}
        multiline
        style={[styles.input, styles.textarea]}
      />
      <Pressable
        testID="new-work-submit"
        accessibilityRole="button"
        accessibilityState={{ disabled: !canSubmit }}
        disabled={!canSubmit}
        onPress={submit}
        style={[styles.submit, !canSubmit && styles.submitOff]}
      >
        <Text style={styles.submitText}>{busy ? 'Starter…' : 'Start opgave'}</Text>
      </Pressable>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.line,
    padding: tokens.spacing.lg,
    gap: tokens.spacing.md
  },
  title: { color: tokens.color.fg1, fontSize: 17, fontWeight: '700' },
  modeRow: { flexDirection: 'row', gap: tokens.spacing.sm },
  mode: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    flex: 1,
    minHeight: 40,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg2
  },
  modeOn: { backgroundColor: tokens.color.accent },
  modeText: { color: tokens.color.fg2, fontWeight: '700' },
  modeTextOn: { color: tokens.color.bg0 },
  input: {
    color: tokens.color.fg1,
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    fontSize: 15
  },
  textarea: { minHeight: 110, textAlignVertical: 'top' },
  submit: {
    minHeight: 46,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.accent
  },
  submitOff: { opacity: 0.45 },
  submitText: { color: tokens.color.bg0, fontWeight: '700' }
})
