# Mobil Chatboble (Android Bubbles API) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** En ægte Android system-boble (Bubbles API, Android 11+) hvor Bjørn kan tale med Jarvis i en flydende boble oven på andre apps — proaktivt (Jarvis-besked → floatbar samtale-boble), manuelt ("flyt denne chat") og vedvarende (toggle).

**Architecture:** Tilgang A — `BubbleActivity extends ReactActivity` med en anden registreret JS-komponent (`JarvisBubble`) der deler bridge med hovedappen og renderer en kompakt udgave af samme RN-chat mod samme backend-session. Native Kotlin håndterer Bubbles-VVS (Person + long-lived conversation-shortcut + MessagingStyle-notifikation med BubbleMetadata). Ingen backend-ændringer.

**Tech Stack:** React Native/Expo bare (New Architecture), Kotlin (pakke `dk.srvlab.jarvis.mobile`), androidx core Bubbles/Shortcuts API, jest (jest-expo) + `tsc --noEmit`.

**Stier & regler:**
- Alt i `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile`. Gren `codex/jarvis-mobile-companion-v1`.
- Kommandoer kører fra `apps/mobile`. Commit ALTID via `git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 …`.
- Brug **lokale** binærer: `./node_modules/.bin/jest`, `./node_modules/.bin/tsc` (en global `npx jest/tsc` rammer en forkert version).
- `android/` er checket ind og bygges med gradlew (INGEN `expo prebuild`) → native filer redigeres direkte.
- Eksisterende ~104 jest-tests SKAL forblive grønne; `tsc --noEmit` rent.
- Spec: `docs/superpowers/specs/2026-06-20-mobile-chatbubble-design.md`.

---

## File Structure

**Native (ny, Kotlin, `android/app/src/main/java/dk/srvlab/jarvis/mobile/`):**
- `BubbleActivity.kt` — ReactActivity der renderer `JarvisBubble` + giver `sessionId`/`title` som initialProps.
- `BubbleModule.kt` — `@ReactMethod`-API: isSupported/floatCurrentChat/showConversationBubble/setPersistent + Bubbles-VVS.
- `BubblePackage.kt` — ReactPackage der eksponerer BubbleModule.

**Native (modificeret):**
- `MainApplication.kt` — registrér `BubblePackage` i packageList.
- `android/app/src/main/AndroidManifest.xml` — BubbleActivity-entry.

**JS (ny):**
- `src/lib/bubbleTrigger.ts` (+ `.test.ts`) — ren logik: `shouldFloatOnPush`.
- `src/lib/bubbleModule.ts` (+ `.test.ts`) — TS-wrapper + guard over `NativeModules.BubbleModule`.
- `src/bubble/BubbleChat.tsx` — kompakt 1-session-chat + root.
- `src/bubble/registerBubble.tsx` — `AppRegistry.registerComponent('JarvisBubble', …)`.

**JS (modificeret):**
- `index.js` — import af registerBubble + float-på-FCM i baggrundshandler.
- `src/lib/push.ts` — float-på-FCM i forgrund.
- `src/components/SidePanel.tsx` — "flyt denne chat"-knap.
- `src/screens/SettingsScreen.tsx` — persistent-boble-toggle.

---

## Task 1: `bubbleTrigger.ts` — hvornår skal en push blive en boble

**Files:**
- Create: `src/lib/bubbleTrigger.ts`
- Test: `src/lib/bubbleTrigger.test.ts`

- [ ] **Step 1: Write the failing test**

`src/lib/bubbleTrigger.test.ts`:

```typescript
import { shouldFloatOnPush } from './bubbleTrigger'

describe('shouldFloatOnPush', () => {
  it('true for answer_ready', () => {
    expect(shouldFloatOnPush({ kind: 'answer_ready', session_id: 's1' })).toBe(true)
  })
  it('true for reminder', () => {
    expect(shouldFloatOnPush({ kind: 'reminder', session_id: 's1' })).toBe(true)
  })
  it('false for presence', () => {
    expect(shouldFloatOnPush({ kind: 'presence', session_id: 's1' })).toBe(false)
  })
  it('false uden session_id', () => {
    expect(shouldFloatOnPush({ kind: 'answer_ready' })).toBe(false)
  })
  it('false for malformet/tom', () => {
    expect(shouldFloatOnPush({})).toBe(false)
    expect(shouldFloatOnPush(undefined as unknown as Record<string, string>)).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./node_modules/.bin/jest src/lib/bubbleTrigger.test.ts`
