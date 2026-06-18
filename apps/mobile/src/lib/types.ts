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
