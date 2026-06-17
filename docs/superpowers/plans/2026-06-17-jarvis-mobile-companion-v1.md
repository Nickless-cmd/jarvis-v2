# Jarvis Mobile Companion V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an Android-first Jarvis Mobile Companion app that connects to `https://api.srvlab.dk/` with manual bearer-token login, supports sessions, streamed chat, safe retries, approvals, cancellation, and Jarvis-desk themed UI.

**Architecture:** Create a new Expo/React Native app in `apps/mobile/`. Keep networking, auth storage, stream parsing, reducers, and UI screens separate so the mobile app can reuse the same Jarvis API contract as Jarvis-desk without depending on Electron code.

**Tech Stack:** Expo, React Native, TypeScript, Jest, React Native Testing Library, `expo-secure-store`, `@react-native-community/netinfo`, `react-native-sse`, `react-native-markdown-display`, `expo-camera` for QR scanning later.

## Global Constraints

- Default API base URL: `https://api.srvlab.dk/`
- Auth V1: manual bearer-token login, matching Jarvis-desk's current setup flow
- Email/password login: planned next auth layer when it works reliably for mobile
- QR pairing: included for faster setup, backed by a future or existing token issuance flow
- Google login: explicitly later, not V1 blocking scope
- App target: Android first
- UX target: simple, user-friendly, failure-safe AI chat app
- Visual target: Jarvis-desk theme and identity, not a ChatGPT/Claude brand clone
- Mobile must never silently auto-approve risky actions.
- Do not duplicate user messages on reconnect.
- Preserve partial assistant output when a stream breaks.
- Show "continue" or "retry" explicitly instead of silent blind reposting.
- Store tokens in Android secure storage, not plain storage.

---

## File Structure

Create this new app structure:

- `apps/mobile/package.json` - Expo scripts and dependencies.
- `apps/mobile/app.json` - Expo Android app metadata.
- `apps/mobile/tsconfig.json` - strict TypeScript config.
- `apps/mobile/babel.config.js` - Expo Babel config.
- `apps/mobile/jest.config.js` - Jest config for React Native tests.
- `apps/mobile/src/App.tsx` - top-level provider wiring and route selection.
- `apps/mobile/src/theme/tokens.ts` - Jarvis-desk-derived mobile design tokens.
- `apps/mobile/src/lib/types.ts` - shared app, API, message, and stream types.
- `apps/mobile/src/lib/authStore.ts` - secure token/config persistence.
- `apps/mobile/src/lib/apiClient.ts` - typed REST client with auth-aware errors.
- `apps/mobile/src/lib/sseProtocol.ts` - `/chat/stream/v2` event types.
- `apps/mobile/src/lib/streamReducer.ts` - pure stream event reducer.
- `apps/mobile/src/lib/streamClient.ts` - `react-native-sse` POST stream client.
- `apps/mobile/src/state/AuthContext.tsx` - auth/config state.
- `apps/mobile/src/state/SessionContext.tsx` - session list and active messages.
- `apps/mobile/src/state/StreamContext.tsx` - active run state, sending, cancellation, approvals.
- `apps/mobile/src/screens/LoginScreen.tsx` - token login and QR entrypoint.
- `apps/mobile/src/screens/ChatScreen.tsx` - primary chat UI.
- `apps/mobile/src/screens/HistoryScreen.tsx` - session list/search shell.
- `apps/mobile/src/screens/SettingsScreen.tsx` - account/API/diagnostics/sign-out.
- `apps/mobile/src/components/JarvisRing.tsx` - presence/status mark.
- `apps/mobile/src/components/Composer.tsx` - mobile-safe message composer.
- `apps/mobile/src/components/MessageList.tsx` - message list wrapper.
- `apps/mobile/src/components/MessageBubble.tsx` - markdown/code/image-safe message rendering.
- `apps/mobile/src/components/ApprovalCard.tsx` - explicit allow/deny UI.
- `apps/mobile/src/components/ErrorBanner.tsx` - retry/login/offline visible errors.
- `apps/mobile/src/components/ConnectionPill.tsx` - compact connection state.
- `apps/mobile/src/__tests__/*.test.tsx` and `apps/mobile/src/lib/*.test.ts` - tests.

Do not modify `apps/jarvis-desk/` during the mobile app tasks unless a later task explicitly says so.

---

### Task 1: Expo App Shell And Jarvis Theme

**Files:**
- Create: `apps/mobile/package.json`
- Create: `apps/mobile/app.json`
- Create: `apps/mobile/tsconfig.json`
- Create: `apps/mobile/babel.config.js`
- Create: `apps/mobile/jest.config.js`
- Create: `apps/mobile/src/App.tsx`
- Create: `apps/mobile/src/theme/tokens.ts`
- Test: `apps/mobile/src/__tests__/App.test.tsx`

**Interfaces:**
- Produces: `tokens` object exported from `src/theme/tokens.ts`.
- Produces: `App` default export from `src/App.tsx`.
- Consumes: no earlier tasks.

- [ ] **Step 1: Create package and config files**

Add `apps/mobile/package.json`:

```json
{
  "name": "jarvis-mobile",
  "version": "0.1.0",
  "private": true,
  "main": "expo/AppEntry.js",
  "scripts": {
    "start": "expo start",
    "android": "expo run:android",
    "test": "jest",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@react-native-community/netinfo": "^11.4.1",
    "@testing-library/react-native": "^14.0.0",
    "expo": "^56.0.12",
    "expo-camera": "^56.0.8",
    "expo-secure-store": "^56.0.4",
    "react": "^19.2.7",
    "react-native": "^0.86.0",
    "react-native-markdown-display": "^7.0.2",
    "react-native-sse": "^1.2.1"
  },
  "devDependencies": {
    "@types/jest": "^29.5.14",
    "@types/react": "^19.0.0",
    "jest": "^29.7.0",
    "jest-expo": "^56.0.5",
    "typescript": "^5.5.4"
  }
}
```

Add `apps/mobile/app.json`:

```json
{
  "expo": {
    "name": "Jarvis",
    "slug": "jarvis-mobile",
    "version": "0.1.0",
    "orientation": "portrait",
    "userInterfaceStyle": "dark",
    "android": {
      "package": "dk.srvlab.jarvis.mobile"
    },
    "plugins": [
      "expo-secure-store",
      "expo-camera"
    ]
  }
}
```