Expected: FAIL — `Cannot find module './bubbleTrigger'`

- [ ] **Step 3: Write minimal implementation**

`src/lib/bubbleTrigger.ts`:

```typescript
/** Afgør om en indkommende FCM-data-besked skal blive en floatbar samtale-boble.
 *  Kun de proaktive Jarvis-beskeder (svar/påmindelse) med en session floates. */
const FLOAT_KINDS = new Set(['answer_ready', 'reminder'])

export function shouldFloatOnPush(data: Record<string, string> | undefined): boolean {
  if (!data) return false
  const kind = data.kind ?? ''
  const sessionId = data.session_id ?? ''
  return FLOAT_KINDS.has(kind) && sessionId.length > 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./node_modules/.bin/jest src/lib/bubbleTrigger.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/bubbleTrigger.ts apps/mobile/src/lib/bubbleTrigger.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): bubbleTrigger.shouldFloatOnPush"
```

---

## Task 2: `bubbleModule.ts` — TS-wrapper + guard over native

**Files:**
- Create: `src/lib/bubbleModule.ts`
- Test: `src/lib/bubbleModule.test.ts`

Den native `BubbleModule` findes først efter en ny native build. Wrapperen skal være no-op/false hvis modulet mangler (jest, iOS, gammel build).

- [ ] **Step 1: Write the failing test**

`src/lib/bubbleModule.test.ts`:

```typescript
import { bubble } from './bubbleModule'

// I jest findes NativeModules.BubbleModule ikke → guard skal aktiveres.
describe('bubbleModule guard (intet native modul)', () => {
  it('isSupported → false uden native modul', async () => {
    expect(await bubble.isSupported()).toBe(false)
  })
  it('float/show/setPersistent kaster ikke', () => {
    expect(() => bubble.floatCurrentChat('s1', 'Titel')).not.toThrow()
    expect(() => bubble.showConversationBubble('s1', 'Titel', 'Hej')).not.toThrow()
    expect(() => bubble.setPersistent(true, 's1', 'Titel')).not.toThrow()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./node_modules/.bin/jest src/lib/bubbleModule.test.ts`
Expected: FAIL — `Cannot find module './bubbleModule'`

- [ ] **Step 3: Write minimal implementation**

`src/lib/bubbleModule.ts`:

```typescript
import { NativeModules } from 'react-native'

interface BubbleNative {
  isSupported(): Promise<boolean>
  floatCurrentChat(sessionId: string, title: string): void
  showConversationBubble(sessionId: string, title: string, body: string): void
  setPersistent(enabled: boolean, sessionId: string, title: string): void
}

const native: BubbleNative | undefined = NativeModules.BubbleModule

/** Tynd, sikker wrapper. Hvis det native modul mangler (iOS/gammel build/jest)
 *  bliver alt no-op og isSupported() → false. */
export const bubble = {
  async isSupported(): Promise<boolean> {
    if (!native) return false
    try {
      return await native.isSupported()
    } catch {
      return false
    }
  },
  floatCurrentChat(sessionId: string, title: string): void {
    try {
      native?.floatCurrentChat(sessionId, title)
    } catch {
      /* no-op */
    }
  },
  showConversationBubble(sessionId: string, title: string, body: string): void {
    try {
      native?.showConversationBubble(sessionId, title, body)
    } catch {
      /* no-op */
    }
  },
  setPersistent(enabled: boolean, sessionId: string, title: string): void {
    try {
      native?.setPersistent(enabled, sessionId, title)
    } catch {
      /* no-op */
    }
  },
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./node_modules/.bin/jest src/lib/bubbleModule.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/bubbleModule.ts apps/mobile/src/lib/bubbleModule.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): bubbleModule TS-wrapper m. guard"
```

---

## Task 3: `BubbleActivity.kt` — ReactActivity for boblen

**Files:**
- Create: `android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleActivity.kt`

Spejler `MainActivity.kt`'s delegate-opsætning (New Architecture-wrapper), men renderer `JarvisBubble` og sender intent-extras videre som initialProps.

