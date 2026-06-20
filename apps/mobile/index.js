import { registerRootComponent } from 'expo'
import messaging from '@react-native-firebase/messaging'
import notifee, { AndroidImportance, EventType } from '@notifee/react-native'
import App from './src/App'
import { display, submitNotificationReply, REPLY_ACTION_ID } from './src/lib/push'
import { loadAuthConfig } from './src/lib/authStore'
import './src/bubble/registerBubble'

// Direct Reply baggrunds-handler: når brugeren svarer fra statusbaren (uden at
// åbne appen) sender vi teksten til sessionens run. Svaret kommer tilbage som en
// ny FCM-notifikation. SKAL registreres uden for komponent-træet.
notifee.onBackgroundEvent(async ({ type, detail }) => {
  if (type === EventType.ACTION_PRESS && detail.pressAction?.id === REPLY_ACTION_ID) {
    const config = await loadAuthConfig()
    if (config && config.authToken) await submitNotificationReply(config, detail)
  }
})

// FCM data-only baggrunds-handler — SKAL registreres uden for komponent-træet
// (kører når appen er i baggrund/dræbt). For answer_ready HENTER vi det faktiske
// svar over HTTPS (samme display() som forgrunden) — Google ser kun vække-signalet,
// aldrig indholdet. Fallback til en generisk notifikation hvis auth mangler.
messaging().setBackgroundMessageHandler(async (msg) => {
  const data = msg.data ?? {}
  try {
    const config = await loadAuthConfig()
    if (config && config.authToken) {
      await display(config, data)
      return
    }
  } catch {
    /* fald igennem til generisk visning nedenfor */
  }
  // Fallback: ingen gemt auth → vis hvad vi har (preview hvis sat).
  const channelId = await notifee.createChannel({
    id: 'jarvis',
    name: 'Jarvis',
    importance: AndroidImportance.HIGH
  })
  const title = data.kind === 'reminder' ? 'Påmindelse' : 'Jarvis'
  await notifee.displayNotification({
    title,
    body: data.preview ?? 'Åbn for at se',
    data,
    android: { channelId, pressAction: { id: 'default' }, smallIcon: 'ic_notification' }
  })
})

// Standard Expo-entry: registrér rod-komponenten fra src/App (appen ligger i src/,
// så Expo's default expo/AppEntry.js's '../../App' fejlede i release-bundlen).
registerRootComponent(App)