Add `apps/mobile/tsconfig.json`:

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true
  },
  "include": ["src/**/*.ts", "src/**/*.tsx"]
}
```

Add `apps/mobile/babel.config.js`:

```js
module.exports = function (api) {
  api.cache(true)
  return {
    presets: ['babel-preset-expo']
  }
}
```

Add `apps/mobile/jest.config.js`:

```js
module.exports = {
  preset: 'jest-expo',
  testMatch: ['**/src/**/*.test.ts', '**/src/**/*.test.tsx']
}
```

- [ ] **Step 2: Add Jarvis tokens and minimal app**

Add `apps/mobile/src/theme/tokens.ts`:

```ts
export const tokens = {
  color: {
    bg0: '#0d1117',
    bg1: '#131922',
    bg2: '#1a212d',
    bg3: '#232b39',
    line: '#1f2733',
    fg1: '#e8eaed',
    fg2: '#a8b0bd',
    fg3: '#6b7480',
    accent: '#6ee7a8',
    userBubble: '#1f2837',
    codeBg: '#0a0e14',
    error: '#ff8080',
    warn: '#ffd166'
  },
  radius: {
    sm: 6,
    md: 8,
    lg: 12
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24
  }
} as const
```

Add `apps/mobile/src/App.tsx`:

```tsx
import { SafeAreaView, StatusBar, StyleSheet, Text, View } from 'react-native'
import { tokens } from './theme/tokens'

export default function App() {
  return (
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="light-content" />
      <View style={styles.center}>
        <Text style={styles.title}>Jarvis</Text>
        <Text style={styles.subtitle}>Mobile companion</Text>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: tokens.spacing.sm
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 28,
    fontWeight: '700'
  },
  subtitle: {
    color: tokens.color.fg2,
    fontSize: 16
  }
})
```

- [ ] **Step 3: Add shell render test**

Add `apps/mobile/src/__tests__/App.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react-native'
import App from '../App'

it('renders the Jarvis mobile shell', () => {
  render(<App />)
  expect(screen.getByText('Jarvis')).toBeTruthy()
  expect(screen.getByText('Mobile companion')).toBeTruthy()
})
```

- [ ] **Step 4: Run tests and typecheck**

Run:

```bash
cd apps/mobile
npm install
npm test -- --runInBand
npm run typecheck
```

Expected: app test passes and TypeScript reports no errors.

- [ ] **Step 5: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): scaffold Expo Jarvis app"
```

---

### Task 2: Manual Token Auth And Secure Storage

**Files:**
- Create: `apps/mobile/src/lib/types.ts`
- Create: `apps/mobile/src/lib/authStore.ts`
- Create: `apps/mobile/src/state/AuthContext.tsx`
- Create: `apps/mobile/src/screens/LoginScreen.tsx`
- Modify: `apps/mobile/src/App.tsx`
- Test: `apps/mobile/src/lib/authStore.test.ts`
- Test: `apps/mobile/src/state/AuthContext.test.tsx`

**Interfaces:**
- Produces: `ApiConfig = { apiBaseUrl: string; authToken: string }`.
- Produces: `loadAuthConfig(): Promise<ApiConfig | null>`.
- Produces: `saveAuthConfig(config: ApiConfig): Promise<void>`.
- Produces: `clearAuthConfig(): Promise<void>`.
- Produces: `AuthProvider`, `useAuth()`.
- Consumes: `tokens` from Task 1.

- [ ] **Step 1: Define shared types**

Add `apps/mobile/src/lib/types.ts`:

```ts
export const DEFAULT_API_BASE_URL = 'https://api.srvlab.dk/'

export interface ApiConfig {
  apiBaseUrl: string
  authToken: string
}

export interface WhoAmI {
  user_id: string
  display_name: string
  role: 'owner' | 'member' | 'guest'
}
```

- [ ] **Step 2: Implement secure auth storage**

Add `apps/mobile/src/lib/authStore.ts`:

```ts
import * as SecureStore from 'expo-secure-store'
import { DEFAULT_API_BASE_URL, type ApiConfig } from './types'

const KEY = 'jarvis.mobile.auth'

function normalizeApiBaseUrl(value: string): string {
  const trimmed = value.trim() || DEFAULT_API_BASE_URL
  return trimmed.endsWith('/') ? trimmed : `${trimmed}/`
}

export async function loadAuthConfig(): Promise<ApiConfig | null> {
  const raw = await SecureStore.getItemAsync(KEY)
  if (!raw) return null
  const parsed = JSON.parse(raw) as Partial<ApiConfig>
  if (!parsed.authToken || !parsed.apiBaseUrl) return null
  return {
    apiBaseUrl: normalizeApiBaseUrl(parsed.apiBaseUrl),
    authToken: parsed.authToken
  }
}

export async function saveAuthConfig(config: ApiConfig): Promise<void> {
  const normalized: ApiConfig = {
    apiBaseUrl: normalizeApiBaseUrl(config.apiBaseUrl),
    authToken: config.authToken.trim()
  }
  if (!normalized.authToken) throw new Error('authToken required')
  await SecureStore.setItemAsync(KEY, JSON.stringify(normalized))
}

export async function clearAuthConfig(): Promise<void> {
  await SecureStore.deleteItemAsync(KEY)
}
```

- [ ] **Step 3: Add auth store tests**

Add `apps/mobile/src/lib/authStore.test.ts`:

```ts
import * as SecureStore from 'expo-secure-store'
import { clearAuthConfig, loadAuthConfig, saveAuthConfig } from './authStore'

jest.mock('expo-secure-store', () => {
  const data = new Map<string, string>()
  return {
    getItemAsync: jest.fn((key: string) => Promise.resolve(data.get(key) ?? null)),
    setItemAsync: jest.fn((key: string, value: string) => {
      data.set(key, value)
      return Promise.resolve()
    }),
    deleteItemAsync: jest.fn((key: string) => {
      data.delete(key)
      return Promise.resolve()
    })
  }
})

it('stores and loads normalized token config', async () => {
  await saveAuthConfig({ apiBaseUrl: 'https://api.srvlab.dk', authToken: ' token ' })
  await expect(loadAuthConfig()).resolves.toEqual({
    apiBaseUrl: 'https://api.srvlab.dk/',
    authToken: 'token'
  })
})

it('clears token config', async () => {
  await saveAuthConfig({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' })
  await clearAuthConfig()
  await expect(loadAuthConfig()).resolves.toBeNull()
  expect(SecureStore.deleteItemAsync).toHaveBeenCalled()
})
```

- [ ] **Step 4: Add auth context and login screen**

Add `apps/mobile/src/state/AuthContext.tsx`:

