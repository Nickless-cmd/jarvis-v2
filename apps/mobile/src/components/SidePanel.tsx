import { useEffect, useMemo, useRef, useState } from 'react'
import { Animated, Dimensions, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg'
import { Activity, Boxes, Code2, Eye, Image as ImageIcon, MessageCircle, MessageSquare, MessagesSquare, MoreVertical, Pin, Search, Settings, SlidersHorizontal, SquarePen, Terminal } from 'lucide-react-native'
import { formatRelativeDate } from '../lib/relativeDate'
import { AnimeretPuls } from './AnimeretPuls'
import { PulsIkon } from './PulsIkon'
import type { ChatSession } from '../lib/types'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { OpmaerksomhedsLinje } from './OpmaerksomhedsLinje'
import { SessionMenu } from './SessionMenu'
import { TeamsPanel } from './TeamsPanel'
import { useI18n } from '../i18n/I18nContext'

const PANEL_WIDTH = Math.min(360, Math.round(Dimensions.get('window').width * 0.86))

/**
 * Slide-in panel (åbnes via presence-ringen). Sessioner med søg + datoer,
 * "Ny samtale", og et tandhjul → Settings (hvor plugins/connectors + log ud
 * bor — spec §"Settings vs Plugins"). Lukker ved ring-tryk, valg, eller udenfor.
 */
/** En raekke i panelet: ikon + navn. Erstatter de navnloese ikoner i toppen —
 *  en oejenpaere og en kasse siger ikke hvad de goer, og man skulle trykke for
 *  at finde ud af det. */
function Felt({
  ikon, navn, onPress, testID, badge, fejl,
}: {
  ikon: React.ReactNode
  navn: string
  onPress?: () => void
  testID?: string
  badge?: number
  /** Listen bag feltet kunne ikke hentes — samme skelnen som desk's
   *  Klokke.tsx: en tom liste og en brudt liste maa ikke ligne hinanden.
   *  UAFHAENGIG af `badge`: et gammelt tal kan staa samtidig med markoeren,
   *  fordi en fejlet hentning ikke nulstiller det sidst kendte tal. */
  fejl?: boolean
}) {
  const styles = useStyles(makestyles)
  const { t } = useI18n()
  const label = fejl ? t('side.fieldError', { navn }) : badge ? `${navn} (${badge})` : navn
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => [styles.felt, pressed ? styles.pressed : null]}
    >
      <View style={styles.feltIkon}>
        {ikon}
        {/* Prikken sidder OVEN PAA ikonet, ligesom `.klokke-fejl` i desk —
            og er, ligesom der, en ren visuel markoer (aria-hidden): teksten
            for skaermlaesere kommer fra `accessibilityLabel` ovenfor, ikke
            fra prikken selv. */}
        {fejl && (
          <View
            testID={testID ? `${testID}-fejl` : undefined}
            style={styles.feltFejl}
            accessibilityElementsHidden
            importantForAccessibility="no-hide-descendants"
          />
        )}
      </View>
      <Text style={styles.feltTekst} numberOfLines={1}>{navn}</Text>
      {/* Samme stil som badgen i Aktivitet-skærmen selv (accentText, 12/800) —
          tælleren skal ikke se anderledes ud fordi den bor på knappen der
          fører derhen. */}
      {badge ? <Text style={styles.badge}>{badge > 9 ? '9+' : badge}</Text> : null}
    </Pressable>
  )
}

/**
 * Fade i enden af en session-titel (Bjørn 21/9-2026: «enden af sessions
 * navnet skal have fade som i desk»).
 *
 * Desk løser det med `mask-image: linear-gradient(to right, #000 calc(100% -
 * 30px), transparent)` på titlen. Den regel har ingen pendant her: hverken
 * `@react-native-masked-view/masked-view` eller `expo-linear-gradient` er
 * installeret. `react-native-svg` ER — og en gradient fra transparent til
 * rækkens EGEN baggrund giver samme virkning: teksten glider ud i fladen
 * frem for at blive klippet med en hård kant.
 *
 * `farve` er derfor BAGGRUNDEN, ikke tekstfarven. Rækken skifter mellem bg0
 * og bg3 (aktiv), og et overlay i den forkerte af dem ville ses som en plet.
 */
