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

export const reloadToolHooks = (config: ApiConfig) =>
  apiFetch<ToolHooksStatus>(config, '/api/tool-hooks/reload', { method: 'POST' })

export const getToolHookLog = (config: ApiConfig, limit = 100) =>
  apiFetch<ToolHookLog>(config, `/api/tool-hooks/log?limit=${limit}`)