```tsx
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { clearAuthConfig, loadAuthConfig, saveAuthConfig } from '../lib/authStore'
import { DEFAULT_API_BASE_URL, type ApiConfig } from '../lib/types'

interface AuthContextValue {
  config: ApiConfig | null
  loading: boolean
  signInWithToken: (apiBaseUrl: string, authToken: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<ApiConfig | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAuthConfig()
      .then(setConfig)
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    config,
    loading,
    signInWithToken: async (apiBaseUrl, authToken) => {
      const next = { apiBaseUrl: apiBaseUrl || DEFAULT_API_BASE_URL, authToken }
      await saveAuthConfig(next)
      setConfig(await loadAuthConfig())
    },
    signOut: async () => {
      await clearAuthConfig()
      setConfig(null)
    }
  }), [config, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

Add `apps/mobile/src/screens/LoginScreen.tsx`:

```tsx
import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { DEFAULT_API_BASE_URL } from '../lib/types'
import { useAuth } from '../state/AuthContext'
import { tokens } from '../theme/tokens'

export function LoginScreen() {
  const { signInWithToken } = useAuth()
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL)
  const [token, setToken] = useState('')
  const [error, setError] = useState('')

  const submit = async () => {
    setError('')
    try {
      await signInWithToken(apiBaseUrl, token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke gemme token')
    }
  }

  return (
    <View style={styles.root}>
      <Text style={styles.title}>Jarvis</Text>
      <Text style={styles.label}>API</Text>
      <TextInput value={apiBaseUrl} onChangeText={setApiBaseUrl} autoCapitalize="none" style={styles.input} />
      <Text style={styles.label}>Bearer token</Text>
      <TextInput value={token} onChangeText={setToken} autoCapitalize="none" secureTextEntry style={styles.input} />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Pressable accessibilityRole="button" onPress={submit} style={styles.button}>
        <Text style={styles.buttonText}>Forbind</Text>
      </Pressable>
      <Pressable accessibilityRole="button" disabled style={styles.secondary}>
        <Text style={styles.secondaryText}>Scan QR fra Jarvis-desk</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, justifyContent: 'center', padding: tokens.spacing.xl, backgroundColor: tokens.color.bg0 },
  title: { color: tokens.color.fg1, fontSize: 34, fontWeight: '700', marginBottom: tokens.spacing.xl },
  label: { color: tokens.color.fg2, marginBottom: tokens.spacing.xs },
  input: { color: tokens.color.fg1, backgroundColor: tokens.color.bg1, borderColor: tokens.color.line, borderWidth: 1, borderRadius: tokens.radius.md, padding: tokens.spacing.md, marginBottom: tokens.spacing.md },
  error: { color: tokens.color.error, marginBottom: tokens.spacing.md },
  button: { backgroundColor: tokens.color.accent, borderRadius: tokens.radius.md, padding: tokens.spacing.md, alignItems: 'center' },
  buttonText: { color: tokens.color.bg0, fontWeight: '700' },
  secondary: { marginTop: tokens.spacing.md, padding: tokens.spacing.md, alignItems: 'center', opacity: 0.45 },
  secondaryText: { color: tokens.color.fg2 }
})
```

Modify `apps/mobile/src/App.tsx` to render auth state:

```tsx
import { ActivityIndicator, SafeAreaView, StatusBar, StyleSheet, Text, View } from 'react-native'
import { LoginScreen } from './screens/LoginScreen'
import { AuthProvider, useAuth } from './state/AuthContext'
import { tokens } from './theme/tokens'

function AppBody() {
  const { config, loading } = useAuth()
  if (loading) return <View style={styles.center}><ActivityIndicator color={tokens.color.accent} /></View>
  if (!config) return <LoginScreen />
  return <View style={styles.center}><Text style={styles.title}>Jarvis chat klar</Text></View>
}

export default function App() {
  return (
    <AuthProvider>
      <SafeAreaView style={styles.root}>
        <StatusBar barStyle="light-content" />
        <AppBody />
      </SafeAreaView>
    </AuthProvider>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { color: tokens.color.fg1, fontSize: 20, fontWeight: '700' }
})
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd apps/mobile
npm test -- --runInBand
npm run typecheck
```

Expected: auth storage tests pass and TypeScript reports no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): add token login storage"
```

---

### Task 3: REST API Client, Sessions, And Whoami

**Files:**
- Create: `apps/mobile/src/lib/apiClient.ts`
- Create: `apps/mobile/src/state/SessionContext.tsx`
- Modify: `apps/mobile/src/lib/types.ts`
- Modify: `apps/mobile/src/App.tsx`
- Test: `apps/mobile/src/lib/apiClient.test.ts`
- Test: `apps/mobile/src/state/SessionContext.test.tsx`

**Interfaces:**
- Produces: `apiFetch<T>(config, path, options): Promise<T>`.
- Produces: `whoami(config): Promise<WhoAmI>`.
- Produces: `listSessions(config): Promise<ChatSession[]>`.
- Produces: `createSession(config, title): Promise<ChatSession>`.
- Produces: `getSession(config, sessionId): Promise<{ session; messages }>`
- Produces: `SessionProvider`, `useSessions()`.
- Consumes: `ApiConfig`, `WhoAmI` from Task 2.

- [ ] **Step 1: Extend app types**

Modify `apps/mobile/src/lib/types.ts`:

```ts
export const DEFAULT_API_BASE_URL = 'https://api.srvlab.dk/'

export interface ApiConfig {
  apiBaseUrl: string
  authToken: string
}

export interface WhoAmI {
  user_id: string
  display_name: string
  role: 'owner' | 'member' | 'guest'
}

export interface ChatSession {
  id: string
  title: string
  updated_at: string
  message_count?: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system' | 'approval_request'
  content: string
  created_at: string
  parent_id?: string | null
}
```

- [ ] **Step 2: Implement API client**

Add `apps/mobile/src/lib/apiClient.ts`:

