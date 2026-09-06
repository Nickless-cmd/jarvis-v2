import messaging from '@react-native-firebase/messaging'
import notifee, { AndroidImportance, AndroidStyle, EventType } from '@notifee/react-native'
import type { ApiConfig } from './types'
import { ackNotification } from './presence'
import { replyToSession } from './replyToSession'
import { approveTool, cancelRun, denyTool } from './apiClient'
import {
  APPROVE_ACTION_ID,
  DENY_ACTION_ID,
  OPEN_RUN_ACTION_ID,
  STOP_RUN_ACTION_ID,
  notificationActionsFor
} from './notificationActions'

/** id på notifikationens "Svar"-action (Direct Reply / RemoteInput). */
export const REPLY_ACTION_ID = 'jarvis-reply'

export type PushData = { kind: string; session_id?: string; run_id?: string; title?: string; preview?: string; notif_id?: string; severity?: string; message?: string; request_id?: string; capability_name?: string }

/** Pure: byg notifikations-felter ud fra data + (evt.) hentet beskedtekst. Testbar. */
export function buildNotification(data: PushData, fetchedBody: string | null) {
  if (data.kind === 'reminder') {
    return { title: 'Påmindelse', body: data.preview ?? '', data }
  }
  if (data.kind === 'error') {
    // Kanonisk fejl (Canonical Error System): kun kritiske/høje fejl når frem hertil
    // som push. Vis ærligt at noget gik galt, med serverens besked.
    const critical = data.severity === 'critical'
    return {
      title: critical ? 'Jarvis: kritisk fejl' : 'Jarvis stødte på et problem',
      body: data.message ?? data.preview ?? 'Der opstod en fejl.',
      data
    }
  }
  if (data.kind === 'initiative') {
    return { title: 'Jarvis', body: data.preview ?? 'Jarvis vil sige noget', data }
  }
  if (data.kind === 'approval_requested') {
    // Fase 1's leverance-kriterie: Bjørn skal kunne have appen LUKKET og
    // stadig få at vide at noget venter på ham. Uden titel-fallback ville
    // en godkendelse se ud som «Jarvis svarede» og blive læst som småsnak.
    // Serveren sender selv title="Godkendelse kræves" og preview=capability_name
    // (push_dispatcher.on_approval_requested). Brug dem — ellers overskriver
    // klienten serverens ordlyd, og de to kan drive fra hinanden.
    return {
      title: data.title ?? 'Godkendelse kræves',
      body: data.preview ?? data.capability_name ?? 'En handling kræver din godkendelse',
      data
    }
  }
  if (data.kind === 'team_invite') {
    // Backend sender title+preview i payload (commit 45eea82f). Uden denne case
    // faldt team-invites igennem til "Jarvis svarede" (Mikkel-test 2026-06-20).
    return { title: data.title ?? 'Invitation til team', body: data.preview ?? 'Du er blevet inviteret til et team', data }
  }
  if (data.kind === 'answer_ready') {
    // Vis appens egen HTTPS-hentede svar; fald tilbage til serverens medsendte
    // preview hvis fetchLatest fejler (fx udløbet baggrunds-token) — så man ser
    // DET FAKTISKE svar i stedet for et intetsigende "Nyt svar" (Bjørn 3. jul).
    return { title: 'Jarvis svarede', body: fetchedBody ?? data.preview ?? 'Nyt svar', data }
  }
  // Alt ANDET: sig hvad serveren faktisk sendte.
  //
  // Her stod før en catch-all der gav ENHVER ukendt kind titlen «Jarvis svarede».
  // Serveren sender også `central_flag` og `infra_security` (infra-vagtens flag)
  // med felterne `title`/`message` — som den gamle gren slet ikke læste. Resultatet
  // var en strøm af «Jarvis svarede / Nyt svar» hver halve time, hvor Jarvis i
  // virkeligheden meldte om diskpres og en unåelig host. Målt på enheden
  // 2026-09-02: title=«Jarvis svarede», body=«Nyt svar», mens serveren ikke havde
  // afsendt ét eneste answer_ready i fire timer.
  //
  // En notifikation må aldrig påstå noget andet end det, den bærer. Kender vi ikke
  // arten, viser vi serverens egen ordlyd og en neutral titel.
  return {
    title: data.title ?? 'Jarvis',
    body: data.message ?? data.preview ?? 'Der er noget nyt.',
    data
  }
}

