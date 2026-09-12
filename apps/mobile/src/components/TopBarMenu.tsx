import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { ArrowLeftRight, Minimize2, RefreshCw } from 'lucide-react-native'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Menuen bag de tre prikker i headerens højre felt.
 *
 * ## Hvorfor opdatér flyttede herind
 *
 * Den sad som sit eget ikon øverst til højre og var appens mest fremtrædende
 * knap — men den er også den man trykker sjældnest. Bjørn bad om at bytte:
 * «refresh ikonet laves om til en 3-prikket menu og refresh flyttes ind
 * under den». En knap får plads efter hvor tit den bruges, ikke efter hvor
 * tidligt den blev bygget.
 *
 * ## Hvorfor komprimér står her og ikke ved ringen
 *
 * Ringen ved siden af siger at samtalen nærmer sig en komprimering. Det er
 * den ENESTE handling den advarsel inviterer til — en advarsel uden en
 * udvej er bare uro. Men den skal heller ikke kunne rammes ved et uheld,
 * så den ligger et tryk inde.
 */
export function TopBarMenu({
  aaben, onClose, onSync, onCompact, onTilbageTilChat, kodeTilstand,
}: {
  aaben: boolean
  onClose: () => void
  onSync: () => void
  onCompact?: () => void
  onTilbageTilChat?: () => void
  kodeTilstand?: boolean
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <Modal transparent visible={aaben} animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose}>
        <Pressable style={styles.ark} onPress={(e) => e.stopPropagation()}>
          <Punkt
            navn="Opdatér"
            ikon={<RefreshCw size={17} color={tokens.color.fg2} strokeWidth={1.9} />}
            onPress={() => { onSync(); onClose() }}
          />
          {onCompact ? (
            <Punkt
              navn="Komprimér kontekst"
              ikon={<Minimize2 size={17} color={tokens.color.fg2} strokeWidth={1.9} />}
              onPress={() => { onCompact(); onClose() }}
            />
          ) : null}
          {kodeTilstand && onTilbageTilChat ? (
            <Punkt
              navn="Tilbage til chat"
              ikon={<ArrowLeftRight size={17} color={tokens.color.fg2} strokeWidth={1.9} />}
              onPress={() => { onTilbageTilChat(); onClose() }}
            />
          ) : null}
        </Pressable>
      </Pressable>
    </Modal>
  )
}

function Punkt({ navn, ikon, onPress }: { navn: string; ikon: React.ReactNode; onPress: () => void }) {
  const styles = useStyles(makestyles)
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={navn}
      onPress={onPress}
      style={({ pressed }) => [styles.punkt, pressed ? styles.trykket : null]}
    >
      {ikon}
      <Text style={styles.punktTekst}>{navn}</Text>
    </Pressable>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  // Menuen lander under det felt den kom fra, ikke midt paa skaermen: oejet
  // skal kunne se hvad der aabnede den.
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.25)', alignItems: 'flex-end', paddingTop: 58, paddingRight: 14 },
  ark: {
    minWidth: 210,
    backgroundColor: tokens.color.bgFloat,
    borderRadius: 14,
    paddingVertical: 6,
    ...tokens.elevation,
  },
  punkt: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    paddingVertical: 12, paddingHorizontal: 14,
  },
  punktTekst: { color: tokens.color.fg1, fontSize: 15 },
  trykket: { opacity: 0.6 },
})