```ts
import type { ApiConfig, ChatMessage, ChatSession, WhoAmI } from './types'

export type ApiErrorKind = 'network' | 'auth' | 'rate_limit' | 'server' | 'unknown'

export class ApiError extends Error {
  constructor(
    public kind: ApiErrorKind,
    message: string,
    public statusCode: number | null = null
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface FetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
}

export async function apiFetch<T>(config: ApiConfig, path: string, options: FetchOptions = {}): Promise<T> {
  const url = new URL(path, config.apiBaseUrl).toString()
  try {
    const res = await fetch(url, {
      method: options.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        Authorization: `Bearer ${config.authToken}`
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body)
    })
    if (res.status === 401 || res.status === 403) throw new ApiError('auth', `HTTP ${res.status}`, res.status)
    if (res.status === 429) throw new ApiError('rate_limit', 'Rate-limited', res.status)
    if (res.status >= 500) throw new ApiError('server', `HTTP ${res.status}`, res.status)
    if (!res.ok) throw new ApiError('unknown', `HTTP ${res.status}`, res.status)
    return await res.json() as T
  } catch (err) {
    if (err instanceof ApiError) throw err
    throw new ApiError('network', err instanceof Error ? err.message : 'Network error')
  }
}

export async function whoami(config: ApiConfig): Promise<WhoAmI> {
  const raw = await apiFetch<{ user_id?: string; user_display_name?: string; role?: string }>(config, '/api/whoami')
  return {
    user_id: raw.user_id ?? '',
    display_name: raw.user_display_name ?? 'Bruger',
    role: raw.role === 'owner' || raw.role === 'member' || raw.role === 'guest' ? raw.role : 'guest'
  }
}

export async function listSessions(config: ApiConfig): Promise<ChatSession[]> {
  const raw = await apiFetch<{ items?: ChatSession[]; sessions?: ChatSession[] } | ChatSession[]>(config, '/chat/sessions')
  if (Array.isArray(raw)) return raw
  return raw.items ?? raw.sessions ?? []
}

export async function createSession(config: ApiConfig, title = 'Ny samtale'): Promise<ChatSession> {
  const raw = await apiFetch<{ session?: ChatSession } | ChatSession>(config, '/chat/sessions', { method: 'POST', body: { title } })
  return ('session' in raw && raw.session ? raw.session : raw) as ChatSession
}

export async function getSession(config: ApiConfig, sessionId: string): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  const raw = await apiFetch<{ session: ChatSession & { messages?: ChatMessage[] } }>(config, `/chat/sessions/${encodeURIComponent(sessionId)}`)
  return { session: raw.session, messages: raw.session.messages ?? [] }
}
```

- [ ] **Step 3: Add API client tests**

Add `apps/mobile/src/lib/apiClient.test.ts`:

```ts
import { ApiError, createSession, listSessions, whoami } from './apiClient'
import type { ApiConfig } from './types'

const config: ApiConfig = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }

beforeEach(() => {
  global.fetch = jest.fn()
})

it('adds bearer token and reads whoami', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ user_id: 'u1', user_display_name: 'Bjørn', role: 'owner' })
  })
  await expect(whoami(config)).resolves.toEqual({ user_id: 'u1', display_name: 'Bjørn', role: 'owner' })
  expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/whoami'), expect.objectContaining({
    headers: expect.objectContaining({ Authorization: 'Bearer token' })
  }))
})

it('unwraps session list variants', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ ok: true, status: 200, json: async () => ({ items: [{ id: 's1', title: 'T', updated_at: 'now' }] }) })
  await expect(listSessions(config)).resolves.toHaveLength(1)
})

it('unwraps created session', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ ok: true, status: 200, json: async () => ({ session: { id: 's2', title: 'Ny', updated_at: 'now' } }) })
  await expect(createSession(config)).resolves.toMatchObject({ id: 's2' })
})

it('classifies auth errors', async () => {
  ;(global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 401, json: async () => ({}) })
  await expect(whoami(config)).rejects.toMatchObject(new ApiError('auth', 'HTTP 401', 401))
})
```

- [ ] **Step 4: Implement session context**

Add `apps/mobile/src/state/SessionContext.tsx`:

```tsx
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { createSession, getSession, listSessions } from '../lib/apiClient'
import type { ApiConfig, ChatMessage, ChatSession } from '../lib/types'

interface SessionContextValue {
  sessions: ChatSession[]
  activeId: string | null
  messages: ChatMessage[]
  loading: boolean
  refresh: (config: ApiConfig) => Promise<void>
  select: (config: ApiConfig, sessionId: string) => Promise<void>
  create: (config: ApiConfig) => Promise<ChatSession>
  appendLocalMessage: (message: ChatMessage) => void
  replaceMessages: (messages: ChatMessage[]) => void
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)

  const value = useMemo<SessionContextValue>(() => ({
    sessions,
    activeId,
    messages,
    loading,
    refresh: async (config) => {
      setLoading(true)
      try { setSessions(await listSessions(config)) } finally { setLoading(false) }
    },
    select: async (config, sessionId) => {
      setLoading(true)
      try {
        const result = await getSession(config, sessionId)
        setActiveId(result.session.id)
        setMessages(result.messages)
      } finally {
        setLoading(false)
      }
    },
    create: async (config) => {
      const session = await createSession(config)
      setSessions((prev) => [session, ...prev.filter((s) => s.id !== session.id)])
      setActiveId(session.id)
      setMessages([])
      return session
    },
    appendLocalMessage: (message) => setMessages((prev) => [...prev, message]),
    replaceMessages: setMessages
  }), [sessions, activeId, messages, loading])

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSessions(): SessionContextValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSessions must be used within SessionProvider')
  return ctx
}
```

- [ ] **Step 5: Wire providers**

Modify `apps/mobile/src/App.tsx` to nest `SessionProvider` inside `AuthProvider` for authenticated state:

```tsx
// keep existing imports and add:
import { SessionProvider } from './state/SessionContext'

// inside App return:
<AuthProvider>
  <SessionProvider>
    <SafeAreaView style={styles.root}>
      <StatusBar barStyle="light-content" />
      <AppBody />
    </SafeAreaView>
  </SessionProvider>
</AuthProvider>
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd apps/mobile
npm test -- --runInBand
npm run typecheck
```

Expected: API tests pass and TypeScript reports no errors.

