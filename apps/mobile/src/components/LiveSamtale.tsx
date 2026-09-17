import { useEffect, useRef, useState } from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { requestRecordingPermissionsAsync } from 'expo-audio'
import { AndroidAudioTypePresets, AudioSession } from '@livekit/react-native'
import { Room, RoomEvent, type Participant } from 'livekit-client'
import { apiFetch } from '../lib/apiClient'
import type { ApiConfig } from '../lib/types'
import { useStyles, type Theme } from '../theme/ThemeContext'

/**
 * Ægte stemme-samtale med Jarvis — som et telefonopkald.
 *
 * Bjørn 17/9-2026: «det skal være ægte tale og naturlig afbrydelser.. som en
 * samtale med et menneske». Den gamle samtaletilstand lyttede efter LYDSTYRKE
 * på en ekstra mikrofon; man måtte trykke på orben for at afbryde.
 *
 * Her er mikrofonen åben hele opkaldet, og lyden går over WebRTC med
 * ekko-dæmpning på selve signalet. Afbrydelsen sker på serveren
 * (apps/voice_agent): taler han mens Jarvis taler, tier Jarvis. Ingen knap.
 *
 * Skærmen gør kun tre ting: åbner opkaldet, viser hvem der har ordet, og
 * lægger på.
 */
type Tilstand = 'forbinder' | 'lytter' | 'taenker' | 'taler' | 'fejl'

const TEKST: Record<Tilstand, string> = {
  forbinder: 'Forbinder…',
  lytter: 'Jarvis lytter',
  taenker: 'Jarvis tænker',
  taler: 'Jarvis taler — bare afbryd',
  fejl: 'Kunne ikke forbinde'
}

export function LiveSamtale({ config, sessionId, aaben, onLuk }: {
  config: ApiConfig | null
  sessionId: string | null
  aaben: boolean
  onLuk: () => void
}) {
  const styles = useStyles(makeStyles)
  const [tilstand, setTilstand] = useState<Tilstand>('forbinder')
  const [fejl, setFejl] = useState('')
  const rumRef = useRef<Room | null>(null)

  useEffect(() => {
    if (!aaben || !config) return
    let annulleret = false
    const rum = new Room({ adaptiveStream: false, dynacast: false })
    rumRef.current = rum

    // LiveKit-agenten udgiver sin tilstand som deltager-attribut.
    const opdater = (_: unknown, p?: Participant) => {
      const agent = p ?? [...rum.remoteParticipants.values()].find((x) => x.attributes?.['lk.agent.state'])
      const s = agent?.attributes?.['lk.agent.state']
      if (s === 'speaking') setTilstand('taler')
      else if (s === 'thinking') setTilstand('taenker')
      else if (s === 'listening' || s === 'initializing') setTilstand('lytter')
    }
    rum.on(RoomEvent.ParticipantAttributesChanged, (_c, p) => opdater(undefined, p as Participant))
    rum.on(RoomEvent.ParticipantConnected, () => opdater(undefined))
    rum.on(RoomEvent.Disconnected, () => { if (!annulleret) onLuk() })

    void (async () => {
      try {
        setTilstand('forbinder')
        setFejl('')
        const tilladelse = await requestRecordingPermissionsAsync()
        if (!tilladelse.granted) throw new Error('Mikrofon-tilladelse mangler')
        const billet = await apiFetch<{ url: string; token: string }>(config, '/voice/samtale', {
          method: 'POST',
          body: { session_id: sessionId ?? '' }
        })
        await AudioSession.configureAudio({
          android: {
            preferredOutputList: ['speaker'],
            audioTypeOptions: AndroidAudioTypePresets.communication
          }
        })
        await AudioSession.startAudioSession()
        if (annulleret) return
        await rum.connect(billet.url, billet.token, { autoSubscribe: true })
        await rum.localParticipant.setMicrophoneEnabled(true, {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        })
        if (!annulleret) setTilstand('lytter')
      } catch (e) {
        if (annulleret) return
        setFejl(e instanceof Error ? e.message : String(e))
        setTilstand('fejl')
      }
    })()

    return () => {
      annulleret = true
      rumRef.current = null
      void rum.disconnect()
      void AudioSession.stopAudioSession()
    }
  }, [aaben, config, sessionId])

  return (
    <Modal visible={aaben} animationType="fade" onRequestClose={onLuk}>
      <View style={styles.flade}>
        <View style={[styles.cirkel, tilstand === 'taler' && styles.cirkelTaler, tilstand === 'taenker' && styles.cirkelTaenker]} />
        <Text style={styles.status} testID="live-samtale-status">{TEKST[tilstand]}</Text>
        {fejl ? <Text style={styles.fejl}>{fejl}</Text> : null}
        <Pressable accessibilityRole="button" style={styles.laegPaa} onPress={onLuk}>
          <Text style={styles.laegPaaTekst}>Læg på</Text>
        </Pressable>
      </View>
    </Modal>
  )
}

const makeStyles = (t: Theme) => StyleSheet.create({
  flade: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: t.color.bg0, gap: 28 },
  cirkel: { width: 160, height: 160, borderRadius: 80, backgroundColor: t.color.accent, opacity: 0.35 },
  cirkelTaler: { opacity: 0.9 },
  cirkelTaenker: { opacity: 0.6 },
  status: { color: t.color.fg1, fontSize: 20 },
  fejl: { color: t.color.fg2, fontSize: 14, paddingHorizontal: 32, textAlign: 'center' },
  laegPaa: { marginTop: 24, paddingHorizontal: 36, paddingVertical: 14, borderRadius: 28, backgroundColor: '#c0392b' },
  laegPaaTekst: { color: '#fff', fontSize: 17, fontWeight: '600' }
})
