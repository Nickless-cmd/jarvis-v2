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