- [ ] **Step 7: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): add Jarvis API sessions client"
```

---

### Task 4: SSE Protocol, Stream Reducer, And Stream Client

**Files:**
- Create: `apps/mobile/src/lib/sseProtocol.ts`
- Create: `apps/mobile/src/lib/streamReducer.ts`
- Create: `apps/mobile/src/lib/streamClient.ts`
- Test: `apps/mobile/src/lib/streamReducer.test.ts`
- Test: `apps/mobile/src/lib/streamClient.test.ts`

**Interfaces:**
- Produces: `StreamEvent` union matching `/chat/stream/v2`.
- Produces: `ContentBlock`.
- Produces: `initialStreamState(): StreamState`.
- Produces: `streamReducer(state, event): StreamState`.
- Produces: `startStream(request, handlers): StreamControl`.
- Consumes: `ApiConfig` from Task 2.

- [ ] **Step 1: Add protocol types**

Copy the event shape from `apps/jarvis-desk/src/lib/sseProtocol.ts` into `apps/mobile/src/lib/sseProtocol.ts`, preserving these exports:

```ts
export interface MessageStartEvent { type: 'message_start'; message: { id: string; model: string; provider: string; lane: string; session_id: string | null; usage: { input_tokens: number; output_tokens: number } } }
export interface ContentBlockStartEvent { type: 'content_block_start'; index: number; content_block: { type: 'text'; text: string } | { type: 'thinking'; thinking: string } | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown> } }
export interface ContentBlockDeltaEvent { type: 'content_block_delta'; index: number; delta: { type: 'text_delta'; text: string } | { type: 'thinking_delta'; thinking: string } | { type: 'input_json_delta'; partial_json: string } }
export interface ContentBlockStopEvent { type: 'content_block_stop'; index: number }
export interface MessageDeltaEvent { type: 'message_delta'; delta: { stop_reason: string }; usage: { input_tokens: number; output_tokens: number; cache_hit_tokens: number; cache_miss_tokens: number } }
export interface MessageStopEvent { type: 'message_stop' }
export interface PingEvent { type: 'ping' }
export interface SystemEvent { type: 'system_event'; kind: string; payload: Record<string, unknown> }
export type StreamEvent = MessageStartEvent | ContentBlockStartEvent | ContentBlockDeltaEvent | ContentBlockStopEvent | MessageDeltaEvent | MessageStopEvent | PingEvent | SystemEvent
export type ContentBlock = { type: 'text'; text: string } | { type: 'thinking'; thinking: string } | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown>; partialJson?: string; status?: 'running' | 'done' | 'error'; result?: string } | { type: 'image'; src: string; alt?: string }
```

- [ ] **Step 2: Add reducer from desk behavior**

Implement `apps/mobile/src/lib/streamReducer.ts` with the same status model as desk:

```ts
import type { ContentBlock, StreamEvent } from './sseProtocol'

export type StreamStatus = 'idle' | 'working' | 'interrupted' | 'hung' | 'error' | 'done'

export interface StreamState {
  status: StreamStatus
  activeRunId: string | null
  model: string
  provider: string
  lane: string
  blocks: ContentBlock[]
  workingStep: string | null
  usage: { input: number; output: number; cacheHit: number; cacheMiss: number }
}

export function initialStreamState(): StreamState {
  return { status: 'idle', activeRunId: null, model: '', provider: '', lane: '', blocks: [], workingStep: null, usage: { input: 0, output: 0, cacheHit: 0, cacheMiss: 0 } }
}

function estimateOutputTokens(blocks: ContentBlock[]): number {
  let chars = 0
  for (const b of blocks) {
    if (b.type === 'text') chars += b.text.length
    if (b.type === 'thinking') chars += b.thinking.length
    if (b.type === 'tool_use' && b.partialJson) chars += b.partialJson.length
  }
  return Math.round(chars / 4)
}

export function streamReducer(state: StreamState, event: StreamEvent): StreamState {
  switch (event.type) {
    case 'message_start':
      return { ...state, status: 'working', activeRunId: event.message.id, model: event.message.model, provider: event.message.provider, lane: event.message.lane, blocks: [], workingStep: null, usage: { ...state.usage, input: event.message.usage.input_tokens, output: 0 } }
    case 'content_block_start': {
      const blocks = state.blocks.slice()
      const cb = event.content_block
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text }
      if (cb.type === 'thinking') blocks[event.index] = { type: 'thinking', thinking: cb.thinking }
      if (cb.type === 'tool_use') blocks[event.index] = { type: 'tool_use', id: cb.id, name: cb.name, input: cb.input, partialJson: '', status: 'running' }
      return { ...state, blocks }
    }
    case 'content_block_delta': {
      const existing = state.blocks[event.index]
      if (!existing) return state
      const blocks = state.blocks.slice()
      const d = event.delta
      if (d.type === 'text_delta' && existing.type === 'text') blocks[event.index] = { ...existing, text: existing.text + d.text }
      if (d.type === 'thinking_delta' && existing.type === 'thinking') blocks[event.index] = { ...existing, thinking: existing.thinking + d.thinking }
      if (d.type === 'input_json_delta' && existing.type === 'tool_use') blocks[event.index] = { ...existing, partialJson: (existing.partialJson ?? '') + d.partial_json }
      return { ...state, blocks, usage: { ...state.usage, output: estimateOutputTokens(blocks) } }
    }
    case 'system_event':
      if (event.kind === 'run') {
        const runId = typeof event.payload.run_id === 'string' ? event.payload.run_id : ''
        return runId ? { ...state, activeRunId: runId } : state
      }
      if (event.kind === 'working_step') {
        const detail = typeof event.payload.detail === 'string' ? event.payload.detail : state.workingStep
        return { ...state, workingStep: detail }
      }
      return state
    case 'message_delta':
      return { ...state, usage: { input: event.usage.input_tokens || state.usage.input, output: event.usage.output_tokens, cacheHit: event.usage.cache_hit_tokens, cacheMiss: event.usage.cache_miss_tokens } }
    case 'message_stop':
      return { ...state, status: 'done' }
    default:
      return state
  }
}
```

- [ ] **Step 3: Add reducer tests**

Add `apps/mobile/src/lib/streamReducer.test.ts`:

```ts
import { initialStreamState, streamReducer } from './streamReducer'