function FadeKant({ farve, bredde = 28 }: { farve: string; bredde?: number }) {
  const styles = useStyles(makestyles)
  return (
    <Svg
      testID="session-fade"
      pointerEvents="none"
      width={bredde}
      height="100%"
      style={styles.fadeKant}
    >
      <Defs>
        <LinearGradient id="titelFade" x1="0" y1="0" x2="1" y2="0">
          <Stop offset="0" stopColor={farve} stopOpacity="0" />
          <Stop offset="1" stopColor={farve} stopOpacity="1" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="100%" height="100%" fill="url(#titelFade)" />
    </Svg>
  )
}

export function SidePanel({
  open,
  onClose,
  displayName,
  sessions,
  activeId,
  onSelectSession,
  onNewSession,
  onOpenSettings,
  onOpenChatSettings,
  onOpenSenses,
  onOpenArtifacts,
  onOpenBilleder,
  onOpenActivity,
  activityAntal = 0,
  activityFejl = false,
  isOwner: inHousehold = false,
  workingIds = [],
  onSessionAction,
  unreadIds = {},
  onFloatActive,
  bubbleSupported = false,
  kodeTilstand = false,
  onSkiftFlade,
  config = null
}: {
  open: boolean
  onClose: () => void
  displayName: string
  sessions: ChatSession[]
  activeId: string | null
  onSelectSession: (sessionId: string) => void
  onNewSession: () => void
  onOpenSettings: () => void
  /** Indstillinger for den AKTIVE samtale — model, værktøjer, stemme. */
  onOpenChatSettings?: () => void
  /** Sansernes Arkiv. Kun sat for husstanden — men serveren er den ægte grænse. */
  onOpenSenses?: () => void
  onOpenArtifacts?: () => void
  /** Billederne i DENNE samtale. Uden en aktiv samtale er der intet at vise. */
  onOpenBilleder?: () => void
  onOpenActivity?: () => void
  /** Antal åbne notifikationer — vises som en lille tæller på Aktivitet-feltet.
   *  0 tegner ingen badge (samme regel som outboxCount's «i kø»-tal). */
  activityAntal?: number
  /** Notifikations-hentningen fejlede — en synlig markoer paa feltet,
   *  UAFHAENGIG af `activityAntal` (det sidst kendte tal bliver staaende).
   *  Samme skelnen som desk's Klokke.tsx mellem «ingen» og «kunne ikke
   *  hentes»; se ChatScreen.tsx's `notifFejl`. */
  activityFejl?: boolean
  /** Bor brugeren i hjemmet (owner eller partner)? Skjuler kun indgangen. */
  isOwner?: boolean
  /** Står vi i code-fladen? Afgør om feltet fører IND eller UD. */
  kodeTilstand?: boolean
  /** Skifter mellem chat og code. Uden den tegnes feltet ikke. */
  onSkiftFlade?: (tilKode: boolean) => void
  workingIds?: string[]
  /** Handlinger paa én samtale. Uden den tegnes prikkerne slet ikke —
   *  en menu der aabner og ikke kan goere noget er vaerre end ingen. */
  onSessionAction?: (handling: {
    slags: 'rename' | 'delete' | 'flags'
    id: string
    titel?: string
    flags?: { pinned?: boolean; archived?: boolean }
  }) => void
  unreadIds?: Record<string, boolean>
  onFloatActive?: () => void
  bubbleSupported?: boolean
  config?: import('../lib/types').ApiConfig | null
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { t } = useI18n()
  const insets = useSafeAreaInsets()
  const translateX = useRef(new Animated.Value(-PANEL_WIDTH)).current
  const [mounted, setMounted] = useState(open)
  const [query, setQuery] = useState('')
  // Soegefeltet er foldet sammen som standard: det blev brugt sjaeldent og
  // fyldte en linje hele tiden. Ikonet i toppen folder det ud.
  const [soegAaben, setSoegAaben] = useState(false)
  const [menuFor, setMenuFor] = useState<ChatSession | null>(null)
  // Initialer som R4's «BS»-cirkel. To bogstaver, aldrig flere.
  const initials = useMemo(
    () =>
      (displayName || 'J')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0]?.toUpperCase() ?? '')
        .join('') || 'J',
    [displayName]
  )

  useEffect(() => {
    if (open) setMounted(true)
    Animated.timing(translateX, {
      toValue: open ? 0 : -PANEL_WIDTH,
      duration: 220,
      useNativeDriver: true
    }).start(({ finished }) => {
      if (finished && !open) setMounted(false)
    })
  }, [open, translateX])

  const now = new Date()
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return sessions
    return sessions.filter((s) => (s.title || '').toLowerCase().includes(q))
  }, [sessions, query])

  if (!mounted) return null

  return (
    <Modal transparent visible={mounted} animationType="none" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Animated.View
          style={[
            styles.panel,
            { width: PANEL_WIDTH, paddingTop: insets.top + tokens.spacing.md, transform: [{ translateX }] }
          ]}
        >
          <View style={styles.headerRow}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('common.closePanel')}
              onPress={onClose}
              hitSlop={8}
              style={styles.identity}
            >
              {/* Mærket, ikke den gamle ring (Bjørn 21/9-2026: «i venstre panel
                  i toppen lige før mit navn er det gamle ring ikon stadigvæk»).
                  Ringen var en cirkel med en prik i — den form hører til før
                  Puls-mærket. Desk har allerede mærket her (JarvisRing), så
                  telefonens navn og skrivebordets står nu som samme tegn.

                  OG DET SKAL LEVE (Bjørn, samme dag: «bør være animeret og en
                  smule større»). Her staar maerket uden en tilstand at foelge —
                  det er navnet, ikke en session — saa det animerer altid. Det
                  er den samme rytme som desk's JarvisRing bruger, og som
                  session-raekkens maerke bruger: tre bjaelker i boelge, 1,6 s.
                  Roen for bevægelsesfølsomme kommer fra AnimeretPuls selv. */}
              <AnimeretPuls size={32} farve={tokens.color.accent} testID="navn-puls" />
              <Text style={styles.name} numberOfLines={1}>
                {displayName || 'Jarvis'}
              </Text>
            </Pressable>
            {/* SØGNINGEN ER ET IKON HER, ikke et felt nedenfor. Feltet stod og
                fyldte en linje hele tiden for noget man goer sjaeldent, mens de
                fem genveje sad som ikoner uden navn — altsaa det modsatte af
                hvor tit de bruges. */}
            <Pressable
              testID="panel-search-toggle"
              accessibilityRole="button"
              accessibilityLabel={soegAaben ? t('side.closeSearch') : t('side.searchConversations')}
              accessibilityState={{ expanded: soegAaben }}
              onPress={() => setSoegAaben((v) => !v)}
              hitSlop={8}
              style={styles.gear}
            >
              <Search size={18} color={soegAaben ? tokens.color.accent : tokens.color.fg2} strokeWidth={1.8} />
            </Pressable>
          </View>

          {soegAaben ? (
            <View style={styles.searchWrap}>
              <Search size={15} color={tokens.color.fg3} strokeWidth={1.8} />
              <TextInput
                autoFocus
                value={query}
                onChangeText={setQuery}
                placeholder={t('side.searchConversations')}
                placeholderTextColor={tokens.color.fg3}
                style={styles.search}
              />
            </View>
          ) : null}

          {/* De fem som FELTER. Som ikoner sagde de ikke hvad de var — en oejenpaere
              og en kasse er ikke selvforklarende, og man skulle trykke for at finde
              ud af det. Et felt baerer sit eget navn. */}
          {/* Tilstands-hjernen (19/9-2026): hvad kræver dig — tavs når intet gør. */}
          <OpmaerksomhedsLinje onAabn={onSelectSession} />
          <View style={styles.felter}>
            {bubbleSupported && activeId ? (
              <Felt ikon={<MessageCircle size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn={t('side.moveChatToBubble')} onPress={onFloatActive} />
            ) : null}
            {inHousehold && onOpenSenses ? (
              // Skjuler kun noget der ALLEREDE er lukket: /companion/senses
              // afviser alle uden for husstanden med 403 i auth-laget.
              // Forskellen på en dør og et gardin — her er gardinet.
              <Felt testID="open-senses"
                    ikon={<Eye size={18} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn={t('side.sensesArchive')} onPress={onOpenSenses} />
            ) : null}
            {onOpenArtifacts ? (
              <Felt testID="open-artifacts"
                    ikon={<Boxes size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn={t('side.artifacts')} onPress={onOpenArtifacts} />
            ) : null}
            {onOpenBilleder && activeId ? (
              // Kraever en AKTIV samtale: feltet hedder «Billeder» og betyder
              // billederne HER. Uden en samtale ville det foere til en tom
              // skaerm der ser ud som om der ingen billeder findes.
              <Felt testID="open-billeder"
                    ikon={<ImageIcon size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn={t('side.images')} onPress={onOpenBilleder} />
            ) : null}
            {onOpenActivity ? (
              <Felt testID="open-activity"
                    ikon={<Activity size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn={t('side.activity')} onPress={onOpenActivity} badge={activityAntal}
                    fejl={activityFejl} />
            ) : null}
            {onOpenChatSettings ? (
              <Felt testID="open-chat-settings"
                    ikon={<SlidersHorizontal size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn={t('side.thisConversation')} onPress={onOpenChatSettings} />
            ) : null}
            {/* SAMME felt, to retninger. Bjørn bad om «et tilbage til chat felt
                i panelet når man er i code mode» — men en dør der kun åbner
                indad efterlader code-fladen uden en indgang, og porten han
                beskrev (QR'en) findes ikke: `/auth/pair/*` udsteder et
                login-token og binder ikke telefonen til en desk-instans.
                Derfor bærer feltet begge veje. */}
            {onSkiftFlade ? (
              <Felt testID="skift-flade"
                    ikon={kodeTilstand
                      ? <MessagesSquare size={17} color={tokens.color.fg2} strokeWidth={1.8} />
                      : <Terminal size={17} color={tokens.color.fg2} strokeWidth={1.8} />}
                    navn={kodeTilstand ? t('topbar.backToChat') : t('app.code')}
                    onPress={() => onSkiftFlade(!kodeTilstand)} />
            ) : null}
          </View>

          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            {filtered.length === 0 ? (
              <Text style={styles.empty}>{query ? t('side.noMatches') : t('side.noConversations')}</Text>
            ) : (
              filtered.map((session) => {
                const aktiv = session.id === activeId
                const arbejder = workingIds.includes(session.id)
                const ulaest = Boolean(unreadIds[session.id])
                // Taggets farve foelger desk's trappe: daempet i ro, fuld
                // accent paa den aktive raekke (desk: color-mix 60% -> accent).
                const tagFarve = aktiv ? tokens.color.accent : tokens.color.accentDim
                return (
                  <Pressable
                    key={session.id}
                    accessibilityRole="button"
                    onPress={() => onSelectSession(session.id)}
                    style={({ pressed }) => [
                      styles.sessionRow,
                      aktiv ? styles.sessionActive : null,
                      pressed ? styles.pressed : null
                    ]}
                  >
                    <View style={styles.sessionHoved}>
                      {/* 1. Typen staar FAST til venstre (desk 20/9-2026).
                          Foer havde raekken intet tag, saa en code-session laa
                          i samme liste som en chat uden at nogen kunne se
                          hvilken der var hvilken. */}
                      <View testID={`session-tag-${session.kind === 'code' ? 'code' : 'chat'}`}>
                        {session.kind === 'code'
                          ? <Code2 size={13} color={tagFarve} strokeWidth={2.2} />
                          : <MessageSquare size={13} color={tagFarve} strokeWidth={2.2} />}
                      </View>
                      {/* 2. Titlen fader ud i fladen i stedet for at blive
                          klippet med en haard kant (desk: mask-image). */}
                      <View style={styles.titelRamme}>
                        <Text style={styles.sessionTitle} numberOfLines={1}>
                          {session.title || t('side.newConversation')}
                        </Text>
                        <FadeKant farve={aktiv ? tokens.color.bg3 : tokens.color.bg0} />
                      </View>
                      {/* 3. Pulsen, ikke prikken — og paa sin EGEN plads FOER
                          menuen. Foer laa prikken absolut OVEN over de tre
                          prikker, saa de to signaler stod oven paa hinanden. */}
                      {arbejder || ulaest ? (
                        <View testID={arbejder ? 'session-puls-arbejder' : 'session-puls-ulaest'}>
                          {arbejder
                            ? <AnimeretPuls size={14} farve={tokens.color.accent} />
                            : <PulsIkon size={14} color={tokens.color.accent} />}
                        </View>
                      ) : null}
                      {session.pinned ? (
                        <Pin size={11} color={tokens.color.fg3} strokeWidth={2} />
                      ) : null}
                      {onSessionAction ? (
                        // Egen Pressable OVENPAA raekken, ikke inde i dens onPress:
                        // et tryk paa prikkerne maa ikke ogsaa aabne samtalen.
                        <Pressable
                          testID={`session-menu-${session.id}`}
                          accessibilityRole="button"
                          accessibilityLabel={t('side.sessionActions', { title: session.title || t('side.newConversation') })}
                          hitSlop={10}
                          onPress={() => setMenuFor(session)}
                          style={styles.prikker}
                        >
                          <MoreVertical size={16} color={tokens.color.fg3} strokeWidth={2} />
                        </Pressable>
                      ) : null}
                    </View>
                    <Text style={styles.sessionMeta}>
                      {formatRelativeDate(session.updated_at, now)} · {t('side.messageCount', { count: session.message_count ?? 0 })}
                    </Text>
                  </Pressable>
                )
              })
            )}
            <TeamsPanel config={config} onSelectSession={onSelectSession} />
          </ScrollView>

          {/* Indstillinger NEDERST. Den sad som et af seks ikoner i toppen, hvor
              den konkurrerede med fem genveje man bruger oftere. Nederst er den
              hvor man leder efter den — og fastlaast, saa den ikke ruller vaek. */}
          <Pressable
            testID="open-settings"
            accessibilityRole="button"
            accessibilityLabel={t('settings.title')}
            onPress={onOpenSettings}
            style={({ pressed }) => [styles.felt, styles.feltBund, pressed ? styles.pressed : null]}
          >
            <Settings size={17} color={tokens.color.fg2} strokeWidth={1.8} />
            <Text style={styles.feltTekst}>{t('settings.title')}</Text>
          </Pressable>

          {/* Bundlaget, målt på R4: en lilla pille med blyant + label i
              venstre side, og brugerens initial-cirkel til højre. Den flyder
              OVER listen frem for at ligge i den — så «ny samtale» altid er
              inden for rækkevidde, uanset hvor langt man har rullet. */}
          <View style={styles.dock} pointerEvents="box-none">
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={t('side.newConversation')}
              onPress={onNewSession}
              style={({ pressed }) => [styles.fab, pressed ? styles.pressed : null]}
            >
              <SquarePen size={18} color={tokens.color.bg0} strokeWidth={2} />
              <Text style={styles.fabText}>{t('side.newConversation')}</Text>
            </Pressable>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{initials}</Text>
            </View>
          </View>
        </Animated.View>

        <SessionMenu
          session={menuFor}
          open={Boolean(menuFor)}
          onClose={() => setMenuFor(null)}
          onRename={(id, titel) => onSessionAction?.({ slags: 'rename', id, titel })}
          onDelete={(id) => onSessionAction?.({ slags: 'delete', id })}
          onSetFlags={(id, flags) => onSessionAction?.({ slags: 'flags', id, flags })}
        />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('common.closePanel')}
          style={styles.scrim}
          onPress={onClose}
        />
      </View>
    </Modal>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  overlay: { flex: 1, flexDirection: 'row' },
  // Målt i ChatGPT-appen (R4 + live 2026-09-02): panelet er SORT som resten af
  // appen, ikke en lysere flade, og der er hverken kant mod chatten eller
  // streg under overskriften. Dybden kommer alene af at chatten bag den
  // dæmpes. Det er dét der gør menuen rolig frem for kasse-agtig.
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)' },
  panel: {
    backgroundColor: tokens.color.bg0
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.lg,
    paddingBottom: tokens.spacing.lg
  },
  identity: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm, flexShrink: 1 },
  name: { color: tokens.color.fg1, fontSize: 24, fontWeight: '700', flexShrink: 1 },
  gear: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center', borderRadius: 20, backgroundColor: tokens.color.bg2 },
  prikker: { paddingLeft: 2, paddingVertical: 2 },
  felter: { paddingHorizontal: tokens.spacing.sm, paddingBottom: tokens.spacing.xs },
  felt: {
    flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm,
    paddingVertical: 10, paddingHorizontal: tokens.spacing.sm, borderRadius: 10,
  },
  feltBund: {
    marginHorizontal: tokens.spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: tokens.color.bg2,
    borderRadius: 0, paddingTop: 12,
  },
  feltTekst: { color: tokens.color.fg1, fontSize: 14, flexShrink: 1 },
  // Samme vaerdier som ActivityCenterScreen's egen `styles.badge` — tallet
  // maa ikke se anderledes ud fordi det staar paa knappen i stedet for i
  // skaermen den fører til.
  badge: { color: tokens.color.accentText, fontSize: 12, fontWeight: '800' },
  // `position: relative` alene for at give `feltFejl` noget at vaere
  // absolut i forhold til — ikonet selv fylder ikke mere end foer.
  feltIkon: { position: 'relative' },
  // Samme rødt som DictationBar's `liveDot` (tokens.color.error) — 8px,
  // oeverst til hoejre paa ikonet. Uafhaengig af `badge`-tallet, som
  // Klokke.tsx's `.klokke-fejl` i desk.
  feltFejl: {
    position: 'absolute', top: -2, right: -2,
    width: 8, height: 8, borderRadius: 4,
    backgroundColor: tokens.color.error,
  },
  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    margin: tokens.spacing.md,
    marginBottom: 0,
    paddingHorizontal: tokens.spacing.md,
    height: 40,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg2
  },
  search: { flex: 1, color: tokens.color.fg1, fontSize: 15, padding: 0 },
  body: { padding: tokens.spacing.md, paddingBottom: tokens.spacing.xl },
  dock: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.lg,
    paddingBottom: tokens.spacing.lg,
    paddingTop: tokens.spacing.sm,
    gap: tokens.spacing.md
  },
  fab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    height: 48,
    paddingHorizontal: tokens.spacing.lg,
    borderRadius: tokens.radius.pill,
    backgroundColor: tokens.color.accent
  },
  fabText: { color: tokens.color.bg0, fontWeight: '700', fontSize: 15 },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: tokens.color.bg2,
    alignItems: 'center',
    justifyContent: 'center'
  },
  avatarText: { color: tokens.color.fg1, fontWeight: '700', fontSize: 14 },
  empty: { color: tokens.color.fg3, paddingVertical: tokens.spacing.sm },
  sessionRow: {
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  sessionActive: { backgroundColor: tokens.color.bg3 },
  // Raekkens hovedlinje: tag, titel, puls, menu — samme raekkefoelge som desk.
  // Meta-linjen (dato · antal) staar under den.
  sessionHoved: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  // Titlen ejer den ledige plads, saa fade-kanten kan laegge sig i dens
  // hoejre side. Uden `flex: 1` ville rammen krympe til teksten og fade'en
  // sidde midt i titlen.
  titelRamme: { flex: 1, justifyContent: 'center' },
  fadeKant: { position: 'absolute', right: 0, top: 0, bottom: 0 },
  sessionTitle: { color: tokens.color.fg1, fontWeight: '700' },
  sessionMeta: { color: tokens.color.fg3, marginTop: tokens.spacing.xs, fontSize: 12 },
  pressed: { opacity: 0.7 }
})
