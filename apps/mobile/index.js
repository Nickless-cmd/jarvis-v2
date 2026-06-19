import { registerRootComponent } from 'expo'
import messaging from '@react-native-firebase/messaging'
import notifee, { AndroidImportance } from '@notifee/react-native'
import App from './src/App'

// FCM data-only baggrunds-handler — SKAL registreres uden for komponent-træet
// (kører når appen er i baggrund/dræbt). Viser straks en native notifikation med
// preview; appen henter fuld tekst ved tap/åbning. Google ser kun data, intet indhold.
messaging().setBackgroundMessageHandler(async (msg) => {
  const data = msg.data ?? {}
  const channelId = await notifee.createChannel({
    id: 'jarvis',
    name: 'Jarvis',
    importance: AndroidImportance.HIGH
  })
  const title = data.kind === 'reminder' ? 'Påmindelse' : 'Jarvis svarede'
  await notifee.displayNotification({
    title,
    body: data.preview ?? 'Nyt fra Jarvis',
    data,
    android: { channelId, pressAction: { id: 'default' }, smallIcon: 'ic_notification' }
  })
})

// Standard Expo-entry: registrér rod-komponenten fra src/App (appen ligger i src/,
// så Expo's default expo/AppEntry.js's '../../App' fejlede i release-bundlen).
registerRootComponent(App)