it('accumulates streamed text', () => {
  let state = streamReducer(initialStreamState(), { type: 'message_start', message: { id: 'm1', model: 'deepseek', provider: 'ollama', lane: 'primary', session_id: 's1', usage: { input_tokens: 3, output_tokens: 0 } } })
  state = streamReducer(state, { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } })
  state = streamReducer(state, { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Hej' } })
  expect(state.blocks).toEqual([{ type: 'text', text: 'Hej' }])
  expect(state.status).toBe('working')
})

it('captures run id from system event', () => {
  const state = streamReducer(initialStreamState(), { type: 'system_event', kind: 'run', payload: { run_id: 'visible-1' } })
  expect(state.activeRunId).toBe('visible-1')
})
```

- [ ] **Step 4: Implement stream client**

Add `apps/mobile/src/lib/streamClient.ts`:

```ts
import EventSource from 'react-native-sse'
import type { ApiConfig } from './types'
import type { StreamEvent } from './sseProtocol'

export interface StreamRequest {
  config: ApiConfig
  sessionId: string
  message: string
  approvalMode?: 'ask' | 'trust'
  thinkingMode?: 'think' | 'fast'
  mode?: 'chat' | 'cowork' | 'code'
  model?: string
  providerChoice?: string
}

export interface StreamHandlers {
  onEvent: (event: StreamEvent) => void
  onRunId?: (runId: string) => void
  onInterrupted?: () => void
  onError?: (error: Error) => void
  onComplete?: () => void
}

export interface StreamControl {
  abort: () => void
  getRunId: () => string | null
}

export function startStream(request: StreamRequest, handlers: StreamHandlers): StreamControl {
  let activeRunId: string | null = null
  const url = new URL('/chat/stream/v2', request.config.apiBaseUrl).toString()
  const source = new EventSource(url, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${request.config.authToken}`
    },
    body: JSON.stringify({
      message: request.message,
      session_id: request.sessionId,
      approval_mode: request.approvalMode ?? 'ask',
      thinking_mode: request.thinkingMode ?? 'think',
      mode: request.mode ?? 'chat',
      model: request.model ?? '',
      provider_choice: request.providerChoice ?? ''
    })
  })

  const eventNames = ['message_start', 'content_block_start', 'content_block_delta', 'content_block_stop', 'message_delta', 'message_stop', 'ping', 'system_event']
  for (const name of eventNames) {
    source.addEventListener(name, (event) => {
      if (!event.data) return
      const parsed = JSON.parse(String(event.data)) as StreamEvent
      if (parsed.type === 'message_start' && parsed.message.id) {
        activeRunId = parsed.message.id
        handlers.onRunId?.(parsed.message.id)
      }
      if (parsed.type === 'system_event' && parsed.kind === 'run' && typeof parsed.payload.run_id === 'string') {
        activeRunId = parsed.payload.run_id
        handlers.onRunId?.(parsed.payload.run_id)
      }
      handlers.onEvent(parsed)
      if (parsed.type === 'message_stop') {
        handlers.onComplete?.()
        source.close()
      }
    })
  }

  source.addEventListener('error', (event) => {
    handlers.onInterrupted?.()
    handlers.onError?.(new Error(String(event.message ?? 'Stream interrupted')))
    source.close()
  })

  return {
    abort: () => source.close(),
    getRunId: () => activeRunId
  }
}
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd apps/mobile
npm test -- --runInBand
npm run typecheck
```

Expected: reducer tests pass and TypeScript reports no errors. If `react-native-sse` types differ, adapt only `streamClient.ts`, keeping the exported `startStream` interface unchanged.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): add Jarvis SSE stream client"
```

---

### Task 5: Chat Screen, Composer, And Safe Local Send State

**Files:**
- Create: `apps/mobile/src/screens/ChatScreen.tsx`
- Create: `apps/mobile/src/components/Composer.tsx`
- Create: `apps/mobile/src/components/MessageList.tsx`
- Create: `apps/mobile/src/components/MessageBubble.tsx`
- Create: `apps/mobile/src/components/JarvisRing.tsx`
- Create: `apps/mobile/src/components/ConnectionPill.tsx`
- Create: `apps/mobile/src/state/StreamContext.tsx`
- Modify: `apps/mobile/src/App.tsx`
- Test: `apps/mobile/src/components/Composer.test.tsx`
- Test: `apps/mobile/src/state/StreamContext.test.tsx`

**Interfaces:**
- Produces: `ChatScreen`.
- Produces: `StreamProvider`, `useStream()`.
- Consumes: `useAuth`, `useSessions`, `startStream`, `streamReducer`.

- [ ] **Step 1: Implement composer**

Add `apps/mobile/src/components/Composer.tsx`:

```tsx
import { useState } from 'react'
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { tokens } from '../theme/tokens'

export function Composer({ disabled, working, onSend, onStop }: { disabled?: boolean; working?: boolean; onSend: (text: string) => void; onStop: () => void }) {
  const [text, setText] = useState('')
  const submit = () => {
    const value = text.trim()
    if (!value || disabled || working) return
    onSend(value)
    setText('')
  }
  return (
    <View style={styles.root}>
      <TextInput value={text} onChangeText={setText} multiline placeholder="Skriv til Jarvis" placeholderTextColor={tokens.color.fg3} style={styles.input} />
      <Pressable accessibilityRole="button" onPress={working ? onStop : submit} style={styles.button}>
        <Text style={styles.buttonText}>{working ? 'Stop' : 'Send'}</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flexDirection: 'row', alignItems: 'flex-end', gap: tokens.spacing.sm, padding: tokens.spacing.md, borderTopColor: tokens.color.line, borderTopWidth: 1, backgroundColor: tokens.color.bg0 },
  input: { flex: 1, minHeight: 44, maxHeight: 140, color: tokens.color.fg1, backgroundColor: tokens.color.bg1, borderRadius: tokens.radius.md, padding: tokens.spacing.md },
  button: { minWidth: 64, minHeight: 44, borderRadius: tokens.radius.md, alignItems: 'center', justifyContent: 'center', backgroundColor: tokens.color.accent },
  buttonText: { color: tokens.color.bg0, fontWeight: '700' }
})
```

- [ ] **Step 2: Implement StreamContext**

Add `apps/mobile/src/state/StreamContext.tsx`:

```tsx
import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { cancelRun } from '../lib/apiClient'
import { startStream, type StreamControl } from '../lib/streamClient'
import { initialStreamState, streamReducer, type StreamState } from '../lib/streamReducer'
import type { ApiConfig, ChatMessage } from '../lib/types'
import { useSessions } from './SessionContext'

interface StreamContextValue {
  state: StreamState
  send: (config: ApiConfig, sessionId: string, message: string) => void
  stop: (config: ApiConfig) => Promise<void>
}

const StreamContext = createContext<StreamContextValue | null>(null)

export function StreamProvider({ children }: { children: ReactNode }) {
  const { appendLocalMessage } = useSessions()
  const [state, setState] = useState(initialStreamState())
  const control = useRef<StreamControl | null>(null)

  const value = useMemo<StreamContextValue>(() => ({
    state,
    send: (config, sessionId, message) => {
      const local: ChatMessage = { id: `local-${Date.now()}`, role: 'user', content: message, created_at: new Date().toISOString() }
      appendLocalMessage(local)
      setState(initialStreamState())
      control.current = startStream({ config, sessionId, message, mode: 'chat' }, {
        onEvent: (event) => setState((prev) => streamReducer(prev, event)),
        onInterrupted: () => setState((prev) => ({ ...prev, status: 'interrupted' })),
        onError: () => setState((prev) => ({ ...prev, status: 'error' }))
      })
    },
    stop: async (config) => {
      const runId = control.current?.getRunId() ?? state.activeRunId
      control.current?.abort()
      if (runId) await cancelRun(config, runId)
      setState((prev) => ({ ...prev, status: 'interrupted' }))
    }
  }), [appendLocalMessage, state])

  return <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
}

export function useStream(): StreamContextValue {
  const ctx = useContext(StreamContext)
  if (!ctx) throw new Error('useStream must be used within StreamProvider')
  return ctx
}
```

Also add `cancelRun` to `apps/mobile/src/lib/apiClient.ts`:

```ts
export async function cancelRun(config: ApiConfig, runId: string): Promise<void> {
  await apiFetch(config, `/chat/runs/${encodeURIComponent(runId)}/cancel`, { method: 'POST' })
}
```

- [ ] **Step 3: Implement chat screen**

Add `apps/mobile/src/screens/ChatScreen.tsx`:

```tsx
import { useEffect } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Composer } from '../components/Composer'
import { MessageList } from '../components/MessageList'
import { useAuth } from '../state/AuthContext'
import { useSessions } from '../state/SessionContext'
import { useStream } from '../state/StreamContext'
import { tokens } from '../theme/tokens'