- [ ] **Step 1: Write the Activity**

`android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleActivity.kt`:

```kotlin
package dk.srvlab.jarvis.mobile

import android.os.Bundle

import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate

import expo.modules.ReactActivityDelegateWrapper

class BubbleActivity : ReactActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    setTheme(R.style.AppTheme)
    super.onCreate(null)
  }

  override fun getMainComponentName(): String = "JarvisBubble"

  override fun createReactActivityDelegate(): ReactActivityDelegate {
    return ReactActivityDelegateWrapper(
      this,
      BuildConfig.IS_NEW_ARCHITECTURE_ENABLED,
      object : DefaultReactActivityDelegate(this, mainComponentName, fabricEnabled) {
        override fun getLaunchOptions(): Bundle {
          return Bundle().apply {
            putString("sessionId", intent?.getStringExtra("sessionId") ?: "")
            putString("title", intent?.getStringExtra("title") ?: "")
          }
        }
      }
    )
  }
}
```

- [ ] **Step 2: Verificér Kotlin-syntaks (kompileres i Task 9-build; her kun lokal sanity)**

Run: `grep -c "class BubbleActivity" android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleActivity.kt`
Expected: `1`

- [ ] **Step 3: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleActivity.kt
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): BubbleActivity (ReactActivity for JarvisBubble)"
```

---

## Task 4: `BubbleModule.kt` + `BubblePackage.kt` — Bubbles-VVS

**Files:**
- Create: `android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleModule.kt`
- Create: `android/app/src/main/java/dk/srvlab/jarvis/mobile/BubblePackage.kt`

- [ ] **Step 1: Skriv BubbleModule**

`android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleModule.kt`:

```kotlin
package dk.srvlab.jarvis.mobile

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build

import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.Person
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat

import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class BubbleModule(private val ctx: ReactApplicationContext) : ReactContextBaseJavaModule(ctx) {
  override fun getName(): String = "BubbleModule"

  private val channelId = "jarvis-bubbles"

  private fun ensureChannel() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
    val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    if (nm.getNotificationChannel(channelId) == null) {
      val ch = NotificationChannel(channelId, "Jarvis-bobler", NotificationManager.IMPORTANCE_HIGH)
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) ch.setAllowBubbles(true)
      nm.createNotificationChannel(ch)
    }
  }

  private fun person(): Person =
    Person.Builder()
      .setName("Jarvis")
      .setKey("jarvis")
      .setImportant(true)
      .setIcon(IconCompat.createWithResource(ctx, R.drawable.ic_notification))
      .build()

  private fun pushShortcut(sessionId: String, title: String): String {
    val shortcutId = "bubble-$sessionId"
    val intent = Intent(ctx, BubbleActivity::class.java).apply {
      action = Intent.ACTION_VIEW
      putExtra("sessionId", sessionId)
      putExtra("title", title)
    }
    val shortcut = ShortcutInfoCompat.Builder(ctx, shortcutId)
      .setLongLived(true)
      .setShortLabel(if (title.isBlank()) "Jarvis" else title)
      .setPerson(person())
      .setCategories(setOf("android.shortcut.conversation"))
      .setIntent(intent)
      .build()
    ShortcutManagerCompat.pushDynamicShortcut(ctx, shortcut)
    return shortcutId
  }

  private fun pendingFlags(): Int {
    val base = PendingIntent.FLAG_UPDATE_CURRENT
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) base or PendingIntent.FLAG_MUTABLE else base
  }

  private fun postBubble(
    sessionId: String,
    title: String,
    body: String,
    autoExpand: Boolean,
    suppress: Boolean,
    ongoing: Boolean
  ) {
    ensureChannel()
    val shortcutId = pushShortcut(sessionId, title)
    val intent = Intent(ctx, BubbleActivity::class.java).apply {
      action = Intent.ACTION_VIEW
      putExtra("sessionId", sessionId)
      putExtra("title", title)
    }
    val pi = PendingIntent.getActivity(ctx, sessionId.hashCode(), intent, pendingFlags())
    val icon = IconCompat.createWithResource(ctx, R.drawable.ic_notification)
    val bubble = NotificationCompat.BubbleMetadata.Builder(pi, icon)
      .setDesiredHeight(600)
      .setAutoExpandBubble(autoExpand)
      .setSuppressNotification(suppress)
      .build()
    val msgStyle = NotificationCompat.MessagingStyle(person())
      .addMessage(if (body.isBlank()) "Jarvis" else body, System.currentTimeMillis(), person())
    val notif = NotificationCompat.Builder(ctx, channelId)
      .setSmallIcon(R.drawable.ic_notification)
      .setShortcutId(shortcutId)
      .setBubbleMetadata(bubble)
      .setStyle(msgStyle)
      .setOngoing(ongoing)
      .build()
    NotificationManagerCompat.from(ctx).notify(sessionId.hashCode(), notif)
  }

  @ReactMethod
  fun isSupported(promise: Promise) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
      promise.resolve(false)
      return
    }
    val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    promise.resolve(nm.areBubblesAllowed())
  }

  @ReactMethod
  fun floatCurrentChat(sessionId: String, title: String) {
    postBubble(sessionId, title, "Chat med Jarvis", autoExpand = true, suppress = true, ongoing = false)
  }

  @ReactMethod
  fun showConversationBubble(sessionId: String, title: String, body: String) {
    postBubble(sessionId, title, body, autoExpand = false, suppress = false, ongoing = false)
  }

  @ReactMethod
  fun setPersistent(enabled: Boolean, sessionId: String, title: String) {
    val id = if (sessionId.isBlank()) "default" else sessionId
    if (enabled) {
      postBubble(id, title, "Chat med Jarvis", autoExpand = false, suppress = false, ongoing = true)
    } else {
      NotificationManagerCompat.from(ctx).cancel(id.hashCode())
    }
  }
}
```

- [ ] **Step 2: Skriv BubblePackage**

`android/app/src/main/java/dk/srvlab/jarvis/mobile/BubblePackage.kt`:

```kotlin
package dk.srvlab.jarvis.mobile

