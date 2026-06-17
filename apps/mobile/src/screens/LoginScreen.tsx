import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { DEFAULT_API_BASE_URL } from '../lib/types'
import { useAuth } from '../state/AuthContext'
import { tokens } from '../theme/tokens'

export function LoginScreen() {
  const { signInWithToken } = useAuth()
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL)
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [qrMessage, setQrMessage] = useState('')
  const qrEnabled = process.env.EXPO_PUBLIC_ENABLE_QR_PAIRING === '1'

  const submit = async () => {
    setError('')

    try {
      await signInWithToken(apiBaseUrl, token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke gemme token')
    }
  }

  const startQrPairing = () => {
    setQrMessage(
      qrEnabled
        ? 'QR pairing kræver stadig en kortlivet pairing exchange i Jarvis API.'
        : 'QR pairing er ikke aktiv endnu. Brug bearer token for nu.'
    )
  }

  return (
    <View style={styles.root}>
      <Text style={styles.title}>Jarvis</Text>
      <Text style={styles.subtitle}>Mobile companion</Text>
      <Text style={styles.label}>API</Text>
      <TextInput
        autoCapitalize="none"
        onChangeText={setApiBaseUrl}
        style={styles.input}
        value={apiBaseUrl}
      />
      <Text style={styles.label}>Bearer token</Text>
      <TextInput
        autoCapitalize="none"
        onChangeText={setToken}
        secureTextEntry
        style={styles.input}
        value={token}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Pressable accessibilityRole="button" onPress={submit} style={styles.button}>
        <Text style={styles.buttonText}>Forbind</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        onPress={startQrPairing}
        style={[styles.secondary, qrEnabled ? null : styles.secondaryDisabled]}
      >
        <Text style={styles.secondaryText}>Scan QR fra Jarvis-desk</Text>
      </Pressable>
      {qrMessage ? <Text style={styles.qrMessage}>{qrMessage}</Text> : null}
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    justifyContent: 'center',
    padding: tokens.spacing.xl,
    backgroundColor: tokens.color.bg0
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 34,
    fontWeight: '700',
    marginBottom: tokens.spacing.sm
  },
  subtitle: {
    color: tokens.color.fg2,
    fontSize: 16,
    marginBottom: tokens.spacing.xl
  },
  label: {
    color: tokens.color.fg2,
    marginBottom: tokens.spacing.xs
  },
  input: {
    color: tokens.color.fg1,
    backgroundColor: tokens.color.bg1,
    borderColor: tokens.color.line,
    borderWidth: 1,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md,
    marginBottom: tokens.spacing.md
  },
  error: {
    color: tokens.color.error,
    marginBottom: tokens.spacing.md
  },
  button: {
    backgroundColor: tokens.color.accent,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md,
    alignItems: 'center'
  },
  buttonText: {
    color: tokens.color.bg0,
    fontWeight: '700'
  },
  secondary: {
    marginTop: tokens.spacing.md,
    padding: tokens.spacing.md,
    alignItems: 'center'
  },
  secondaryDisabled: {
    opacity: 0.45
  },
  secondaryText: {
    color: tokens.color.fg2
  },
  qrMessage: {
    color: tokens.color.fg3,
    textAlign: 'center'
  }
})
