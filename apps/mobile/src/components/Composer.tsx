import { useEffect, useRef, useState } from 'react'
import { hentForslag, PAUSE_MS, saetSammen } from '../lib/forslag'
import { Animated, Image, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { haptik } from '../lib/haptics'
import { ArrowUp, ChevronDown, Cpu, FileText, Mic, Plus, SearchCheck, ShieldCheck, Square } from 'lucide-react-native'
import { PulsIkon } from './PulsIkon'
import type { ApprovalMode } from './PermissionPicker'
import type { DictationState } from '../lib/useComposerDictation'
import { DictationBar } from './DictationBar'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { UploadRing, samletUploadAndel } from './UploadRing'

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
  config,
  disabled,
  working,
  modelLabel,
  onSend,
  onStop,
  onPressModel,
  onAttach,
  onDictate,
  onConversation,
  attachments,
  onRemoveAttachment,
  onFocusChange,
  showJumpToBottom,
  onJumpToBottom,
  researchMode,
  onResearchModeChange,
  permission,
  onPressPermission,
  indsaet,
  dictationState = 'idle',
  dictationElapsedMs = 0,
  dictationError,
  dictationLevel,
  onStopDictation,
  onCancelDictation,
}: {
  /** API-adgang til forslag. Udeladt = ingen forslag, alt andet virker. */
  config?: { apiBaseUrl: string; authToken: string } | null
  disabled?: boolean
  working?: boolean
  modelLabel?: string
  onSend: (text: string) => void | Promise<void>
  onStop: () => void
  onPressModel?: () => void
  onAttach?: () => void
  onDictate?: () => void
  onConversation?: () => void
  attachments?: { id: string; uri: string; name: string; mime: string; status?: 'uploading' | 'ready' | 'error'; progress?: number }[]
  onRemoveAttachment?: (id: string) => void
  /** Løftes ud, så skærmen kan vide om komponisten er i brug. */
  onFocusChange?: (focused: boolean) => void
  /** Rul-til-bunden flytter IND i komponisten mens man skriver. */
  showJumpToBottom?: boolean
  onJumpToBottom?: () => void
  researchMode?: boolean
  onResearchModeChange?: (next: boolean) => void
  permission?: ApprovalMode
  onPressPermission?: () => void
  /** Tekst udefra — fx en delt lokation eller udklipsholderen.
   *
   *  Signalet er en TÆLLER og ikke bare strengen: indsætter man den samme
   *  tekst to gange, ændrer strengen sig ikke, og en effekt på strengen alene
   *  ville tie anden gang. */
  indsaet?: { tekst: string; n: number; erstat?: boolean }
  dictationState?: DictationState
  dictationElapsedMs?: number
  dictationError?: string
  dictationLevel?: Animated.Value
  onStopDictation?: () => void
  onCancelDictation?: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [text, setText] = useState('')
  const sidsteIndsaet = useRef(0)

  // ── Forslag i komponisten ────────────────────────────────────────────────
  // Hvad der kunne skrives videre. Laves af en LOKAL model (qwen paa GPU'en):
  // et forslag fyrer mens han skriver, altsaa foer der overhovedet er en tur,
  // og den betalte lane er kun til hans egne ture. Vigtigere endnu: et halvt
  // skrevet udkast er det mest private i en samtale — det indeholder det man
  // fortryder og sletter igen — og det forlader ikke maskinen.
  //
  // `config` kommer som PROP og ikke fra `useAuth()`. Foerste udgave greb i
  // konteksten, og alle sytten komponist-tests gik roede med «useAuth must be
  // used within AuthProvider» — med rette: en praesentations-komponent der
  // raekker ned i auth-laget kan ikke proeves alene. Uden config er der bare
  // ingen forslag; alt andet i komponisten virker.
  const [forslag, setForslag] = useState('')
  const afbryd = useRef<AbortController | null>(null)

  /**
   * Skriv i feltet — og ryd forslaget i SAMME opdatering.
   *
   * Første udgave ryddede det i effekten nedenfor. Det er ét billede for sent:
   * en test fangede at linjen stadig stod med det gamle forslag efter et nyt
   * tastetryk, og i appen ville man se et forslag der passer til en sætning
   * der ikke findes mere. React batcher de to `set` her, så der er ingen
   * mellemtilstand at få øje på.
   */
  function skriv(ny: string) {
    setText(ny)
    setForslag('')
  }

  useEffect(() => {
    afbryd.current?.abort()
    if (!config || disabled) {
      // Slaas feltet fra midt i det hele, skal linjen ogsaa vaek. `skriv`
      // rydder kun ved tastetryk, og et forslag hen over et deaktiveret felt
      // er noget man kan trykke paa uden at kunne goere noget ved det.
      setForslag('')
      return
    }
    const c = new AbortController()
    afbryd.current = c
    const id = setTimeout(() => {
      void hentForslag(
        config.apiBaseUrl.replace(/\/$/, ''), config.authToken, text, c.signal
      ).then((f) => { if (!c.signal.aborted) setForslag(f) })
    }, PAUSE_MS)
    return () => { clearTimeout(id); c.abort() }
  }, [text, config, disabled])
  const [submitting, setSubmitting] = useState(false)
  const [focused, setFocused] = useState(false)
  // Et tryk på hvilepillen skal åbne arbejdsformen FØR tastaturet er nået frem.
  // Uden dette flag ville vi vente på TextInputens onFocus — men den findes ikke
  // endnu i hvileformen, så trykket ville ikke føre nogen steder hen.
  const [wantFocus, setWantFocus] = useState(false)
  const inputRef = useRef<TextInput>(null)
  // Hvileform: intet skrevet, ikke i fokus, intet vedhæftet, ikke i gang.
  const att = attachments ?? []
  // null = ingen upload i gang. Vigtigt at kunne skelne fra 0 %, ellers
  // ville ringen staa tom paa skaermen naar der intet sker.
  const uploadAndel = samletUploadAndel(att)
  const resting = !text && !focused && !wantFocus && att.length === 0 && !working && dictationState === 'idle'

  // Arbejdsformen er lige monteret efter et tryk på hvilepillen → giv feltet
  // fokus, så tastaturet kommer frem uden et ekstra tryk.
  useEffect(() => {
    if (wantFocus) inputRef.current?.focus()
  }, [wantFocus])

  // Tekst udefra lægges TIL det man allerede har skrevet — ikke i stedet for.
  // Man kan godt have skrevet en halv sætning og så dele sin lokation.
  useEffect(() => {
    if (!indsaet || indsaet.n === sidsteIndsaet.current) return
    sidsteIndsaet.current = indsaet.n
    const t = String(indsaet.tekst || '')
    // `erstat`: teksten ER feltet — fx beskeden man spolede tilbage fra, og
    // tom igen når tilbagespolingen fortrydes (Claude Desktop §8).
    if (indsaet.erstat) { setText(t); if (t) setWantFocus(true); return }
    if (!t) return
    setText((prev) => (prev ? `${prev}\n${t}` : t))
    setWantFocus(true)
  }, [indsaet])

  // Skærmen skal vide om komponisten er i brug: rul-til-bunden sidder OVER
  // komponisten når den hviler, og INDE I den mens man skriver — ellers ville
  // knappen ligge oven på det man er ved at skrive.
  useEffect(() => {
    onFocusChange?.(!resting)
  }, [resting, onFocusChange])

  // Under et svar: står der noget i feltet, lægger knappen det i kø; er feltet
  // tomt, er den stop. Så kan man både skrive videre og afbryde.
  const koeer = !!working && (!!text.trim() || att.length > 0)
  const stopper = !!working && !koeer

  const submit = async () => {
    const value = text.trim()
    // Tillad send når der er en vedhæftning, selv uden tekst.
    // Under et svar er send tilladt: ChatScreen lægger beskeden i kø.
    if ((!value && att.length === 0) || disabled || submitting) return

    setSubmitting(true)
    // Kvitteringen kommer FØR kaldet: den skal mærkes i det øjeblik man
    // trykker, ikke når serveren svarer.
    void haptik('send')
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
          <Pressable testID="composer-dictate" accessibilityRole="button" accessibilityLabel="Dikter" onPress={onDictate} hitSlop={6} style={styles.iconBtn}>
            <Mic size={21} color={tokens.color.fg1} strokeWidth={1.8} />
          </Pressable>
          {uploadAndel !== null ? (
            // UNDER UPLOAD viser knappen fremdrift i stedet for boelgen.
            // Tallet blev maalt hele tiden og stod paa miniaturen — et sted
            // ingen kigger mens de venter. Her er det dér hvor oejet hviler.
            <View testID="composer-upload" style={styles.sendBtnTom}>
              <UploadRing andel={uploadAndel} size={38} />
            </View>
          ) : (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Start samtale"
              onPress={onConversation}
              style={({ pressed }) => [styles.sendBtn, pressed ? styles.pressed : null]}
            >
              <PulsIkon size={21} color={tokens.color.bg0} />
            </Pressable>
          )}
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
                  <View>
                    <Image source={{ uri: a.uri }} style={styles.attachThumb} />
                    {a.status === 'uploading' ? (
                      <View style={styles.attachBadge}>
                        <Text style={styles.attachBadgeText}>{Math.max(1, Math.min(99, Math.round(a.progress ?? 1)))}%</Text>
                      </View>
                    ) : a.status === 'error' ? (
                      <View style={[styles.attachBadge, styles.attachBadgeError]}>
                        <Text style={styles.attachBadgeText}>Fejl</Text>
                      </View>
                    ) : null}
                  </View>
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
        <DictationBar
          state={dictationState}
          elapsedMs={dictationElapsedMs}
          error={dictationError}
          level={dictationLevel}
          onStop={() => onStopDictation?.()}
          onCancel={() => onCancelDictation?.()}
        />
        {forslag ? (
          <Pressable
            testID="composer-forslag"
            accessibilityRole="button"
            accessibilityLabel={`Forslag: ${text}${forslag}. Tryk for at bruge det.`}
            onPress={() => {
              setText(saetSammen(text, forslag))
              setForslag('')
              inputRef.current?.focus()
            }}
            style={styles.forslag}
          >
            <Text numberOfLines={1} style={styles.forslagTekst}>
              <Text style={styles.forslagSkrevet}>{text}</Text>{forslag}
            </Text>
          </Pressable>
        ) : null}
        <TextInput
          ref={inputRef}
          testID="composer-input"
          value={text}
          onChangeText={skriv}
          onFocus={() => setFocused(true)}
          onBlur={() => { setFocused(false); setWantFocus(false) }}
          multiline
          editable={!disabled}
          placeholder="Skriv til Jarvis"
          placeholderTextColor={tokens.color.fg3}
          style={styles.input}
        />
        <View style={styles.controls}>
          <View testID="composer-control-row" style={styles.left}>
            <Pressable accessibilityRole="button" accessibilityLabel="Vedhæft" onPress={onAttach} hitSlop={6} style={styles.iconBtn}>
              <Plus size={22} color={tokens.color.fg1} strokeWidth={2} />
            </Pressable>
            {onPressPermission ? (
              <Pressable
                testID="composer-permission"
                accessibilityRole="button"
                accessibilityLabel={`Tilladelser: ${permission === 'trust' ? 'Fuld adgang' : 'Spørg først'}`}
                onPress={onPressPermission}
                style={[styles.controlIcon, permission === 'trust' && styles.controlIconOn]}
              >
                <ShieldCheck size={18} color={permission === 'trust' ? tokens.color.bg0 : tokens.color.fg2} strokeWidth={2} />
              </Pressable>
            ) : null}
            {modelLabel ? (
              <Pressable
                testID="composer-model"
                accessibilityRole="button"
                accessibilityLabel={`Model: ${modelLabel}`}
                onPress={onPressModel}
                style={styles.controlIcon}
              >
                <Cpu size={18} color={tokens.color.fg2} strokeWidth={2} />
              </Pressable>
            ) : null}
            {onResearchModeChange ? (
              <Pressable
                testID="composer-research"
                accessibilityRole="button"
                accessibilityLabel={`Research: ${researchMode ? 'Til' : 'Fra'}`}
                accessibilityState={{ selected: Boolean(researchMode) }}
                onPress={() => onResearchModeChange(!researchMode)}
                style={[styles.controlIcon, researchMode && styles.controlIconOn]}
              >
                <SearchCheck size={18} color={researchMode ? tokens.color.bg0 : tokens.color.fg2} strokeWidth={2} />
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
            <Pressable testID="composer-dictate" accessibilityRole="button" accessibilityLabel="Dikter" onPress={onDictate} hitSlop={6} style={styles.iconBtn}>
              <Mic size={21} color={tokens.color.fg1} strokeWidth={1.8} />
            </Pressable>
            <Pressable
              testID="composer-button"
              accessibilityRole="button"
              disabled={(disabled && !stopper) || submitting}
              accessibilityLabel={stopper ? 'Stop svar' : koeer ? 'Læg i kø' : text || att.length ? 'Send' : 'Start samtale'}
              onPress={stopper ? () => { void haptik('stop'); onStop() } : text || att.length ? submit : onConversation}
              style={({ pressed }) => [
                styles.sendBtn,
                stopper ? styles.stopBtn : null,
                (disabled && !stopper) || submitting ? styles.disabled : null,
                pressed ? styles.pressed : null
              ]}
            >
              {stopper ? (
                <Square size={15} color={tokens.color.bg0} fill={tokens.color.bg0} strokeWidth={2} />
              ) : text || att.length ? (
                <ArrowUp size={20} color={tokens.color.bg0} strokeWidth={2.5} />
              ) : (
                <PulsIkon size={21} color={tokens.color.bg0} />
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
    backgroundColor: tokens.color.bgFloat,
    ...tokens.elevation,
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
  attachBadge: {
    position: 'absolute',
    right: 3,
    bottom: 3,
    minWidth: 34,
    alignItems: 'center',
    borderRadius: tokens.radius.pill,
    paddingHorizontal: 6,
    paddingVertical: 2,
    backgroundColor: 'rgba(0,0,0,0.72)'
  },
  attachBadgeError: { backgroundColor: tokens.color.error },
  attachBadgeText: { color: tokens.color.fg1, fontSize: 10, fontWeight: '800' },
  attachName: { color: tokens.color.fg2, fontSize: 13, flexShrink: 1 },
  attachRemove: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.bg3 },
  attachRemoveText: { color: tokens.color.fg1, fontSize: 18, lineHeight: 20 },
  // Forslags-linjen staar OVER feltet, ikke inde i det. Ghost-tekst inde i et
  // RN-TextInput kraever en usynlig kopi ovenpaa, holdt i synk ved hvert
  // tastetryk — to sandheder om hvad der staar. En linje man kan trykke paa
  // siger det samme, rammes med en tommelfinger og kan laeses op.
  forslag: {
    paddingHorizontal: 2,
    paddingBottom: 4
  },
  forslagTekst: {
    fontSize: 15,
    color: tokens.color.fg3
  },
  // Det ALLEREDE skrevne staar endnu svagere: oejet skal fange fortsaettelsen,
  // ikke laese sin egen saetning igen.
  forslagSkrevet: {
    color: tokens.color.fg3,
    opacity: 0.45
  },
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
  sendBtnTom: {
    width: 44, height: 44, borderRadius: 22,
    alignItems: 'center', justifyContent: 'center'
  },
  controlIcon: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.bg3
  },
  controlIconOn: { backgroundColor: tokens.color.accent },
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