async function fetchLatest(config: ApiConfig, sessionId: string): Promise<string | null> {
  try {
    const url = new URL(`/chat/sessions/${encodeURIComponent(sessionId)}`, config.apiBaseUrl).toString()
    const r = await fetch(url, {
      headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {},
    })
    if (!r.ok) return null
    const j = await r.json()
    // GET /chat/sessions/{id} returnerer {session: {..., messages: [...]}} —
    // beskederne ligger NESTED under session (ikke top-niveau).
    const msgs = j.session?.messages ?? j.messages ?? []
    const last = [...msgs].reverse().find((m: { role?: string }) => m.role === 'assistant')
    if (!last) return null
    const c = last.content
    const text =
      typeof c === 'string'
        ? c
        : Array.isArray(c)
          ? c.map((b: { text?: string }) => b.text ?? '').join('')
          : ''
    // Hent rigeligt til den udfoldede notifikation (BigText). Den sammenfoldede
    // linje afkortes selv af Android; udfoldet/ved svar ser man hele svaret.
    return text.slice(0, 500)
  } catch {
    return null
  }
}


/** Er dette en push om en ventende godkendelse? */
export function isApprovalPush(data: { kind?: string } | null | undefined): boolean {
  return String(data?.kind ?? '') === 'approval_requested'
}

/**
 * Blev appen åbnet ved at trykke på en godkendelses-notifikation?
 *
 * Kaldes ved opstart. Bruges til at lande direkte i Arbejde → Godkend frem for
 * i Snak, så trykket fører hen til dét der ventede. Self-safe: kan notifee ikke
 * svare, åbner appen bare normalt.
 */
export async function openedFromApprovalPush(): Promise<boolean> {
  try {
    const initial = await notifee.getInitialNotification()
    return isApprovalPush(initial?.notification?.data as { kind?: string } | undefined)
  } catch {
    return false
  }
}

/**
 * Lyt efter tryk på en godkendelses-notifikation mens appen er åben.
 * Returnerer en afmelder.
 */
export function attachApprovalTapHandler(onOpen: () => void): () => void {
  try {
    return notifee.onForegroundEvent(({ type, detail }) => {
      if (type !== EventType.PRESS) return
      if (isApprovalPush(detail.notification?.data as { kind?: string } | undefined)) onOpen()
    })
  } catch {
    return () => {}
  }
}

export async function display(config: ApiConfig, data: PushData) {
  const body = data.session_id ? await fetchLatest(config, data.session_id) : null
  const n = buildNotification(data, body)
  const channelId = await notifee.createChannel({
    id: 'jarvis',
    name: 'Jarvis',
    importance: AndroidImportance.HIGH,
  })
  await notifee.displayNotification({
    title: n.title,
    body: n.body,
    data: n.data as Record<string, string>,
    android: {
      channelId,
      pressAction: { id: 'default' },
      smallIcon: 'ic_notification',
      // BigText: udfoldet (eller ved svar) vises hele beskeden, ikke kun 1-2 linjer
      // — så man kan se hvad man svarer på.
      style: { type: AndroidStyle.BIGTEXT, text: n.body },
      // Direct Reply: svar Jarvis direkte fra statusbaren uden at åbne appen.
      // IKKE på godkendelser: et fritekstsvar er ikke et ja/nej, og en
      // «Svar»-knap dér ville love noget serveren ikke kan tage imod.
      actions: isApprovalPush(data)
        ? notificationActionsFor(data)
        : [
            ...notificationActionsFor(data),
            {
              title: 'Svar',
              pressAction: { id: REPLY_ACTION_ID },
              input: { allowFreeFormInput: true, placeholder: 'Skriv til Jarvis…' }
            }
          ]
    },
  })
  // Device-awareness: kvittér så serveren ved beskeden nåede mobilen (annullerer
  // eskalering til en anden enhed). Best-effort.
  if (data.notif_id) void ackNotification(config, data.notif_id)
}

const RUN_NOTIFICATION_ID = 'jarvis-active-run'