import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager

class BubblePackage : ReactPackage {
  override fun createNativeModules(reactContext: ReactApplicationContext): List<NativeModule> =
    listOf(BubbleModule(reactContext))

  override fun createViewManagers(reactContext: ReactApplicationContext): List<ViewManager<*, *>> =
    emptyList()
}
```

- [ ] **Step 3: Sanity-check**

Run: `grep -c "@ReactMethod" android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleModule.kt`
Expected: `4`

- [ ] **Step 4: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/android/app/src/main/java/dk/srvlab/jarvis/mobile/BubbleModule.kt apps/mobile/android/app/src/main/java/dk/srvlab/jarvis/mobile/BubblePackage.kt
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): BubbleModule + BubblePackage (Bubbles-VVS)"
```

---

## Task 5: Registrér package + manifest-entry

**Files:**
- Modify: `android/app/src/main/java/dk/srvlab/jarvis/mobile/MainApplication.kt`
- Modify: `android/app/src/main/AndroidManifest.xml`

- [ ] **Step 1: Registrér BubblePackage i MainApplication**

I `MainApplication.kt`, find blokken:

```kotlin
        PackageList(this).packages.apply {
          // Packages that cannot be autolinked yet can be added manually here, for example:
          // add(MyReactNativePackage())
        }
```

Ændr `apply`-blokken til:

```kotlin
        PackageList(this).packages.apply {
          // Packages that cannot be autolinked yet can be added manually here, for example:
          // add(MyReactNativePackage())
          add(BubblePackage())
        }
```

- [ ] **Step 2: Tilføj BubbleActivity til manifestet**

I `android/app/src/main/AndroidManifest.xml`, find `</application>`-tag'en og indsæt umiddelbart FØR den:

```xml
    <activity
      android:name=".BubbleActivity"
      android:exported="true"
      android:resizeableActivity="true"
      android:allowEmbedded="true"
      android:documentLaunchMode="always"
      android:taskAffinity=""
      android:theme="@style/AppTheme"
      android:configChanges="keyboard|keyboardHidden|orientation|screenSize|uiMode|smallestScreenSize" />
```

- [ ] **Step 3: Verificér XML + registrering**

Run: `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('android/app/src/main/AndroidManifest.xml'); print('xml ok')" && grep -c "add(BubblePackage())" android/app/src/main/java/dk/srvlab/jarvis/mobile/MainApplication.kt`
Expected: `xml ok` efterfulgt af `1`

