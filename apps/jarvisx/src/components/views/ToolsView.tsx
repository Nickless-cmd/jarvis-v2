import { useState } from 'react'
import { Wrench, Cpu, HardDrive, Database, Search, RefreshCw } from 'lucide-react'
import { useMcEndpoint } from '../../lib/useMcEndpoint'

interface SystemHealth {
  cpu_pct?: string
  ram_pct?: string
  ram_used_gb?: string
  ram_total_gb?: string
  disk_free_mb?: string
  disk_free_gb?: string
}

interface Tool {
  name: string
  description: string
  required?: string[]
}

interface SkillsResp {
  tools: Tool[]
}

export function ToolsView({ apiBaseUrl }: { apiBaseUrl: string }) {
  const sys = useMcEndpoint<SystemHealth>(apiBaseUrl, '/mc/system/health', 5000)
  const skills = useMcEndpoint<SkillsResp>(apiBaseUrl, '/mc/skills', 0)
  const [filter, setFilter] = useState('')

  const tools = skills.data?.tools ?? []
  const filtered = filter.trim()
    ? tools.filter(
        (t) =>
          t.name.toLowerCase().includes(filter.toLowerCase()) ||
          t.description.toLowerCase().includes(filter.toLowerCase()),
      )
    : tools

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold">Værktøjer</h2>
          <span className="font-mono text-[10px] text-fg3">
            {tools.length} tools · system 5s polling
          </span>
        </div>
        <button
          onClick={() => {
            sys.refresh()
            skills.refresh()
          }}
          className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2 py-1 text-[10px] text-fg2 hover:text-accent"
        >
          <RefreshCw size={10} />
          refresh
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {/* System health row */}
        <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <SysCard
            Icon={Cpu}
            label="CPU"
            value={sys.data?.cpu_pct}
            unit="%"
            pct={parseFloat(sys.data?.cpu_pct || '0') / 100}
            color="#5ab8a0"
          />
          <SysCard
            Icon={HardDrive}
            label="RAM"
            value={sys.data?.ram_pct}
            unit="%"
            pct={parseFloat(sys.data?.ram_pct || '0') / 100}
            color="#58a6ff"
            secondary={
              sys.data?.ram_used_gb && sys.data?.ram_total_gb
                ? `${sys.data.ram_used_gb} / ${sys.data.ram_total_gb} GB`
                : undefined
            }
          />
          <SysCard
            Icon={Database}
            label="Disk free"
            value={sys.data?.disk_free_gb}
            unit="GB"
            pct={undefined}
            color="#d4963a"
          />
          <SysCard
            Icon={Wrench}
            label="Tools"
            value={tools.length.toString()}
            unit=""
            pct={undefined}
            color="#bc8cff"
          />
        </div>

        {/* Tools catalog */}
        <div className="rounded-lg border border-line bg-bg1">
          <div className="flex items-center gap-3 border-b border-line px-4 py-2.5">
            <Search size={12} className="text-fg3" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filtrér værktøjer…"
              className="flex-1 bg-transparent text-xs text-fg placeholder:text-fg3 focus:outline-none"
            />
            {filter && (
              <button
                onClick={() => setFilter('')}
                className="font-mono text-[10px] text-fg3 hover:text-fg"
              >
                clear
              </button>
            )}
            <span className="font-mono text-[10px] text-fg3">
              {filtered.length} / {tools.length}
            </span>
          </div>
          <div className="divide-y divide-line/40">
            {skills.loading && tools.length === 0 && (
              <div className="px-4 py-3 text-[11px] text-fg3">loading tools…</div>
            )}
            {filtered.map((t) => (
              <div
                key={t.name}
                className="grid grid-cols-[180px,1fr] gap-3 px-4 py-2.5 transition-colors hover:bg-bg2/30"
              >
                <div className="flex items-start gap-2">
                  <Wrench size={11} className="mt-1 flex-shrink-0 text-accent" />
                  <span className="break-all font-mono text-xs text-fg">
                    {t.name}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] leading-relaxed text-fg2">
                    {t.description}
                  </p>
                  {t.required && t.required.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {t.required.map((r) => (
                        <span
                          key={r}
                          className="rounded bg-bg2 px-1.5 py-0.5 font-mono text-[9px] text-fg3"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {filtered.length === 0 && tools.length > 0 && (
              <div className="px-4 py-3 text-[11px] text-fg3">
                Ingen match for "{filter}"
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function SysCard({
  Icon,
  label,
  value,
  unit,
  pct,
  color,
  secondary,
}: {
  Icon: typeof Cpu
  label: string
  value?: string
  unit: string
  pct?: number
  color: string
  secondary?: string
}) {
  return (
    <div className="rounded-lg border border-line bg-bg1 p-4">
      <div className="mb-2 flex items-center gap-2">
        <Icon size={14} style={{ color }} />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
          {label}
        </span>
      </div>
      <div className="mb-2 flex items-baseline gap-1">
        <span className="text-2xl font-semibold tabular-nums text-fg">
          {value ?? '—'}
        </span>
        {unit && <span className="text-xs text-fg3">{unit}</span>}
      </div>
      {pct != null && (
        <div className="overflow-hidden rounded-full bg-bg2" style={{ height: 4 }}>
          <div
            className="h-full transition-all duration-500 ease-out"
            style={{
              width: `${Math.max(0, Math.min(1, pct)) * 100}%`,
              background: `linear-gradient(90deg, ${color}80, ${color})`,
            }}
          />
        </div>
      )}
      {secondary && (
        <div className="mt-1 font-mono text-[10px] text-fg3">{secondary}</div>
      )}
    </div>
  )
}
