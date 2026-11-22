import { apiFetch, type ApiConfig } from './api'

export interface HookInfo {
  name: string
  match: string
  before: boolean
  after: boolean
  timeout_s: number
  active: boolean
}

export interface HookLogMeta {
  path: string
  exists: boolean
  size_bytes: number
  rotated: boolean
  rotated_path: string
}

export interface ToolHooksStatus {
  enabled: boolean
  config: string
  config_findes: boolean
  hooks: HookInfo[]
  fejl?: string
  log: HookLogMeta
}

export interface HookLogEntry {
  time?: string
  timestamp?: string
  ts?: string
  tool?: string
  tool_name?: string
  phase?: string
  result?: unknown
  status?: string
  exit_code?: number
}

export interface ToolHookLog {
  entries: HookLogEntry[]
  coverage_24h: { confined: number; fail_open: number; non_shell: number }
  invalid_lines: number
  log: HookLogMeta
}

export const getToolHooks = (config: ApiConfig) =>
  apiFetch<ToolHooksStatus>(config, '/api/tool-hooks')

/** Det rå config-dokument — med kommandoerne, som redigeringen skal have dem.
 *  `status()` svarer kun `before: true/false`, hvilket ikke er nok til at
 *  skrive en regel tilbage uden at afvæbne den. */
export interface RawHooksConfig {
  enabled: boolean
  hooks: Record<string, unknown>[]
  findes: boolean
  fejl?: string
}

export const getToolHookConfig = (config: ApiConfig) =>
  apiFetch<RawHooksConfig>(config, '/api/tool-hooks/config')

export const reloadToolHooks = (config: ApiConfig) =>
  apiFetch<ToolHooksStatus>(config, '/api/tool-hooks/reload', { method: 'POST' })

export const getToolHookLog = (config: ApiConfig, limit = 100) =>
  apiFetch<ToolHookLog>(config, `/api/tool-hooks/log?limit=${limit}`)

/** Én redigerbar regel. Samme felter som config-filen, så fladen og filen
 *  ikke kan komme til at tale om forskellige ting. */
export interface HookRule {
  name: string
  match: string
  before: string
  after: string
  timeout_s: number
  cwd: string
}

export interface HooksConfigPayload {
  enabled: boolean
  hooks: HookRule[]
  approved?: boolean
}

export interface HooksSaveResult extends ToolHooksStatus {
  ok: boolean
  skrevet: boolean
  backup?: string
}

export interface HooksValidation {
  ok: boolean
  fejl: string[]
}

/** Tør kørsel: hvad ville fejle, uden at skrive noget. */
export const validateToolHooks = (config: ApiConfig, payload: HooksConfigPayload) =>
  apiFetch<HooksValidation>(config, '/api/tool-hooks/validate', { method: 'POST', body: payload })

/** Erstatter hele konfigurationen. `approved` er ikke kosmetik: reglerne
 *  bestemmer hvad der kører shell på hvert tool-kald, og serveren afviser
 *  et gem uden den med 409. */
export const saveToolHooks = (config: ApiConfig, payload: HooksConfigPayload) =>
  apiFetch<HooksSaveResult>(config, '/api/tool-hooks', {
    method: 'PUT',
    body: { ...payload, approved: true },
    timeoutMs: 20_000,
  })

