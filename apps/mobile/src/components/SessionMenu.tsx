import { useState } from 'react'
import { Alert, Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { Archive, ArchiveRestore, Pen, Pin, PinOff, Trash2 } from 'lucide-react-native'
import type { ChatSession } from '../lib/types'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Handlingerne på én samtale — fastgør, arkivér, omdøb, slet.
 *
 * ## Hvorfor de fire ser forskellige ud
 *
 * Tre af dem kan fortrydes ved at gøre det modsatte. Sletning kan ikke, og
 * derfor er den den eneste der spørger, og den eneste der står i advarselsfarve
 * nederst med en linje over sig. Det er ikke pynt: en menu hvor alt ser ens ud
 * inviterer til at ramme det forkerte, og prisen for de fire er ikke ens.
 *
 * ## Fastgør og arkivér er én kontakt hver, ikke to
 *
 * Menuen viser «Fastgør» eller «Frigør» efter hvad samtalen er nu — ikke begge.
 * Serveren afviser i forvejen at have dem samtidig (arkivering frigør
 * fastgørelsen), og en menu der tilbyder en tilstand man allerede er i, får
 * folk til at tro at der skete noget.
 */
export function SessionMenu({
  session, open, onClose, onRename, onDelete, onSetFlags,
}: {
  session: ChatSession | null
  open: boolean
  onClose: () => void
  onRename: (id: string, titel: string) => void
  onDelete: (id: string) => void
  onSetFlags: (id: string, flags: { pinned?: boolean; archived?: boolean }) => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [omdoeber, setOmdoeber] = useState(false)
  const [udkast, setUdkast] = useState('')

  if (!session) return null
  const luk = () => { setOmdoeber(false); onClose() }

  return (
    <Modal transparent visible={open} animationType="slide" onRequestClose={luk}>
      <Pressable style={styles.scrim} onPress={luk}>
        <Pressable style={styles.ark} onPress={(e) => e.stopPropagation()}>
          <View style={styles.greb} />
          <Text style={styles.titel} numberOfLines={1}>
            {session.title || 'Ny samtale'}
          </Text>

          {omdoeber ? (
            <View style={styles.omdoeb}>
              <TextInput
                autoFocus
                testID="session-rename-input"
                value={udkast}
                onChangeText={setUdkast}
                placeholder="Nyt navn"
                placeholderTextColor={tokens.color.fg3}
                style={styles.felt}
                onSubmitEditing={() => {
                  const t = udkast.trim()
                  if (t) onRename(session.id, t)
                  luk()
                }}
              />
              <Pressable
                testID="session-rename-gem"
                accessibilityRole="button"
                accessibilityLabel="Gem navn"
                // Tomt navn gemmes IKKE. En samtale uden titel er svaerere at
                // finde igen end en med et daarligt navn.
                disabled={!udkast.trim()}
                onPress={() => { onRename(session.id, udkast.trim()); luk() }}
                style={[styles.gem, !udkast.trim() ? styles.gemDoed : null]}
              >
                <Text style={styles.gemTekst}>Gem</Text>
              </Pressable>
            </View>
          ) : (
            <>
              <Valg
                testID="session-pin"
                ikon={session.pinned
                  ? <PinOff size={18} color={tokens.color.fg2} strokeWidth={1.8} />
                  : <Pin size={18} color={tokens.color.fg2} strokeWidth={1.8} />}
                navn={session.pinned ? 'Frigør' : 'Fastgør øverst'}
                onPress={() => { onSetFlags(session.id, { pinned: !session.pinned }); luk() }}
              />
              <Valg
                testID="session-archive"
                ikon={session.archived
                  ? <ArchiveRestore size={18} color={tokens.color.fg2} strokeWidth={1.8} />
                  : <Archive size={18} color={tokens.color.fg2} strokeWidth={1.8} />}
                navn={session.archived ? 'Hent ud af arkiv' : 'Arkivér'}
                onPress={() => { onSetFlags(session.id, { archived: !session.archived }); luk() }}
              />
              <Valg
                testID="session-rename"
                ikon={<Pen size={18} color={tokens.color.fg2} strokeWidth={1.8} />}
                navn="Omdøb"
                onPress={() => { setUdkast(session.title || ''); setOmdoeber(true) }}
              />
              <Valg
                testID="session-delete"
                farlig
                ikon={<Trash2 size={18} color={tokens.color.warn} strokeWidth={1.8} />}
                navn="Slet samtale"
                onPress={() => {
                  // DEN ENESTE der spoerger. De tre andre kan fortrydes ved at
                  // goere det modsatte; denne kan ikke.
                  Alert.alert(
                    'Slet samtale?',
                    `«${session.title || 'Ny samtale'}» og alle dens beskeder slettes. Det kan ikke fortrydes.`,
                    [
                      { text: 'Behold', style: 'cancel' },
                      {
                        text: 'Slet', style: 'destructive',
                        onPress: () => { onDelete(session.id); luk() },
                      },
                    ],
                  )
                }}
              />
            </>
          )}
        </Pressable>
      </Pressable>
    </Modal>
  )
}

function Valg({
  ikon, navn, onPress, testID, farlig,
}: { ikon: React.ReactNode; navn: string; onPress: () => void; testID?: string; farlig?: boolean }) {
  const styles = useStyles(makestyles)
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={navn}
      onPress={onPress}
      style={({ pressed }) => [styles.valg, farlig ? styles.valgFarlig : null, pressed ? styles.trykket : null]}
    >
      {ikon}
      <Text style={[styles.valgTekst, farlig ? styles.valgTekstFarlig : null]}>{navn}</Text>
    </Pressable>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  ark: {
    backgroundColor: tokens.color.bg1,
    borderTopLeftRadius: 18, borderTopRightRadius: 18,
    paddingBottom: 28, paddingTop: 8, paddingHorizontal: tokens.spacing.sm,
  },
  greb: {
    alignSelf: 'center', width: 36, height: 4, borderRadius: 2,
    backgroundColor: tokens.color.bg2, marginBottom: 10,
  },
  titel: {
    color: tokens.color.fg2, fontSize: 12,
    paddingHorizontal: tokens.spacing.sm, paddingBottom: 8,
  },
  valg: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    paddingVertical: 13, paddingHorizontal: tokens.spacing.sm, borderRadius: 10,
  },
  valgFarlig: {
    marginTop: 6, borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: tokens.color.bg2, borderRadius: 0, paddingTop: 15,
  },
  valgTekst: { color: tokens.color.fg1, fontSize: 15 },
  valgTekstFarlig: { color: tokens.color.warn },
  trykket: { opacity: 0.6 },
  omdoeb: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm, paddingVertical: 8 },
  felt: {
    flex: 1, color: tokens.color.fg1, fontSize: 15,
    backgroundColor: tokens.color.bg2, borderRadius: 10,
    paddingHorizontal: 12, paddingVertical: 10,
  },
  gem: {
    backgroundColor: tokens.color.accent, borderRadius: 10,
    paddingHorizontal: 16, paddingVertical: 11,
  },
  gemDoed: { opacity: 0.4 },
  gemTekst: { color: tokens.color.bg0, fontSize: 14, fontWeight: '600' },
})
