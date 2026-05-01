import { useState } from 'react'
import { Save, Wifi, WifiOff } from 'lucide-react'

interface SettingsConfig {
  apiBaseUrl: string
  userId: string
  userName: string
  mode: 'dev' | 'thin-client' | 'standalone'
}

interface Props {
  config: SettingsConfig
  onChange: (patch: Partial<SettingsConfig>) => Promise<void>
  role?: string
}

export function SettingsView({ config, onChange, role = 'owner' }: Props) {
  const isOwner = role === 'owner'
  const [draft, setDraft] = useState(config)
  const [saving, setSaving] = useState(false)
  const [pingResult, setPingResult] =
    useState<{ ok: boolean; latencyMs: number; error?: string } | null>(null)
  const [pinging, setPinging] = useState(false)

  const dirty =
    draft.apiBaseUrl !== config.apiBaseUrl ||
    draft.userId !== config.userId ||
    draft.userName !== config.userName ||
    draft.mode !== config.mode

  const save = async () => {
    setSaving(true)
    try {
      await onChange(draft)
    } finally {
      setSaving(false)
    }
  }

  const ping = async () => {
    setPinging(true)
    try {
      const result = window.jarvisx
        ? await window.jarvisx.pingBackend(draft.apiBaseUrl)
        : await fallbackPing(draft.apiBaseUrl)
      setPingResult(result)
    } finally {
      setPinging(false)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <header className="flex items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold">Settings</h2>
          {!isOwner && (
            <span className="rounded-full bg-bg2 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-fg3">
              view only
            </span>
          )}
        </div>
        {dirty && isOwner && <span className="font-mono text-[10px] text-warn">unsaved</span>}
      </header>

      <div className="flex flex-col gap-6 p-6">
        <Section title="Connection">
          <Field label="Mode" hint="dev = local prod-runtime · thin-client = remote server · standalone (Phase 2+)">
            <select
              value={draft.mode}
              onChange={(e) =>
                setDraft({ ...draft, mode: e.target.value as SettingsConfig['mode'] })
              }
              className="rounded-md border border-line2 bg-bg2 px-3 py-2 text-sm"
            >
              <option value="dev">dev — localhost prod-runtime</option>
              <option value="thin-client">thin-client — remote Jarvis server</option>
              <option value="standalone" disabled>
                standalone — Phase 2+
              </option>
            </select>
          </Field>

          <Field label="API base URL" hint="The Jarvis HTTP API root">
            <input
              type="url"
              value={draft.apiBaseUrl}
              onChange={(e) => setDraft({ ...draft, apiBaseUrl: e.target.value })}
              className="w-full rounded-md border border-line2 bg-bg2 px-3 py-2 font-mono text-sm"
              placeholder="http://localhost"
            />
          </Field>

          <div className="flex items-center gap-3">
            <button
              onClick={ping}
              disabled={pinging}
              className="flex items-center gap-2 rounded-md border border-line2 bg-bg2 px-3 py-1.5 text-xs hover:bg-bg2/80 disabled:opacity-50"
            >
              {pingResult?.ok ? <Wifi size={12} /> : <WifiOff size={12} />}
              {pinging ? 'pinging…' : 'Test connection'}
            </button>
            {pingResult && (
              <span
                className={`font-mono text-[10px] ${
                  pingResult.ok ? 'text-ok' : 'text-danger'
                }`}
              >
                {pingResult.ok
                  ? `up · ${pingResult.latencyMs}ms`
                  : `down · ${pingResult.error}`}
              </span>
            )}
          </div>
        </Section>

        <Section title="Identity">
          <p className="text-xs text-fg3">
            Sent on every request as <code className="font-mono">X-JarvisX-User</code> so
            Jarvis routes to the correct workspace.
          </p>
          <Field label="User ID" hint="Discord ID from users.json">
            <input
              value={draft.userId}
              onChange={(e) => setDraft({ ...draft, userId: e.target.value })}
              className="w-full rounded-md border border-line2 bg-bg2 px-3 py-2 font-mono text-sm"
            />
          </Field>
          <Field label="Display name">
            <input
              value={draft.userName}
              onChange={(e) => setDraft({ ...draft, userName: e.target.value })}
              className="w-full rounded-md border border-line2 bg-bg2 px-3 py-2 text-sm"
            />
          </Field>
        </Section>

        <div>
          <button
            disabled={!dirty || saving || !isOwner}
            onClick={save}
            title={!isOwner ? 'Only owner can change settings' : ''}
            className="flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-bg0 disabled:opacity-40"
          >
            <Save size={14} />
            {saving ? 'Saving…' : 'Save'}
          </button>
          {!isOwner && (
            <p className="mt-2 text-[11px] text-fg3">
              Indstillinger kan kun ændres af owner-rollen.
            </p>
          )}
        </div>

      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-fg3">{title}</h3>
      {children}
    </section>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-fg2">{label}</span>
      {children}
      {hint && <span className="text-[10px] text-fg3">{hint}</span>}
    </label>
  )
}

async function fallbackPing(url: string) {
  // When running in plain `vite dev` without Electron preload, do a simple
  // fetch so the Settings UI still works for browser testing.
  const start = performance.now()
  try {
    const res = await fetch(`${url.replace(/\/$/, '')}/openapi.json`, {
      method: 'GET',
      mode: 'cors',
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return { ok: true, latencyMs: Math.round(performance.now() - start) }
  } catch (e: unknown) {
    return {
      ok: false,
      latencyMs: Math.round(performance.now() - start),
      error: e instanceof Error ? e.message : String(e),
    }
  }
}
