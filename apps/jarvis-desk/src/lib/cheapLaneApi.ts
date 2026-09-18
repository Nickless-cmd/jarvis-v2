/** Cheap lane + provider-registret — datalag for de owner-only flader.
 *
 *  Bjørn 16/9-2026: «cheap lane er især vigtigt for jeg ander intet om hvordan
 *  cheap lane eller load_balanceren klarer sig». Der er to kilder, og de svarer
 *  på hvert sit spørgsmål:
 *
 *    balancer-snapshot  → NU: hvilke slots er i køling, hvad er vægten lige nu
 *    historik           → FORLØBET: 90.000 kald med udfald, latens og pris
 *
 *  Løse typer med valgfrie felter, som resten af desk: en flade må aldrig vælte
 *  på et felt backenden holder op med at sende.
 */
import { apiFetch, type ApiConfig } from './api'

export interface BalancerSlot {
  slot_id: string
  provider?: string
  model?: string
  auth_profile?: string
  egress?: string
  status?: 'healthy' | 'cooldown' | 'disabled' | 'stale' | 'recovering' | string
  rpm_limit?: number
  daily_limit?: number
  rpm_used?: number
  daily_used?: number
  daily_headroom?: number
  headroom_pct?: number
  weight?: number
  cooldown_until?: string | null
  cooldown_reason?: string | null
  breaker_level?: number
  consecutive_failures?: number
  manually_disabled?: boolean
  total_calls?: number
  total_failures?: number
  success_rate?: number | null
  last_success_at?: string | null
  stale?: boolean
}

export interface BalancerState {
  enabled?: boolean
  pool_size?: number
  eligible_now?: number
  blocked_now?: number
  header?: {
    total_slots?: number
    healthy?: number
    cooldown?: number
    disabled?: number
    stale?: number
    breaker?: number
    recovering?: number
    by_profile?: Record<string, number>
    by_egress?: Record<string, number>
    providers?: number
  }
  slots?: BalancerSlot[]
  recent_calls?: { at?: string; slot_id?: string; daemon?: string; status?: string; latency_ms?: number; error?: string }[]
}

export interface HistorikUdbyder {
  provider: string
  model: string
  auth_profile?: string
  kald: number
  ok: number
  fejl: number
  /** `null` = ingen kald i vinduet. «Ingen data» er ikke «nul procent». */
  succesrate: number | null
  latens_p50_ms: number
  latens_p95_ms: number
  pris_usd: number
  sidste_kald?: string
  sidste_ok?: string | null
  fejlkoder: { kode: string; antal: number }[]
}

export interface Historik {
  aktiv?: boolean
  timer?: number
  udbydere: HistorikUdbyder[]
  opsummering?: {
    kald: number; ok: number; fejl: number
    succesrate: number | null; pris_usd: number; udbydere: number
  }
}

export interface FejlRaekke {
  provider?: string
  model?: string
  auth_profile?: string
  error_code?: string
  error_message?: string
  retry_after_seconds?: number
  latency_ms?: number
  created_at?: string
}

/** `antal_i_vinduet` er det ÆGTE tal; `vist` er kun hvad loftet gav.
 *  De to holdes adskilt med vilje — et limit-vindue der ligner et facit har
 *  kostet huset tre forkerte konklusioner. */
export interface FejlSvar {
  raekker: FejlRaekke[]
  vist?: number
  antal_i_vinduet?: number
}

export interface TidsserieSpand {
  tid: string
  kald: number
  fejl: number
  latens_ms: number
}

export interface RegistretModel {
  provider?: string
  model?: string
  lane?: string
  enabled?: boolean
  priority?: number
  probe_score?: number | null
  disabled_at?: string
  disabled_reason?: string
  updated_at?: string
}

export interface RegistretUdbyder {
  provider: string
  auth_mode?: string
  auth_profile?: string
  base_url?: string
  enabled?: boolean
  credentials_ready?: boolean
  model_count?: number
  enabled_model_count?: number
  updated_at?: string
}