export async function showRunInProgressNotification(sessionId?: string, runId?: string): Promise<void> {
  try {
    const channelId = await notifee.createChannel({
      id: 'jarvis',
      name: 'Jarvis',
      importance: AndroidImportance.HIGH,
    })
    await notifee.displayNotification({
      id: RUN_NOTIFICATION_ID,
      title: 'Jarvis arbejder',
      body: 'Du kan lukke skærmen. Runnet fortsætter på serveren.',
      data: {
        kind: 'run_in_progress',
        ...(sessionId ? { session_id: sessionId } : {}),
        ...(runId ? { run_id: runId } : {})
      },
      android: {
        channelId,
        pressAction: { id: 'default' },
        smallIcon: 'ic_notification',
        ongoing: true,
        autoCancel: false,
        actions: notificationActionsFor({ kind: 'run_in_progress', run_id: runId })
      }
    })
  } catch {
    /* notification er hjælp, ikke run-sandhed */
  }
}

export async function clearRunInProgressNotification(): Promise<void> {
  try {
    await notifee.cancelNotification(RUN_NOTIFICATION_ID)
  } catch {
    /* best-effort */
  }
}

/**
 * Håndtér et notifee ACTION_PRESS-svar (Direct Reply): send teksten til
 * sessionens run + erstat notifikationen med en kvittering. Kaldes fra både
 * baggrunds- (index.js) og forgrunds-handleren (ChatScreen).
 */
export async function submitNotificationReply(
  config: ApiConfig,
  detail: { notification?: { id?: string; data?: Record<string, unknown> }; input?: string }
): Promise<void> {
  const text = (detail.input ?? '').trim()
  const sid =
    typeof detail.notification?.data?.session_id === 'string'
      ? (detail.notification.data.session_id as string)
      : ''
  if (!text || !sid) return
  const ok = await replyToSession(config, sid, text)
  const channelId = await notifee.createChannel({
    id: 'jarvis',
    name: 'Jarvis',
    importance: AndroidImportance.HIGH
  })
  await notifee.displayNotification({
    id: detail.notification?.id,
    title: ok ? 'Sendt ✓' : 'Kunne ikke sende',
    body: ok ? text : 'Prøv igen fra appen',
    data: (detail.notification?.data ?? {}) as Record<string, string>,
    android: { channelId, pressAction: { id: 'default' }, smallIcon: 'ic_notification' }
  })
}

export async function handleNotificationAction(
  config: ApiConfig,
  detail: { notification?: { id?: string; data?: Record<string, unknown> }; pressAction?: { id?: string }; input?: string }
): Promise<'handled' | 'open' | 'ignored'> {
  const action = detail.pressAction?.id
  const data = detail.notification?.data ?? {}
  if (action === REPLY_ACTION_ID) {
    await submitNotificationReply(config, detail)
    return 'handled'
  }
  if (action === STOP_RUN_ACTION_ID) {
    const runId = typeof data.run_id === 'string' ? data.run_id : ''
    if (runId) await cancelRun(config, runId)
    return runId ? 'handled' : 'ignored'
  }
  if (action === APPROVE_ACTION_ID || action === DENY_ACTION_ID) {
    const approvalId = typeof data.request_id === 'string' ? data.request_id : ''
    if (!approvalId) return 'ignored'
    if (action === APPROVE_ACTION_ID) await approveTool(config, approvalId)
    else await denyTool(config, approvalId)
    return 'handled'
  }
  if (action === OPEN_RUN_ACTION_ID || action === 'default') return 'open'
  return 'ignored'
}

async function postToken(config: ApiConfig, token: string) {
  const url = new URL('/push/register', config.apiBaseUrl).toString()
  await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
    },
    body: JSON.stringify({ token, platform: 'android' }),
  })
}

/** Registrér token efter login + lyt på rotation. */
export async function registerForPush(config: ApiConfig): Promise<void> {
  try {
    // notifee.requestPermission() udløser Android 13+'s POST_NOTIFICATIONS-dialog
    // (messaging().requestPermission() gør det IKKE pålideligt på Android).
    await notifee.requestPermission()
    await messaging().requestPermission()
    const token = await messaging().getToken()
    await postToken(config, token)
    messaging().onTokenRefresh((t: string) => {
      void postToken(config, t)
    })
  } catch {
    /* graceful: ingen push, in-app virker stadig */
  }
}

/** Kald i forgrunden (app åben). Returnerer unsubscribe. */
export function attachForegroundHandler(config: ApiConfig) {
  return messaging().onMessage(async (msg) => {
    await display(config, (msg.data ?? {}) as unknown as PushData)
  })
}