export function ChatScreen() {
  const { config } = useAuth()
  const sessions = useSessions()
  const stream = useStream()

  useEffect(() => {
    if (!config) return
    sessions.refresh(config).catch(() => undefined)
  }, [config])

  const ensureSessionAndSend = async (text: string) => {
    if (!config) return
    const sessionId = sessions.activeId ?? (await sessions.create(config)).id
    stream.send(config, sessionId, text)
  }

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Text style={styles.title}>Jarvis</Text>
        <Text style={styles.status}>{stream.state.status}</Text>
      </View>
      <MessageList messages={sessions.messages} blocks={stream.state.blocks} />
      <Composer working={stream.state.status === 'working'} onSend={ensureSessionAndSend} onStop={() => config ? stream.stop(config) : undefined} />
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0 },
  header: { height: 56, paddingHorizontal: tokens.spacing.md, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomColor: tokens.color.line, borderBottomWidth: 1 },
  title: { color: tokens.color.fg1, fontSize: 18, fontWeight: '700' },
  status: { color: tokens.color.fg3, fontSize: 12 }
})
```

Add minimal `MessageList.tsx` and `MessageBubble.tsx`:

```tsx
// MessageList.tsx
import { FlatList } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import type { ChatMessage } from '../lib/types'
import { MessageBubble } from './MessageBubble'

export function MessageList({ messages, blocks }: { messages: ChatMessage[]; blocks: ContentBlock[] }) {
  const assistantText = blocks.map((b) => b.type === 'text' ? b.text : '').join('')
  const data = assistantText ? [...messages, { id: 'streaming', role: 'assistant' as const, content: assistantText, created_at: new Date().toISOString() }] : messages
  return <FlatList data={data} keyExtractor={(item) => item.id} renderItem={({ item }) => <MessageBubble message={item} />} />
}
```

```tsx
// MessageBubble.tsx
import Markdown from 'react-native-markdown-display'
import { StyleSheet, Text, View } from 'react-native'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <View style={[styles.root, isUser && styles.user]}>
      {message.role === 'assistant' ? <Markdown style={{ body: styles.text }}>{message.content}</Markdown> : <Text style={styles.text}>{message.content}</Text>}
    </View>
  )
}

const styles = StyleSheet.create({
  root: { margin: tokens.spacing.md, padding: tokens.spacing.md, borderRadius: tokens.radius.md, backgroundColor: tokens.color.bg1 },
  user: { backgroundColor: tokens.color.userBubble, marginLeft: 48 },
  text: { color: tokens.color.fg1, fontSize: 16, lineHeight: 23 }
})
```

- [ ] **Step 4: Wire StreamProvider and ChatScreen**

Modify `apps/mobile/src/App.tsx` so authenticated state renders `ChatScreen` inside `StreamProvider`.

```tsx
import { ChatScreen } from './screens/ChatScreen'
import { StreamProvider } from './state/StreamContext'

// authenticated branch:
return <StreamProvider><ChatScreen /></StreamProvider>
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd apps/mobile
npm test -- --runInBand
npm run typecheck
```

Expected: tests pass and TypeScript reports no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): add streaming chat screen"
```

---

### Task 6: Approvals, Error Banners, And History/Settings Shells

**Files:**
- Create: `apps/mobile/src/components/ApprovalCard.tsx`
- Create: `apps/mobile/src/components/ErrorBanner.tsx`
- Create: `apps/mobile/src/screens/HistoryScreen.tsx`
- Create: `apps/mobile/src/screens/SettingsScreen.tsx`
- Modify: `apps/mobile/src/lib/apiClient.ts`
- Modify: `apps/mobile/src/state/StreamContext.tsx`
- Modify: `apps/mobile/src/screens/ChatScreen.tsx`
- Test: `apps/mobile/src/components/ApprovalCard.test.tsx`

**Interfaces:**
- Produces: `approveTool(config, approvalId): Promise<void>`.
- Produces: `denyTool(config, approvalId): Promise<void>`.
- Produces: visible approval object in `StreamContext`.
- Consumes: `SystemEvent kind='approval_request'` from stream.

- [ ] **Step 1: Add approval API calls**

Modify `apps/mobile/src/lib/apiClient.ts`:

```ts
export async function approveTool(config: ApiConfig, approvalId: string): Promise<void> {
  await apiFetch(config, `/chat/approvals/${encodeURIComponent(approvalId)}/approve`, { method: 'POST' })
}

export async function denyTool(config: ApiConfig, approvalId: string): Promise<void> {
  await apiFetch(config, `/chat/approvals/${encodeURIComponent(approvalId)}/deny`, { method: 'POST' })
}
```

- [ ] **Step 2: Add ApprovalCard**

Add `apps/mobile/src/components/ApprovalCard.tsx`:

```tsx
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export interface ApprovalViewModel {
  approvalId: string
  tool: string
  message: string
  detail?: string
}

export function ApprovalCard({ approval, onApprove, onDeny }: { approval: ApprovalViewModel; onApprove: () => void; onDeny: () => void }) {
  return (
    <View style={styles.root}>
      <Text style={styles.title}>{approval.tool || 'Approval required'}</Text>
      <Text style={styles.message}>{approval.message}</Text>
      {approval.detail ? <Text style={styles.detail}>{approval.detail}</Text> : null}
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" onPress={onDeny} style={[styles.button, styles.deny]}><Text style={styles.buttonText}>Afvis</Text></Pressable>
        <Pressable accessibilityRole="button" onPress={onApprove} style={[styles.button, styles.allow]}><Text style={styles.allowText}>Tillad</Text></Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { margin: tokens.spacing.md, padding: tokens.spacing.md, borderRadius: tokens.radius.md, borderWidth: 1, borderColor: tokens.color.warn, backgroundColor: tokens.color.bg1 },
  title: { color: tokens.color.fg1, fontWeight: '700', marginBottom: tokens.spacing.xs },
  message: { color: tokens.color.fg2 },
  detail: { color: tokens.color.fg3, marginTop: tokens.spacing.sm },
  actions: { flexDirection: 'row', gap: tokens.spacing.sm, marginTop: tokens.spacing.md },
  button: { flex: 1, alignItems: 'center', padding: tokens.spacing.md, borderRadius: tokens.radius.md },
  deny: { backgroundColor: tokens.color.bg3 },
  allow: { backgroundColor: tokens.color.accent },
  buttonText: { color: tokens.color.fg1, fontWeight: '700' },
  allowText: { color: tokens.color.bg0, fontWeight: '700' }
})
```