export interface Registret {
  udbydere: RegistretUdbyder[]
  modeller: RegistretModel[]
  lanes?: Record<string, { i_alt: number; aktive: number }>
  opsummering?: { udbydere: number; modeller: number; aktive_modeller: number }
}

// ── læsning ──────────────────────────────────────────────────────────────

export function getBalancerState(config: ApiConfig): Promise<BalancerState> {
  return apiFetch<BalancerState>(config, '/mc/cheap-balancer-state')
}

export function getHistorik(config: ApiConfig, timer = 24): Promise<Historik> {
  return apiFetch<Historik>(config, `/mc/cheap-lane/history?timer=${timer}`)
}

export function getFejl(config: ApiConfig, timer = 24, loft = 100): Promise<FejlSvar> {
  return apiFetch<FejlSvar>(config, `/mc/cheap-lane/errors?timer=${timer}&loft=${loft}`)
}

export function getTidsserie(
  config: ApiConfig, timer = 24, spand = 60,
): Promise<{ spand: TidsserieSpand[] }> {
  return apiFetch<{ spand: TidsserieSpand[] }>(
    config, `/mc/cheap-lane/timeseries?timer=${timer}&spand_minutter=${spand}`)
}

export function getRegistret(config: ApiConfig): Promise<Registret> {
  return apiFetch<Registret>(config, '/mc/provider-registry')
}

// ── handlinger ───────────────────────────────────────────────────────────

/** Slot-handlinger rammer balancerens EGEN tilstand (JSON-filen), ikke registret.
 *  Et slot slået fra her kommer tilbage ved næste `refresh-pool`-runde med
 *  `manually_disabled` bevaret — det er en pause, ikke en fjernelse. */
export function slotHandling(
  config: ApiConfig, slotId: string, handling: 'reset' | 'disable' | 'enable',
): Promise<{ status?: string }> {
  return apiFetch(config, `/mc/cheap-balancer/slot/${encodeURIComponent(slotId)}/${handling}`,
    { method: 'POST' })
}

export function refreshPool(config: ApiConfig): Promise<{ status?: string; pool_size?: number }> {
  return apiFetch(config, '/mc/cheap-balancer/refresh-pool', { method: 'POST' })
}

/** Registret er den varige sandhed: slår man en model fra her, er den væk af
 *  puljen ved næste opbygning — også efter en genstart. */
export function saetModel(
  config: ApiConfig, provider: string, model: string, aktiv: boolean, grund = '',
): Promise<{ status?: string; fejl?: string }> {
  return apiFetch(config, '/mc/provider-registry/model',
    { method: 'POST', body: { provider, model, aktiv, grund } })
}

export function saetUdbyder(
  config: ApiConfig, provider: string, aktiv: boolean, grund = '',
): Promise<{ status?: string; fejl?: string }> {
  return apiFetch(config, '/mc/provider-registry/provider',
    { method: 'POST', body: { provider, aktiv, grund } })
}

export function fjernModel(
  config: ApiConfig, provider: string, model: string,
): Promise<{ status?: string; fejl?: string }> {
  return apiFetch(config,
    `/mc/provider-registry/model?provider=${encodeURIComponent(provider)}&model=${encodeURIComponent(model)}`,
    { method: 'DELETE' })
}

export function fjernUdbyder(
  config: ApiConfig, provider: string,
): Promise<{ status?: string; fejl?: string }> {
  return apiFetch(config,
    `/mc/provider-registry/provider?provider=${encodeURIComponent(provider)}`,
    { method: 'DELETE' })
}

export function getBackups(config: ApiConfig): Promise<{ backups: { navn: string; tid: string; bytes: number }[] }> {
  return apiFetch(config, '/mc/provider-registry/backups')
}

export function gendanBackup(config: ApiConfig, sti = ''): Promise<{ status?: string; fejl?: string }> {
  return apiFetch(config, '/mc/provider-registry/restore',
    { method: 'POST', body: { sti } })
}

