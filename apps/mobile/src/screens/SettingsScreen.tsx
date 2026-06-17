import { useState } from 'react'
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native'
import {
  googleLinkStart,
  googleLoginResult,
  health,
  type GoogleLoginResult
} from '../lib/apiClient'
import { useAuth } from '../state/AuthContext'
import { tokens } from '../theme/tokens'

const GOOGLE_LINK_POLL_ATTEMPTS = 75
const GOOGLE_LINK_POLL_MS = 2000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function SettingsScreen() {
  const { config, signOut } = useAuth()
  const [diagnostic, setDiagnostic] = useState('Ikke testet')
  const [googleBusy, setGoogleBusy] = useState(false)
  const [googleMessage, setGoogleMessage] = useState('')

  const checkApi = async () => {
    if (!config) {
      setDiagnostic('Ikke forbundet')
      return
    }

    try {
      setDiagnostic((await health(config.apiBaseUrl)) ? 'API svarer' : 'API svarer ikke')
    } catch {
      setDiagnostic('Kunne ikke kontakte API')
    }
  }

  const linkGoogle = async () => {
    if (!config || googleBusy) return
    setGoogleBusy(true)
    setGoogleMessage('Åbner Google...')

    try {
      const start = await googleLinkStart(config)
      if (!start.authorize_url || !start.nonce) {
        setGoogleMessage('Google-link er ikke konfigureret på serveren.')
        return
      }

      await Linking.openURL(start.authorize_url)
      setGoogleMessage('Godkend i browseren - venter...')

      for (let i = 0; i < GOOGLE_LINK_POLL_ATTEMPTS; i += 1) {
        const result = await googleLoginResult(config.apiBaseUrl, start.nonce).catch(
          (): GoogleLoginResult => ({ status: 'pending' })
        )

        if (result.status === 'ok') {
          setGoogleMessage('Google-konto forbundet')
          return
        }

        if (result.status === 'error') {
          setGoogleMessage('Kunne ikke forbinde Google-konto.')
          return
        }

        await sleep(GOOGLE_LINK_POLL_MS)
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
      <Text style={styles.heading}>Indstillinger</Text>
      <View style={styles.section}>
        <Text style={styles.label}>API</Text>
        <Text style={styles.value}>{config?.apiBaseUrl ?? 'Ikke forbundet'}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Token</Text>
        <Text style={styles.value}>{config?.authToken ? 'Gemt sikkert' : 'Mangler'}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Google</Text>
        <Text style={styles.value}>Forbind kontoen for Google-login fremover.</Text>
        <Pressable
          accessibilityRole="button"
          disabled={googleBusy}
          onPress={linkGoogle}
          style={[styles.secondaryButton, googleBusy ? styles.buttonDisabled : null]}
        >
          <Text style={styles.secondaryButtonText}>
            {googleBusy ? 'Forbinder...' : 'Forbind Google-konto'}
          </Text>
        </Pressable>
        {googleMessage ? <Text style={styles.message}>{googleMessage}</Text> : null}
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Diagnostik</Text>
        <Text style={styles.value}>{diagnostic}</Text>
        <Pressable accessibilityRole="button" onPress={checkApi} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>Test API</Text>
        </Pressable>
      </View>
      <Pressable accessibilityRole="button" onPress={() => void signOut()} style={styles.signOut}>
        <Text style={styles.signOutText}>Log ud</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0,
    padding: tokens.spacing.md
  },
  heading: {
    color: tokens.color.fg1,
    fontSize: 22,
    fontWeight: '700',
    marginBottom: tokens.spacing.md
  },
  section: {
    paddingVertical: tokens.spacing.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  label: {
    color: tokens.color.fg3,
    marginBottom: tokens.spacing.xs
  },
  value: {
    color: tokens.color.fg1
  },
  signOut: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.color.bg3,
    marginTop: tokens.spacing.xl
  },
  secondaryButton: {
    minHeight: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: tokens.radius.md,
    borderColor: tokens.color.line,
    borderWidth: 1,
    marginTop: tokens.spacing.md
  },
  secondaryButtonText: {
    color: tokens.color.fg1,
    fontWeight: '700'
  },
  buttonDisabled: {
    opacity: 0.6
  },
  message: {
    color: tokens.color.fg3,
    marginTop: tokens.spacing.sm
  },
  signOutText: {
    color: tokens.color.fg1,
    fontWeight: '700'
  }
})
