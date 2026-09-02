import { useState } from 'react'
import { Image, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { ArrowUp, AudioLines, Mic, Plus, Square } from 'lucide-react-native'
import { tokens } from '../theme/tokens'

/**
 * Komponisten har TO former — begge målt i ChatGPT-appen (densitet 2,625):
 *
 *   i hvile   344 dp bred · 48 dp høj · 34 dp margen · ÉN række
 *   i brug    387 dp bred · to rækker · 12 dp margen
 *
 * Den vokser og bliver BREDERE når man går i gang. Det er ikke pynt: den
 * smalle hvileform giver tråden luft, og den brede arbejdsform giver plads
 * til at skrive. Vi havde kun den brede — derfor virkede bunden tung.
 *
 * I hvile er højre knap en voice-knap (lydbølge); så snart der er tekst,
 * bliver den en send-pil. Under arbejde bliver den en firkant i SAMME lilla —
 * ChatGPT skifter ikke farve for at kunne stoppe.
 */
export function Composer({
  disabled,
  working,
  modelLabel,
  onSend,
  onStop,
  onPressModel,
  onAttach,
  onMic,
  attachment,
  onRemoveAttachment
}: {
  disabled?: boolean
  working?: boolean
  modelLabel?: string
  onSend: (text: string) => void | Promise<void>
  onStop: () => void
  onPressModel?: () => void
  onAttach?: () => void
  onMic?: () => void
  attachment?: { uri: string; name: string } | null
  onRemoveAttachment?: () => void
}) {
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [focused, setFocused] = useState(false)
  // Hvileform: intet skrevet, ikke i fokus, intet vedhæftet, ikke i gang.
  const resting = !text && !focused && !attachment && !working

  const submit = async () => {
    const value = text.trim()
    // Tillad send når der er en vedhæftning, selv uden tekst.
    if ((!value && !attachment) || disabled || working || submitting) return

    setSubmitting(true)
    try {
      await onSend(value)
      setText('')
    } catch {
      // Behold kladden hvis send fejler.
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <View style={[styles.outer, resting && styles.outerResting]}>
      <View style={[styles.card, resting ? styles.cardResting : null]}>
        {attachment ? (
          <View style={styles.attachChip}>
            <Image source={{ uri: attachment.uri }} style={styles.attachThumb} />
            <Text style={styles.attachName} numberOfLines={1}>{attachment.name}</Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Fjern vedhæftning"
              onPress={onRemoveAttachment}
              hitSlop={8}
              style={styles.attachRemove}
            >
              <Text style={styles.attachRemoveText}>×</Text>
            </Pressable>
          </View>
        ) : null}
        <TextInput
          testID="composer-input"
          value={text}
          onChangeText={setText}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          multiline
          editable={!disabled}
          placeholder="Skriv til Jarvis"
          placeholderTextColor={tokens.color.fg3}
          style={styles.input}
        />
        <View style={[styles.controls, resting && styles.controlsResting]}>
          <View style={styles.left}>
            <Pressable accessibilityRole="button" accessibilityLabel="Vedhæft" onPress={onAttach} hitSlop={6} style={styles.iconBtn}>
              <Plus size={22} color={tokens.color.fg1} strokeWidth={2} />
            </Pressable>
            {modelLabel && !resting ? (
              <Pressable accessibilityRole="button" onPress={onPressModel} style={styles.modelPill}>
                <Text style={styles.modelText} numberOfLines={1}>{modelLabel}</Text>
                <Text style={styles.modelChev}>▾</Text>
              </Pressable>
            ) : null}
          </View>
          <View style={styles.right}>
            <Pressable accessibilityRole="button" accessibilityLabel="Diktér" onPress={onMic} hitSlop={6} style={styles.iconBtn}>
              <Mic size={21} color={tokens.color.fg1} strokeWidth={1.8} />
            </Pressable>
            <Pressable
              testID="composer-button"
              accessibilityRole="button"
              disabled={(disabled && !working) || submitting}
              onPress={working ? onStop : submit}
              style={({ pressed }) => [
                styles.sendBtn,
                working ? styles.stopBtn : null,
                (disabled && !working) || submitting ? styles.disabled : null,
                pressed ? styles.pressed : null
              ]}
            >
              {working ? (
                <Square size={15} color={tokens.color.bg0} fill={tokens.color.bg0} strokeWidth={2} />
              ) : text || attachment ? (
                <ArrowUp size={20} color={tokens.color.bg0} strokeWidth={2.5} />
              ) : (
                <AudioLines size={19} color={tokens.color.bg0} strokeWidth={2} />
              )}
            </Pressable>
          </View>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  outer: {
    // I brug: 12 dp margen (målt på R1 → 387 dp bred).
    paddingHorizontal: 12,
    paddingTop: tokens.spacing.sm,
    paddingBottom: tokens.spacing.md
  },
  // I hvile: 34 dp margen (målt på think4 → 344 dp bred). Den smallere pille
  // giver tråden luft; den bredere giver plads til at skrive.
  outerResting: {
    paddingHorizontal: 34
  },
  // Komponisten er MÅLT i ChatGPT-appen 2026-09-02: en flad, mørkegrå pille
  // (#212121) uden skygge og uden kant. Ingen hævet kort, ingen glød ved
  // fokus — fladen ligger stille, og kun send-knappen bærer farve. Det er en
  // del af hvorfor deres komponist virker rolig.
  card: {
    backgroundColor: tokens.color.bg2,
    borderRadius: 28,
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.md,
    paddingBottom: tokens.spacing.sm
  },
  // Hvileform: én række, 48 dp høj, indholdet centreret lodret.
  // BEMÆRK: denne stil hører til `resting` — IKKE til `focused`. Den har
  // været bundet til `focused` og nulstillede derfor kortets polstring
  // præcis når feltet var i brug: teksten klistrede til øverste venstre
  // hjørne, og send-knappens bund ramte kortets bundkant (målt: 1 px fra).
  // Hvile = smal, én række. Fokus = høj, to rækker med luft.
  cardResting: {
    minHeight: 48,
    paddingTop: 0,
    paddingBottom: 0,
    justifyContent: 'center'
  },
  controlsResting: {
    marginTop: 0
  },
  // Fokus markeres ikke med en kant — feltet er allerede i forgrunden.
  cardFocused: {},
  attachChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.xs,
    marginBottom: tokens.spacing.xs
  },
  attachThumb: { width: 40, height: 40, borderRadius: tokens.radius.sm, backgroundColor: tokens.color.bg3 },
  attachName: { flex: 1, color: tokens.color.fg2, fontSize: 13 },
  attachRemove: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.bg3 },
  attachRemoveText: { color: tokens.color.fg1, fontSize: 18, lineHeight: 20 },
  input: {
    minHeight: 28,
    maxHeight: 140,
    color: tokens.color.fg1,
    fontSize: 16,
    // Rettet ind efter [+]-knappen nedenunder: den er 34 bred og starter ved
    // kortets kant, saa dens ikon staar 6 px inde. Teksten skal staa samme
    // sted — ellers hopper venstrekanten mellem de to raekker.
    paddingHorizontal: 6,
    paddingTop: 4,
    paddingBottom: 2
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: tokens.spacing.xs
  },
  left: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm, flexShrink: 1 },
  right: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  iconBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.bg2
  },
  iconPlus: { color: tokens.color.fg1, fontSize: 20, lineHeight: 22, fontWeight: '600' },
  mic: { fontSize: 15 },
  modelPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: tokens.spacing.sm,
    height: 34,
    borderRadius: 17,
    backgroundColor: tokens.color.bg2,
    flexShrink: 1
  },
  modelText: { color: tokens.color.fg2, fontSize: 13, fontWeight: '600', flexShrink: 1 },
  modelChev: { color: tokens.color.fg3, fontSize: 11 },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.accent
  },
  // ChatGPT skifter IKKE farve når man kan stoppe — knappen bliver bare en
  // firkant i samme lilla. Rav signalerer «advarsel», og det er en helt
  // almindelig ting at afbryde.
  stopBtn: { backgroundColor: tokens.color.accent },
  disabled: { opacity: 0.4 },
  pressed: { opacity: 0.85 },
  sendText: { color: tokens.color.bg0, fontWeight: '800', fontSize: 18 }
})