// ── udbyder-fladen (16/9-2026) ───────────────────────────────────────────

export interface UdbyderHelbred {
  provider?: string
  ok?: boolean
  degraded?: boolean
  latency_ms?: number
}

/** `api_key` er valgfri: tom rører ikke legitimationen, så en model kan
 *  tilføjes til en udbyder der allerede har sin nøgle. Nøglen gemmes i
 *  auth-profilen, aldrig i registret, og kommer aldrig tilbage i svaret. */
export function tilfoejUdbyder(
  config: ApiConfig,
  felter: { provider: string; model: string; lane?: string; auth_mode?: string;
    auth_profile?: string; base_url?: string; api_key?: string },
): Promise<{ status?: string; fejl?: string; noegle_gemt?: boolean }> {
  return apiFetch(config, '/mc/provider-registry/add', { method: 'POST', body: felter })
}

/** Flytning er ikke en slukning: modellen bliver aktiv, men i en anden lane. */
export function saetLane(
  config: ApiConfig, provider: string, model: string, lane: string,
): Promise<{ status?: string; fejl?: string; fra?: string; til?: string }> {
  return apiFetch(config, '/mc/provider-registry/lane',
    { method: 'POST', body: { provider, model, lane } })
}

export function getUdbyderHelbred(
  config: ApiConfig,
): Promise<{ providers?: UdbyderHelbred[]; checked_at?: string; summary?: unknown }> {
  return apiFetch(config, '/central/providers')
}

// ── kontrolcentret (18/9-2026) ───────────────────────────────────────────
//
// Ét sammensat snapshot i stedet for fire uafhængige hentninger med hver sin
// timer. Backenden pakker hver sektion i en konvolut med KILDE og FRISKHED,
// så en flade kan sige «balanceren svarede ikke» uden at resten af skærmen
// går i sort — og uden at klienten opfinder sin egen sandhed om hvad der er
// aktuelt.

export type Freskhed = 'live' | 'stale' | 'unknown'

export interface ApiProblem { code?: string; message?: string; detail?: string }

/** En sektion kan mangle uden at snapshotet er ugyldigt. Derfor `data: T | null`
 *  OG `error` — hvis begge er tomme, blev sektionen aldrig forsøgt. */
export interface Sektion<T> {
  source: string
  observed_at: string | null
  freshness: Freskhed
  data: T | null
  error: ApiProblem | null
}

/** Ukendt kapacitet er `null`, aldrig 0 — og enheder blandes aldrig sammen.
 *  «0 tilbage» og «vi ved det ikke» er to forskellige beskeder til en der
 *  skal beslutte om han kan køre videre. */
export interface KvoteVindue {
  period: 'minute' | 'day' | 'week' | 'month' | string
  unit: 'tokens' | 'requests' | 'credits_usd' | string
  provider?: string
  auth_profile?: string
  limit: number | null
  used: number
  remaining: number | null
  source: 'provider' | 'configured' | 'estimated' | 'unknown' | string
  confidence: number | null
  reset_at: string | null
}

export interface Kapacitet {
  generated_at?: string
  windows?: KvoteVindue[]
  totals?: Record<string, { limit: number | null; used: number; remaining: number | null }>
  unknown_members?: { provider?: string; auth_profile?: string; reason?: string }[]
}

export interface Fund {
  code: string
  severity: 'high' | 'medium' | 'low' | string
  evidence?: Record<string, unknown>
  first_observed_at?: string
  last_observed_at?: string
  provider?: string | null
  slot_id?: string | null
  central_incident_id?: string | null
}

export interface Diagnose {
  generated_at?: string
  status?: string
  findings?: Fund[]
}

export interface Tendenser {
  requests?: number
  tokens?: number
  errors?: number
  cost_usd?: number
  truncated?: boolean
}