- [ ] **Step 4: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/android/app/src/main/java/dk/srvlab/jarvis/mobile/MainApplication.kt apps/mobile/android/app/src/main/AndroidManifest.xml
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): registrér BubblePackage + BubbleActivity i manifest"
```

---

## Task 6: `BubbleChat.tsx` + `registerBubble.tsx` — kompakt chat i boblen

**Files:**
- Create: `src/bubble/BubbleChat.tsx`
- Create: `src/bubble/registerBubble.tsx`
- Modify: `index.js`

Genbruger `AuthProvider`/`SessionProvider`/`StreamProvider` + `MessageList` + `Composer` præcis som ChatScreen (`messages={sessions.messages} blocks={stream.state.blocks}`, `working={stream.state.status === 'working'}`), uden side-panel/save-rail/presence.

- [ ] **Step 1: Skriv BubbleChat**

`src/bubble/BubbleChat.tsx`:

```tsx
import { useEffect } from 'react'
import { ActivityIndicator, StatusBar, StyleSheet, Text, View } from 'react-native'
import { SafeAreaProvider, SafeAreaView, initialWindowMetrics } from 'react-native-safe-area-context'
import { MessageList } from '../components/MessageList'
import { Composer } from '../components/Composer'
import { AuthProvider, useAuth } from '../state/AuthContext'
import { SessionProvider, useSessions } from '../state/SessionContext'
import { StreamProvider, useStream } from '../state/StreamContext'
import { tokens } from '../theme/tokens'

/** Kompakt 1-session-chat. Henter sessionen, viser beskeder + composer,
 *  sender via samme stream som hovedappen (server-autoritativ session). */
function BubbleChat({ sessionId, title }: { sessionId: string; title: string }) {
  const { config } = useAuth()
  const sessions = useSessions()
  const stream = useStream()

  useEffect(() => {
    if (config && sessionId) void sessions.select(config, sessionId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.authToken, sessionId])

  const onSend = (text: string) => {
    if (config && sessionId) stream.send(config, sessionId, text)
  }

  return (
    <View style={styles.chat}>
      <Text style={styles.title} numberOfLines={1}>
        {title || 'Jarvis'}
      </Text>
      <View style={styles.list}>
        <MessageList messages={sessions.messages} blocks={stream.state.blocks} />
      </View>
      <Composer onSend={onSend} working={stream.state.status === 'working'} />
    </View>
  )
}

function BubbleBody({ sessionId, title }: { sessionId: string; title: string }) {
  const { config, loading } = useAuth()
  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={tokens.color.accent} />
      </View>
    )
  }
  if (!config) {
    return (
      <View style={styles.center}>
        <Text style={styles.hint}>Åbn appen og log ind for at chatte i boblen.</Text>
      </View>
    )
  }
  return (
    <SessionProvider key={JSON.stringify([config.apiBaseUrl, config.authToken])}>
      <StreamProvider>
        <BubbleChat sessionId={sessionId} title={title} />
      </StreamProvider>
    </SessionProvider>
  )
}

/** Root-komponent registreret som "JarvisBubble". Modtager initialProps
 *  {sessionId, title} fra BubbleActivity. */
export function BubbleChatRoot(props: { sessionId?: string; title?: string }) {
  return (
    <SafeAreaProvider initialMetrics={initialWindowMetrics}>
      <AuthProvider>
        <SafeAreaView style={styles.root}>
          <StatusBar barStyle="light-content" />
          <BubbleBody sessionId={props.sessionId ?? ''} title={props.title ?? ''} />
        </SafeAreaView>
      </AuthProvider>
    </SafeAreaProvider>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  chat: { flex: 1 },
  title: {
    color: tokens.color.fg1,
    fontWeight: '700',
    fontSize: 15,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1,
  },
  list: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: tokens.spacing.lg },
  hint: { color: tokens.color.fg2, textAlign: 'center' },
})
```

- [ ] **Step 2: Skriv registerBubble (side-effekt: registrér komponent)**

`src/bubble/registerBubble.tsx`:

```tsx
import { AppRegistry } from 'react-native'
import { BubbleChatRoot } from './BubbleChat'

