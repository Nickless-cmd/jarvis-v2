export const DEFAULT_API_BASE_URL = 'https://api.srvlab.dk/'

export interface ApiConfig {
  apiBaseUrl: string
  authToken: string
}

export interface WhoAmI {
  user_id: string
  display_name: string
  /**
   * `partner` er «member, plus husstand» — IKKE et trin mellem member og owner.
   * Den giver adgang til det der er privat for dem der bor i hjemmet
   * (Sansernes Arkiv) og intet andet. Se core/identity/household.py.
   */
  role: 'owner' | 'partner' | 'member' | 'guest'
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
  /**
   * Serverens strukturerede blokke for turen, i ÆGTE rækkefølge:
   * text → tool_use → tool_result → text → …
   *
   * `content` er den samme tur klasket sammen til én streng. Renderer man
   * den, får man værktøjerne først og alle synteser smeltet til én blok —
   * netop dét vi rettede på serveren. Har beskeden blokke, er de sandheden.
   */
  content_json?: unknown[] | string | null
}

export interface AccountProfile {
  user_id: string
  email: string
  email_verified: boolean
  language: string
  role: 'owner' | 'member' | 'guest'
  tier: string
  google_linked?: boolean
}

export interface VisibleProvider {
  id: string
  models: string[]
}

export interface ModelOption {
  provider: string
  model: string
  label: string
}

export interface Connector {
  id: string
  name: string
  kind: string
  category: string
  icon: string
  desc: string
  status: string
  connected: boolean
  enabled: boolean
}