export interface Noegletal {
  requests?: number
  tokens?: number
  errors?: number
  cost_usd?: number
  eligible_slots?: number
  active_findings?: number
}

export interface Snapshot {
  schema_version: number
  generated_at: string
  window_hours: number
  status: string
  kpis: Noegletal
  sections: {
    capacity?: Sektion<Kapacitet>
    providers?: Sektion<Registret>
    balancer?: Sektion<BalancerState>
    trends?: Sektion<Tendenser>
    diagnostics?: Sektion<Diagnose>
    central?: Sektion<{ id?: string; ts?: string; cluster?: string; nerve?: string; kind?: string; severity?: string; message?: string }[]>
  }
}

export interface LogLinje {
  invocation_id?: string
  at?: string
  provider?: string
  model?: string
  auth_profile?: string
  daemon?: string
  status?: string
  error_class?: string
  error?: string
  latency_ms?: number
  tokens_in?: number
  tokens_out?: number
  cost_usd?: number
  correlation_id?: string
  has_payload?: boolean
}

export interface LogSide {
  items?: LogLinje[]
  next_cursor?: string | null
  count?: number
  truncated?: boolean
}

export interface LogFilter {
  hours?: number
  provider?: string
  model?: string
  auth_profile?: string
  daemon?: string
  status?: string
  error_class?: string
  correlation_id?: string
  query?: string
  cursor?: string
  limit?: number
}

export interface Revision {
  at?: string
  actor?: string
  action?: string
  target?: string
  reason?: string
  outcome?: string
  revision?: string
}

export function getDashboard(config: ApiConfig, timer = 24): Promise<Snapshot> {
  return apiFetch<Snapshot>(config, `/mc/cheap-lane/dashboard?hours=${timer}`)
}

export function getKapacitet(config: ApiConfig): Promise<Kapacitet> {
  return apiFetch<Kapacitet>(config, '/mc/cheap-lane/capacity')
}

export function getLogs(config: ApiConfig, filter: LogFilter = {}): Promise<LogSide> {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(filter)) {
    if (v !== undefined && v !== null && String(v) !== '') q.set(k, String(v))
  }
  return apiFetch<LogSide>(config, `/mc/cheap-lane/logs?${q.toString()}`)
}

export function getLogDetalje(config: ApiConfig, invocationId: string): Promise<LogLinje & {
  request_payload?: string | null; response_payload?: string | null; redacted?: boolean
}> {
  return apiFetch(config, `/mc/cheap-lane/logs/${encodeURIComponent(invocationId)}`)
}

export function getDiagnose(config: ApiConfig): Promise<Diagnose> {
  return apiFetch<Diagnose>(config, '/mc/cheap-lane/diagnostics')
}

export function getRevisioner(config: ApiConfig, loft = 100): Promise<{ items?: Revision[] }> {
  return apiFetch(config, `/mc/cheap-lane/audit?limit=${loft}`)
}

/** Ingen gentagelse i klienten: en kontrol-handling er IKKE idempotent, og en
 *  stille genafsendelse ville kunne pause den samme udbyder to gange med to
 *  revisioner i sporet. Fejler den, skal mennesket se det og vælge selv. */
export function udfoerKontrol(
  config: ApiConfig,
  kommando: { action: string; target: string; reason?: string; expected_revision?: string;
    parameters?: Record<string, unknown> },
): Promise<{ status?: string; revision?: string; detail?: string }> {
  return apiFetch(config, '/mc/cheap-lane/control', { method: 'POST', body: kommando })
}

export function simulerRute(
  config: ApiConfig, taskKind = 'default', skipProviders: string[] = [],
): Promise<{ candidates?: { provider?: string; model?: string; slot_id?: string; weight?: number;
  eligible?: boolean; reason?: string }[]; chosen?: string | null }> {
  return apiFetch(config, '/mc/cheap-lane/simulate-route',
    { method: 'POST', body: { task_kind: taskKind, skip_providers: skipProviders } })
}