// Registrér boble-roden ved siden af 'main'. BubbleActivity renderer denne.
AppRegistry.registerComponent('JarvisBubble', () => BubbleChatRoot)
```

- [ ] **Step 3: Importér registerBubble i index.js**

I `index.js`, tilføj efter de eksisterende imports (fx efter `import { loadAuthConfig } from './src/lib/authStore'`):

```javascript
import './src/bubble/registerBubble'
```

- [ ] **Step 4: tsc + jest (intet brækket)**

Run: `./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/jest 2>&1 | tail -5`
Expected: tsc rent; alle suites grønne

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/bubble/BubbleChat.tsx apps/mobile/src/bubble/registerBubble.tsx apps/mobile/index.js
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): BubbleChat kompakt chat + registrér JarvisBubble"
```

---

## Task 7: Float-på-FCM (proaktiv boble)

**Files:**
- Modify: `index.js` (baggrundshandler)
- Modify: `src/lib/push.ts` (forgrund)

- [ ] **Step 1: Float i baggrundshandleren**

I `index.js`, i `messaging().setBackgroundMessageHandler(async (msg) => { … })`, efter `const data = msg.data ?? {}` og det eksisterende `display(config, data)`-kald, tilføj float-logik. Find:

```javascript
    const config = await loadAuthConfig()
    if (config && config.authToken) {
      await display(config, data)
      return
    }
```

Ændr til (importér helpers øverst — se Step 3):

```javascript
    const config = await loadAuthConfig()
    if (config && config.authToken) {
      await display(config, data)
      if (shouldFloatOnPush(data)) {
        bubble.showConversationBubble(data.session_id, data.title ?? 'Jarvis', data.preview ?? 'Nyt svar')
      }
      return
    }
```

- [ ] **Step 2: Float i forgrunden (push.ts)**

I `src/lib/push.ts`, i `display(config, data)` (omkring linje 46), efter notifikationen vises, tilføj float. Find slutningen af `display`-funktionen og indsæt før den returnerer / efter `notifee.displayNotification(...)`:

```typescript
  if (shouldFloatOnPush(data)) {
    bubble.showConversationBubble(data.session_id ?? '', data.title ?? 'Jarvis', data.preview ?? 'Nyt svar')
  }
```

Tilføj imports øverst i `src/lib/push.ts`:

```typescript
import { bubble } from './bubbleModule'
import { shouldFloatOnPush } from './bubbleTrigger'
```

- [ ] **Step 3: Tilføj imports i index.js**

I `index.js`, tilføj efter de eksisterende imports:

```javascript
import { bubble } from './src/lib/bubbleModule'
import { shouldFloatOnPush } from './src/lib/bubbleTrigger'
```

- [ ] **Step 4: tsc + jest**

Run: `./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/jest 2>&1 | tail -5`
Expected: tsc rent; alle suites grønne (bubble er no-op i jest)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/index.js apps/mobile/src/lib/push.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): float proaktiv samtale-boble på FCM (for/baggrund)"
```

---

## Task 8: "Flyt denne chat"-knap i SidePanel

**Files:**
- Modify: `src/components/SidePanel.tsx`

SidePanel har allerede `activeId` + `sessions` + `onSelectSession`. Vi tilføjer en lille boble-knap i headeren der floater den aktive session. Knappen skjules hvis bobler ikke understøttes.

- [ ] **Step 1: Tilføj props + støtte-state**

I `SidePanel`-komponentens props-objekt (efter `onOpenSettings: () => void`), tilføj:

```typescript
  onFloatActive?: () => void
  bubbleSupported?: boolean
```

og i destructureringen øverst tilføj `onFloatActive` og `bubbleSupported = false`.

- [ ] **Step 2: Tilføj boble-knap i header-rækken**

I `SidePanel`, i `styles.headerRow`-`View`'en, mellem identitet-`Pressable` og tandhjul-`Pressable`, indsæt (kun når understøttet + der er en aktiv session):

```tsx
            {bubbleSupported && activeId ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Flyt chat til boble"
                onPress={onFloatActive}
                hitSlop={8}
                style={styles.gear}
              >
                <Text style={styles.gearIcon}>🫧</Text>
              </Pressable>
            ) : null}
