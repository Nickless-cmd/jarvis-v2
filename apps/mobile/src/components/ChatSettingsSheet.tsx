import { Modal, Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native'
import { Search } from 'lucide-react-native'
import { haptik } from '../lib/haptics'
import type { ChatIndstillinger } from '../lib/chatSettings'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/** Indstillinger for DENNE samtale.
 *
 *  De globale står i Indstillinger. Det her er de valg der hører til én
 *  samtale: hvilken model, hvor mange værktøjer han må bruge, om svar læses
 *  højt, og om han skal spørge før han ændrer noget.
 *
 *  MEMORY SCOPE er ikke med. Serveren har intet felt for det, så en kontakt
 *  her ville se ud som om den begrænsede hvad han husker uden at gøre det.
 *  Det står skrevet i modulet frem for at ligge som en slukket kontakt der
 *  ligner noget der kommer senere.
 */

export interface ChatSettingsSheetProps {
  visible: boolean
  cfg: ChatIndstillinger
  /** Modeller brugeren må vælge. Tom liste → model-valget skjules. */
  modeller?: { model: string; label: string }[]
  onChange: (next: Partial<ChatIndstillinger>) => void
  onClose: () => void
  /** Åbner søgning i den åbne tråd. Udeladt → rækken vises ikke. */
  onSearch?: () => void
}

export function ChatSettingsSheet({
  visible, cfg, modeller = [], onChange, onClose, onSearch,
}: ChatSettingsSheetProps) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)

  const raekke = (
    titel: string, forklaring: string, hoejre: React.ReactNode, testID?: string,
  ) => (
    <View style={styles.row} testID={testID}>
      <View style={styles.rowText}>
        <Text style={styles.rowTitle}>{titel}</Text>
        <Text style={styles.rowHint}>{forklaring}</Text>
      </View>
      {hoejre}
    </View>
  )

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel="Luk" />
      <View style={styles.sheet}>
        <View style={styles.grabber} />
        <Text style={styles.heading}>Denne samtale</Text>
        <ScrollView style={styles.body}>
          {onSearch ? (
            <Pressable
              testID="chatcfg-search"
              accessibilityRole="button"
              accessibilityLabel="Søg i denne samtale"
              onPress={() => { onClose(); onSearch() }}
              style={styles.action}
            >
              <Search size={17} color={tokens.color.fg2} strokeWidth={1.8} />
              <View style={styles.rowText}>
                <Text style={styles.rowTitle}>Søg i denne samtale</Text>
                <Text style={styles.rowHint}>Springer til træffet, så du ser det i sin sammenhæng.</Text>
              </View>
            </Pressable>
          ) : null}
          {modeller.length > 0 && (
            <View testID="chatcfg-models">
              <Text style={styles.rowTitle}>Model</Text>
              <Text style={styles.rowHint}>Tom betyder «som appen plejer».</Text>
              <View style={styles.chips}>
                {[{ model: '', label: 'Som appen' }, ...modeller].map((m) => (
                  <Pressable
                    key={m.model || 'default'}
                    testID={`chatcfg-model-${m.model || 'default'}`}
                    accessibilityRole="button"
                    onPress={() => onChange({ model: m.model })}
                    style={[styles.chip, cfg.model === m.model ? styles.chipOn : null]}
                  >
                    <Text style={[styles.chipText, cfg.model === m.model ? styles.chipTextOn : null]}>
                      {m.label}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>
          )}

          {raekke(
            'Værktøjer',
            cfg.vaerktoejer === 'fuldt'
              ? 'Han har hele værktøjskassen — også filer og kommandoer.'
              : 'Kun samtale-værktøjer: web, hukommelse, billeder.',
            <Switch
              testID="chatcfg-tools"
              value={cfg.vaerktoejer === 'fuldt'}
              onValueChange={(v) => { void haptik('send'); onChange({ vaerktoejer: v ? 'fuldt' : 'samtale' }) }}
            />,
            'chatcfg-tools-row',
          )}

          {raekke(
            'Spørg før ændringer',
            cfg.spoergFoerst
              ? 'Han beder om lov, før han ændrer noget.'
              : 'Han handler uden at spørge. Farlige kommandoer blokeres stadig.',
            <Switch
              testID="chatcfg-ask"
              value={cfg.spoergFoerst}
              onValueChange={(v) => { void haptik('send'); onChange({ spoergFoerst: v }) }}
            />,
            'chatcfg-ask-row',
          )}

          {raekke(
            'Læs svar højt',
            'Kun i denne samtale.',
            <Switch
              testID="chatcfg-voice"
              value={cfg.stemme}
              onValueChange={(v) => { void haptik('send'); onChange({ stemme: v }) }}
            />,
            'chatcfg-voice-row',
          )}
        </ScrollView>
        <Pressable accessibilityRole="button" testID="chatcfg-close" onPress={onClose} style={styles.close}>
          <Text style={{ color: tokens.color.fg1, fontWeight: '600' }}>Færdig</Text>
        </Pressable>
      </View>
    </Modal>
  )
}

const makestyles = (t: Theme) => StyleSheet.create({
  action: {
    flexDirection: 'row', alignItems: 'center', gap: 11, paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: t.color.line,
    marginBottom: 14,
  },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' },
  sheet: {
    backgroundColor: t.color.bg1, borderTopLeftRadius: 18, borderTopRightRadius: 18,
    paddingHorizontal: 18, paddingBottom: 26, maxHeight: '72%',
  },
  grabber: {
    alignSelf: 'center', width: 38, height: 4, borderRadius: 2,
    backgroundColor: t.color.line, marginTop: 8, marginBottom: 10,
  },
  heading: { color: t.color.fg1, fontSize: 17, fontWeight: '700', marginBottom: 4 },
  body: { marginTop: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 12 },
  rowText: { flex: 1, minWidth: 0 },
  rowTitle: { color: t.color.fg1, fontSize: 15, fontWeight: '600' },
  rowHint: { color: t.color.fg3, fontSize: 12.5, marginTop: 2, lineHeight: 17 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8, marginBottom: 4 },
  chip: {
    paddingVertical: 6, paddingHorizontal: 12, borderRadius: 999,
    borderWidth: 1, borderColor: t.color.line,
  },
  chipOn: { borderColor: t.color.accent, backgroundColor: t.color.bg2 },
  chipText: { color: t.color.fg2, fontSize: 13 },
  chipTextOn: { color: t.color.fg1, fontWeight: '600' },
  close: { alignSelf: 'center', paddingVertical: 12, paddingHorizontal: 26, marginTop: 6 },
})
