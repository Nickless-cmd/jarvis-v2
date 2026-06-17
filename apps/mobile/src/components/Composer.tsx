import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { tokens } from '../theme/tokens'

export function Composer({
  disabled,
  working,
  onSend,
  onStop
}: {
  disabled?: boolean
  working?: boolean
  onSend: (text: string) => void | Promise<void>
  onStop: () => void
}) {
  const [text, setText] = useState('')

  const submit = () => {
    const value = text.trim()
    if (!value || disabled || working) return
    onSend(value)
    setText('')
  }

  return (
    <View style={styles.root}>
      <TextInput
        testID="composer-input"
        value={text}
        onChangeText={setText}
        multiline
        editable={!disabled}
        placeholder="Skriv til Jarvis"
        placeholderTextColor={tokens.color.fg3}
        style={styles.input}
      />
      <Pressable
        testID="composer-button"
        accessibilityRole="button"
        disabled={disabled && !working}
        onPress={working ? onStop : submit}
        style={({ pressed }) => [
          styles.button,
          disabled && !working ? styles.buttonDisabled : null,
          pressed ? styles.buttonPressed : null
        ]}
      >
        <Text style={styles.buttonText}>{working ? 'Stop' : 'Send'}</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: tokens.spacing.sm,
    padding: tokens.spacing.md,
    borderTopColor: tokens.color.line,
    borderTopWidth: 1,
    backgroundColor: tokens.color.bg0
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 140,
    color: tokens.color.fg1,
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md
  },
  button: {
    minWidth: 64,
    minHeight: 44,
    borderRadius: tokens.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.accent
  },
  buttonDisabled: {
    opacity: 0.45
  },
  buttonPressed: {
    opacity: 0.85
  },
  buttonText: {
    color: tokens.color.bg0,
    fontWeight: '700'
  }
})
