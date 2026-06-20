import { registerRootComponent } from 'expo'
import messaging from '@react-native-firebase/messaging'
import notifee, { AndroidImportance } from '@notifee/react-native'
import App from './src/App'
import { display } from './src/lib/push'
import { loadAuthConfig } from './src/lib/authStore'
import { bubble } from './src/lib/bubbleModule'
import { shouldFloatOnPush } from './src/lib/bubbleTrigger'
import './src/bubble/registerBubble'

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
      if (shouldFloatOnPush(data)) {
        bubble.showConversationBubble(data.session_id, data.title ?? 'Jarvis', data.preview ?? 'Nyt svar')
      }
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