```

- [ ] **Step 3: Wire i ChatScreen (kalder bubble)**

I `src/screens/ChatScreen.tsx`, tilføj import:

```typescript
import { bubble } from '../lib/bubbleModule'
```

Tilføj state + opslag (efter de eksisterende `useState`-linjer i `ChatScreen`):

```typescript
  const [bubbleSupported, setBubbleSupported] = useState(false)
  useEffect(() => { void bubble.isSupported().then(setBubbleSupported) }, [])
```

Find `<SidePanel`-elementet og tilføj props:

```tsx
          bubbleSupported={bubbleSupported}
          onFloatActive={() => {
            const id = sessions.activeId
            if (!id) return
            const title = (sessions.sessions ?? []).find((s) => s.id === id)?.title || 'Jarvis'
            bubble.floatCurrentChat(id, title)
          }}
```

- [ ] **Step 4: tsc + jest**

Run: `./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/jest 2>&1 | tail -5`
Expected: tsc rent; alle suites grønne (eksisterende SidePanel.test + ChatScreen.test forbliver grønne — nye props er valgfri)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/SidePanel.tsx apps/mobile/src/screens/ChatScreen.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): 'flyt denne chat'-knap i SidePanel"
```

---

## Task 9: Persistent-boble-toggle i Settings

**Files:**
- Modify: `src/screens/SettingsScreen.tsx`
- Create: `src/lib/bubbleSetting.ts` (+ `.test.ts`) — persistér toggle-tilstand

- [ ] **Step 1: Write failing test for setting-persist**

`src/lib/bubbleSetting.test.ts`:

```typescript
import { parseBubblePersist } from './bubbleSetting'

describe('parseBubblePersist', () => {
  it('"1" → true', () => expect(parseBubblePersist('1')).toBe(true))
  it('"0" → false', () => expect(parseBubblePersist('0')).toBe(false))
  it('null → false', () => expect(parseBubblePersist(null)).toBe(false))
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./node_modules/.bin/jest src/lib/bubbleSetting.test.ts`
Expected: FAIL — `Cannot find module './bubbleSetting'`

- [ ] **Step 3: Implementér bubbleSetting**

`src/lib/bubbleSetting.ts`:

```typescript
import * as SecureStore from 'expo-secure-store'

const KEY = 'jarvis.mobile.bubblePersist'

/** Ren parser (testbar) — "1" = til. */
export function parseBubblePersist(raw: string | null): boolean {
  return raw === '1'
}

export async function loadBubblePersist(): Promise<boolean> {
  try {
    return parseBubblePersist(await SecureStore.getItemAsync(KEY))
  } catch {
    return false
  }
}

export async function saveBubblePersist(on: boolean): Promise<void> {
  try {
    await SecureStore.setItemAsync(KEY, on ? '1' : '0')
  } catch {
    /* no-op */
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./node_modules/.bin/jest src/lib/bubbleSetting.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Tilføj toggle i SettingsScreen**

I `src/screens/SettingsScreen.tsx`, tilføj imports:

```typescript
import { Switch } from 'react-native'
import { bubble } from '../lib/bubbleModule'
import { loadBubblePersist, saveBubblePersist } from '../lib/bubbleSetting'
```

Tilføj state + init (i komponentens top):

```typescript
  const [persistBubble, setPersistBubble] = useState(false)
  const [bubbleOk, setBubbleOk] = useState(false)
  useEffect(() => { void bubble.isSupported().then(setBubbleOk) }, [])
  useEffect(() => { void loadBubblePersist().then(setPersistBubble) }, [])
```

Tilføj en sektion i render (kun hvis understøttet) — placér ved de øvrige indstillinger:

```tsx
        {bubbleOk ? (
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Vedvarende Jarvis-boble</Text>
            <Switch
              value={persistBubble}
              onValueChange={(on) => {
                setPersistBubble(on)
                void saveBubblePersist(on)
                bubble.setPersistent(on, '', 'Jarvis')
              }}
            />
          </View>
        ) : null}
