import { useEffect, useRef, useState } from 'react'
import { Image, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { ArrowUp, AudioLines, ChevronDown, Cpu, FileText, Mic, Plus, Square } from 'lucide-react-native'
import { shortModelLabel } from '../lib/modelLabel'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

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
  attachments,
  onRemoveAttachment,
  onFocusChange,
  showJumpToBottom,
  onJumpToBottom
}: {
  disabled?: boolean
  working?: boolean
  modelLabel?: string
  onSend: (text: string) => void | Promise<void>
  onStop: () => void
  onPressModel?: () => void
  onAttach?: () => void
  onMic?: () => void
  attachments?: { id: string; uri: string; name: string; mime: string }[]
  onRemoveAttachment?: (id: string) => void
  /** Løftes ud, så skærmen kan vide om komponisten er i brug. */
  onFocusChange?: (focused: boolean) => void
  /** Rul-til-bunden flytter IND i komponisten mens man skriver. */
  showJumpToBottom?: boolean
  onJumpToBottom?: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [focused, setFocused] = useState(false)
  // Et tryk på hvilepillen skal åbne arbejdsformen FØR tastaturet er nået frem.
  // Uden dette flag ville vi vente på TextInputens onFocus — men den findes ikke
  // endnu i hvileformen, så trykket ville ikke føre nogen steder hen.
  const [wantFocus, setWantFocus] = useState(false)
  const inputRef = useRef<TextInput>(null)
  // Hvileform: intet skrevet, ikke i fokus, intet vedhæftet, ikke i gang.
  const att = attachments ?? []
  const resting = !text && !focused && !wantFocus && att.length === 0 && !working

  // Arbejdsformen er lige monteret efter et tryk på hvilepillen → giv feltet
  // fokus, så tastaturet kommer frem uden et ekstra tryk.
  useEffect(() => {
    if (wantFocus) inputRef.current?.focus()
  }, [wantFocus])

  // Skærmen skal vide om komponisten er i brug: rul-til-bunden sidder OVER
  // komponisten når den hviler, og INDE I den mens man skriver — ellers ville
  // knappen ligge oven på det man er ved at skrive.
  useEffect(() => {
    onFocusChange?.(!resting)
  }, [resting, onFocusChange])

  const submit = async () => {
    const value = text.trim()
    // Tillad send når der er en vedhæftning, selv uden tekst.
    if ((!value && att.length === 0) || disabled || working || submitting) return

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

  // ── HVILEFORM ────────────────────────────────────────────────────────
  // ÉN række, 48 dp høj — som målt i referencen. Den var før forsøgt lavet
  // ved at nulstille kortets polstring, men kortet indeholdt stadig TO rækker
  // (felt over knapper), så begge huggede kanten: teksten klistrede til
  // overkanten og send-knappen til underkanten. En hvileform på én række skal
  // faktisk VÆRE én række — ikke to rækker med polstringen taget væk.
  //
  // Feltet er en attrap her. Den ægte TextInput lever kun i arbejdsformen, så
  // de to former ikke skal dele én komponent med modstridende krav.
  if (resting) {
    return (
      <View style={[styles.outer, styles.outerResting]}>
        <Pressable
          testID="composer-rest"
          accessibilityRole="button"
          accessibilityLabel="Skriv til Jarvis"
          onPress={() => setWantFocus(true)}
          style={[styles.card, styles.cardResting]}
        >
          <Pressable accessibilityRole="button" accessibilityLabel="Vedhæft" onPress={onAttach} hitSlop={6} style={styles.iconBtn}>
            <Plus size={22} color={tokens.color.fg1} strokeWidth={2} />
          </Pressable>
          <Text style={styles.restPlaceholder} numberOfLines={1}>Skriv til Jarvis</Text>
          <Pressable accessibilityRole="button" accessibilityLabel="Diktér" onPress={onMic} hitSlop={6} style={styles.iconBtn}>
            <Mic size={21} color={tokens.color.fg1} strokeWidth={1.8} />
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Stemme"
            onPress={onMic}
            style={({ pressed }) => [styles.sendBtn, pressed ? styles.pressed : null]}
          >
            <AudioLines size={19} color={tokens.color.bg0} strokeWidth={2} />
          </Pressable>
        </Pressable>
      </View>
    )
  }

  // ── ARBEJDSFORM ──────────────────────────────────────────────────────
  return (
    <View style={styles.outer}>
      <View style={styles.card}>
        {att.length ? (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.attachRow}
          >
            {att.map((a) => (
              <View key={a.id} testID={`attach-chip-${a.id}`} style={styles.attachChip}>
                {a.mime.startsWith('image/') ? (
                  <Image source={{ uri: a.uri }} style={styles.attachThumb} />
                ) : (
                  <View style={styles.attachIcon}>
                    <FileText size={18} color={tokens.color.fg2} strokeWidth={1.8} />
                  </View>
                )}
                <Text style={styles.attachName} numberOfLines={1}>{a.name}</Text>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Fjern ${a.name}`}
                  onPress={() => onRemoveAttachment?.(a.id)}
                  hitSlop={8}
                  style={styles.attachRemove}
                >
                  <Text style={styles.attachRemoveText}>×</Text>
                </Pressable>
              </View>
            ))}
          </ScrollView>
        ) : null}
        <TextInput
          ref={inputRef}
          testID="composer-input"
          value={text}
          onChangeText={setText}
          onFocus={() => setFocused(true)}
          onBlur={() => { setFocused(false); setWantFocus(false) }}
          multiline
          editable={!disabled}
          placeholder="Skriv til Jarvis"
          placeholderTextColor={tokens.color.fg3}
          style={styles.input}
        />
        <View style={styles.controls}>
          <View style={styles.left}>
            <Pressable accessibilityRole="button" accessibilityLabel="Vedhæft" onPress={onAttach} hitSlop={6} style={styles.iconBtn}>
              <Plus size={22} color={tokens.color.fg1} strokeWidth={2} />
            </Pressable>
            {modelLabel ? (
              <Pressable
                testID="composer-model"
                accessibilityRole="button"
                accessibilityLabel={`Model: ${modelLabel}`}
                onPress={onPressModel}
                style={styles.modelPill}
              >
                <Cpu size={15} color={tokens.color.fg2} strokeWidth={2} />
                <Text style={styles.modelText} numberOfLines={1}>{shortModelLabel(modelLabel)}</Text>
              </Pressable>
            ) : null}
          </View>
          <View style={styles.right}>
            {showJumpToBottom ? (
              <Pressable
                testID="composer-jump"
                accessibilityRole="button"
                accessibilityLabel="Rul til nyeste"
                onPress={onJumpToBottom}
                hitSlop={6}
                style={styles.iconBtn}
              >
                <ChevronDown size={20} color={tokens.color.fg1} strokeWidth={2.2} />
              </Pressable>
            ) : null}
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
              ) : text || att.length ? (
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

const makestyles = (tokens: Theme) => StyleSheet.create({
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
  // Hvileform: ÉN vandret række med feltet som attrap mellem ikonerne.
  // Polstringen er lille men ikke NUL — det var netop nul-polstringen der
  // fik indholdet til at hugge kanten, både i den gamle fokus-variant og
  // bagefter i hvile.
  cardResting: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    paddingHorizontal: tokens.spacing.sm,
    paddingTop: tokens.spacing.xs,
    paddingBottom: tokens.spacing.xs
  },
  restPlaceholder: {
    flex: 1,
    color: tokens.color.fg3,
    fontSize: 16
  },
  // Fokus markeres ikke med en kant — feltet er allerede i forgrunden.
  cardFocused: {},
  // Chips ruller vandret. Sender man fem filer, må rækken ikke kunne vokse
  // komponisten ud over skærmen.
  attachRow: { gap: tokens.spacing.xs, paddingBottom: tokens.spacing.xs },
  attachChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg3,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.xs,
    maxWidth: 210
  },
  attachIcon: {
    width: 40, height: 40, borderRadius: tokens.radius.sm,
    alignItems: 'center', justifyContent: 'center',
    backgroundColor: tokens.color.bg2
  },
  attachThumb: { width: 40, height: 40, borderRadius: tokens.radius.sm, backgroundColor: tokens.color.bg3 },
  attachName: { color: tokens.color.fg2, fontSize: 13, flexShrink: 1 },
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
  // Chippen bar før hele strengen «deepseek · deepseek-v4-flash» og åd over
  // halvdelen af rækken. Nu: et lille ikon + modellens egen del af navnet.
  modelPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    height: 30,
    borderRadius: 15,
    backgroundColor: tokens.color.bg3,
    flexShrink: 1
  },
  modelText: { color: tokens.color.fg2, fontSize: 12, fontWeight: '600', flexShrink: 1 },
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
