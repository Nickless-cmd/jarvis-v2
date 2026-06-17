import { useState } from 'react'
import { Linking, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { googleLoginResult, googleLoginStart, type GoogleLoginResult } from '../lib/apiClient'
import { DEFAULT_API_BASE_URL } from '../lib/types'
import { useAuth } from '../state/AuthContext'
import { tokens } from '../theme/tokens'

const GOOGLE_LOGIN_APP_ID = 'jarvis-mobile'
const GOOGLE_LOGIN_POLL_ATTEMPTS = 75
const GOOGLE_LOGIN_POLL_MS = 2000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function LoginScreen() {
  const { signInWithToken } = useAuth()
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL)
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [qrMessage, setQrMessage] = useState('')
  const [googleBusy, setGoogleBusy] = useState(false)
  const [googleMessage, setGoogleMessage] = useState('')
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

  const loginWithGoogle = async () => {
    if (googleBusy) return
    setError('')
    setGoogleMessage('Åbner Google...')
    setGoogleBusy(true)

    try {
      const start = await googleLoginStart(apiBaseUrl, GOOGLE_LOGIN_APP_ID)
      if (!start.authorize_url || !start.nonce) {
        setGoogleMessage('Google-login er ikke konfigureret på serveren.')
        return
      }

      await Linking.openURL(start.authorize_url)
      setGoogleMessage('Log ind i browseren - venter...')

      for (let i = 0; i < GOOGLE_LOGIN_POLL_ATTEMPTS; i += 1) {
        const result = await googleLoginResult(apiBaseUrl, start.nonce).catch(
          (): GoogleLoginResult => ({ status: 'pending' })
        )

        if (result.status === 'ok' && result.token) {
          await signInWithToken(apiBaseUrl, result.token)
          setGoogleMessage('')
          return
        }

        if (result.status === 'error') {
          setGoogleMessage(
            result.error === 'no_account'
              ? 'Ingen Jarvis-konto er knyttet til denne Google-konto.'
              : 'Google-login mislykkedes.'
          )
          return
        }

        await sleep(GOOGLE_LOGIN_POLL_MS)
      }

      setGoogleMessage('Timeout - prøv igen.')
    } catch {
      setGoogleMessage('Kunne ikke nå serveren.')
    } finally {
      setGoogleBusy(false)
    }
  }

  return (
    <View style={styles.root}>
      <Text style={styles.title}>Jarvis</Text>
      <Text style={styles.subtitle}>Mobile companion</Text>
      <Pressable
        accessibilityRole="button"
        disabled={googleBusy}
        onPress={loginWithGoogle}
        style={[styles.googleButton, googleBusy ? styles.buttonDisabled : null]}
      >
        <Text style={styles.googleButtonText}>
          {googleBusy ? 'Forbinder...' : 'Log ind med Google'}
        </Text>
      </Pressable>
      {googleMessage ? <Text style={styles.googleMessage}>{googleMessage}</Text> : null}
      <Text style={styles.divider}>eller med token</Text>
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
  buttonDisabled: {
    opacity: 0.6
  },
  googleButton: {
    backgroundColor: '#ffffff',
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md,
    alignItems: 'center',
    marginBottom: tokens.spacing.sm
  },
  googleButtonText: {
    color: '#1f1f1f',
    fontWeight: '700'
  },
  googleMessage: {
    color: tokens.color.fg3,
    textAlign: 'center',
    marginBottom: tokens.spacing.md
  },
  divider: {
    color: tokens.color.fg3,
    textAlign: 'center',
    marginBottom: tokens.spacing.md
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