```

(Bemærk: `styles.row`/`styles.rowLabel` — hvis de ikke findes i SettingsScreen, brug nærmeste eksisterende række-stil i filen; tilføj ellers `row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: tokens.spacing.md }` og `rowLabel: { color: tokens.color.fg1 }` til StyleSheet.)

- [ ] **Step 6: tsc + jest**

Run: `./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/jest 2>&1 | tail -5`
Expected: tsc rent; alle suites grønne (SettingsScreen.test forbliver grøn)

- [ ] **Step 7: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/bubbleSetting.ts apps/mobile/src/lib/bubbleSetting.test.ts apps/mobile/src/screens/SettingsScreen.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): vedvarende boble-toggle i Settings"
```

---

## Task 10: Version-bump, build, install + manuel boble-verifikation

**Files:**
- Modify: `app.json`, `android/app/build.gradle`, `package.json`

Forudsætning: S24 tilkoblet (`adb devices` viser en enhed).

- [ ] **Step 1: Bump versioner (nuværende 0.1.28 / vc29 → 0.1.29 / vc30)**

- `android/app/build.gradle`: `versionCode 30`, `versionName "0.1.29"`.
- `app.json`: `"version": "0.1.29"`, `"versionCode": 30`.
- `package.json`: `"version": "0.1.29"`.

- [ ] **Step 2: Build release-APK**

Run (fra `apps/mobile/android`): `./gradlew assembleRelease`
Expected: `BUILD SUCCESSFUL`; APK i `app/build/outputs/apk/release/app-release.apk`. (Hvis Kotlin-fejl: ret mod fejlmeddelelsen — typisk manglende import; alle androidx.core-symboler kommer fra `androidx.core:core-ktx` som RN allerede afhænger af.)

- [ ] **Step 3: Install på S24**

Run (fra `apps/mobile/android`): `adb install -r app/build/outputs/apk/release/app-release.apk`
Expected: `Success`

- [ ] **Step 4: Manuel boble-verifikation på enhed**

Bekræft med Bjørn:
1. **Proaktiv:** Jarvis sender en besked → samtale-notifikation kan trækkes ud som flydende boble. Tap boble → kompakt chat på samme session.
2. **Manuel:** Åbn side-panel → tryk 🫧 → boblen popper straks (auto-expand).
3. **Sync:** Skriv i boblen → beskeden dukker op i hovedappen (server-autoritativ session).
4. **Vedvarende:** Settings → slå "Vedvarende Jarvis-boble" til → chat-head forbliver tilgængelig.
5. **Android < 11 / bobler slået fra:** 🫧-knap + toggle skjult / notifikation degraderer pænt (verificér mindst at appen ikke crasher).

- [ ] **Step 5: Commit version-bump**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/app.json apps/mobile/android/app/build.gradle apps/mobile/package.json
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "release(mobile): 0.1.29 (vc30) — chatboble (Bubbles API)"
```

---

## Final verification

- [ ] **jest:** fra `apps/mobile`: `./node_modules/.bin/jest 2>&1 | tail -5` → alle suites grønne (eksisterende ~104 + nye bubbleTrigger/bubbleModule/bubbleSetting).
- [ ] **tsc:** `./node_modules/.bin/tsc --noEmit` → ingen fejl.
- [ ] **Native build:** `assembleRelease` → BUILD SUCCESSFUL.
- [ ] **På enhed:** boble-verifikation (Task 10 Step 4) bekræftet af Bjørn.

---

## Notes / forbehold

- **New Architecture:** appen kører New Arch (TurboModules). Et klassisk `ReactContextBaseJavaModule` i et `ReactPackage` virker stadig via interop — derfor den simple module-form (ingen codegen-spec nødvendig).
- **Bubbles kræver Android 11 (API 30).** `isSupported()` gater al UI; på ældre enheder er funktionen usynlig og FCM-float springes over.
- **PendingIntent mutable:** `FLAG_MUTABLE` tilføjes kun på API 31+ (krav for bobler at kunne opdatere indholdet). På API 30 er mutable default.
- **ic_notification:** genbruger den eksisterende notifikations-ikon-ressource (samme som FCM-push bruger).
- **Auth i boblen:** deles via `expo-secure-store` (`loadAuthConfig`) — samme token som hovedappen; ingen ekstra login.
- **Bootstrap/OTA:** denne version (0.1.29/vc30) er højere end auto-updaterens manifest (vc29) → første ægte OTA-prompt udløses når den publiceres via C-updaterens `~/.jarvis-v2/mobile/`.