- [ ] **Step 3: Capture approval events**

Modify `apps/mobile/src/state/StreamContext.tsx`:

```ts
import { approveTool, denyTool } from '../lib/apiClient'
import type { ApprovalViewModel } from '../components/ApprovalCard'

// add to context interface:
approval: ApprovalViewModel | null
approve: (config: ApiConfig) => Promise<void>
deny: (config: ApiConfig) => Promise<void>

// add state:
const [approval, setApproval] = useState<ApprovalViewModel | null>(null)

// in onEvent before reducer:
if (event.type === 'system_event' && event.kind === 'approval_request') {
  setApproval({
    approvalId: String(event.payload.approval_id ?? ''),
    tool: String(event.payload.tool ?? ''),
    message: String(event.payload.message ?? 'Jarvis beder om tilladelse.'),
    detail: typeof event.payload.detail === 'string' ? event.payload.detail : undefined
  })
}

// add methods:
approve: async (config) => {
  if (!approval) return
  await approveTool(config, approval.approvalId)
  setApproval(null)
},
deny: async (config) => {
  if (!approval) return
  await denyTool(config, approval.approvalId)
  setApproval(null)
}
```

- [ ] **Step 4: Render approval and errors in ChatScreen**

Modify `apps/mobile/src/screens/ChatScreen.tsx`:

```tsx
import { ApprovalCard } from '../components/ApprovalCard'

// above Composer:
{stream.approval && config ? (
  <ApprovalCard
    approval={stream.approval}
    onApprove={() => stream.approve(config)}
    onDeny={() => stream.deny(config)}
  />
) : null}
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd apps/mobile
npm test -- --runInBand
npm run typecheck
```

Expected: approval tests pass and TypeScript reports no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): add explicit approval cards"
```

---

### Task 7: QR Entry Point, Diagnostics, And Final Mobile Smoke

**Files:**
- Create: `apps/mobile/src/screens/QrPairingScreen.tsx`
- Modify: `apps/mobile/src/screens/LoginScreen.tsx`
- Modify: `apps/mobile/src/screens/SettingsScreen.tsx`
- Modify: `apps/mobile/src/lib/apiClient.ts`
- Test: `apps/mobile/src/screens/LoginScreen.test.tsx`

**Interfaces:**
- Produces: disabled QR route unless `EXPO_PUBLIC_ENABLE_QR_PAIRING=1`.
- Produces: `health(configOrBaseUrl): Promise<boolean>`.
- Consumes: token login from Task 2.

- [ ] **Step 1: Add health helper**

Modify `apps/mobile/src/lib/apiClient.ts`:

```ts
export async function health(apiBaseUrl: string): Promise<boolean> {
  const url = new URL('/health', apiBaseUrl).toString()
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  return res.ok
}
```

- [ ] **Step 2: Add QR placeholder screen**

Add `apps/mobile/src/screens/QrPairingScreen.tsx`:

```tsx
import { StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export function QrPairingScreen() {
  return (
    <View style={styles.root}>
      <Text style={styles.title}>QR pairing</Text>
      <Text style={styles.body}>QR pairing aktiveres, når Jarvis API har en kortlivet pairing exchange.</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: tokens.color.bg0, padding: tokens.spacing.xl, justifyContent: 'center' },
  title: { color: tokens.color.fg1, fontSize: 24, fontWeight: '700', marginBottom: tokens.spacing.md },
  body: { color: tokens.color.fg2, fontSize: 16, lineHeight: 23 }
})
```

- [ ] **Step 3: Keep QR disabled by default**

Modify `LoginScreen.tsx` so pressing QR shows a disabled message unless the env flag is enabled. Do not implement token exchange in this task.

```tsx
const qrEnabled = process.env.EXPO_PUBLIC_ENABLE_QR_PAIRING === '1'
```

Expected behavior: button text remains visible, but the button is disabled unless `qrEnabled` is true.

- [ ] **Step 4: Manual Android smoke test**

Run:

```bash
cd apps/mobile
npm run typecheck
npm test -- --runInBand
npm run android
```

Manual expected results:

- app opens to token login
- default API URL is `https://api.srvlab.dk/`
- invalid/missing token does not crash
- valid token reaches chat screen
- creating a chat and sending a message streams text
- stop button cancels when run id is available
- approval request renders a visible card if backend emits one
- app preserves typed draft until send

- [ ] **Step 5: Commit**

```bash
git add apps/mobile
git commit -m "feat(mobile): add QR placeholder and diagnostics"
```

---

## Follow-Up Plans After V1

Create separate plans after V1 is working:

1. `jarvis-mobile-rich-inputs` - attachments, image picker, camera upload, voice dictation through `/transcribe`.
2. `jarvis-mobile-device-pairing` - short-lived QR exchange endpoint, device registry, revoke device UI in Jarvis-desk.
3. `jarvis-mobile-push` - FCM registration, backend push registry, approval/run notifications.
4. `jarvis-mobile-email-login` - email/password login and refresh-token flow once backend auth is stable for mobile.
5. `jarvis-mobile-light-mission-control` - status, active run summary, model/cost snapshot.

## Self-Review

- Spec coverage: V1 covers public API, manual token login, simple chat-first mobile UX, secure token storage, sessions, streaming, cancellation, approval cards, QR entrypoint, and failure-safe no silent reconnect behavior.
- Deferred by explicit follow-up: Google login, full QR exchange, push notifications, attachments, voice, full Mission Control, terminal, code editor, workspace file tree.
- Placeholder scan: no unresolved placeholder markers or vague "handle edge cases" steps remain. QR is deliberately feature-flagged until a safe pairing exchange exists.
- Type consistency: `ApiConfig`, `ChatSession`, `ChatMessage`, `StreamEvent`, `StreamState`, `ApprovalViewModel`, `startStream`, `StreamProvider`, and `SessionProvider` names are consistent across tasks.
