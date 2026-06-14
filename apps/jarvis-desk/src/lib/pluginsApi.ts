import { apiFetch, type ApiConfig } from './api'

export interface PluginRuleset {
  allowed_channels?: string[]
  blocked_roles?: string[]
  quiet_hours?: [number, number]
  rate_limits?: Record<string, number>
}

export interface PluginsOverview {
  available: unknown[]
  connected: unknown[]
  rulesets: Record<string, PluginRuleset>
}

export async function getPluginsOverview(config: ApiConfig): Promise<PluginsOverview> {
  return apiFetch<PluginsOverview>(config, '/plugins')
}

export async function putPluginRuleset(
  config: ApiConfig,
  pluginId: string,
  ruleset: PluginRuleset,
): Promise<void> {
  await apiFetch(config, `/plugins/rulesets/${encodeURIComponent(pluginId)}`, {
    method: 'PUT',
    body: ruleset,
  })
}
