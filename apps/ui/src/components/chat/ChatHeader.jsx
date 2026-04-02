import { Activity, Search, Settings, RefreshCw } from 'lucide-react'
import { Chip } from '../shared/Chip'

export function ChatHeader({
  session,
  selection,
  onRefresh,
  isRefreshing,
  isStreaming,
}) {
  const provider = selection.currentProvider || 'unknown'

  return (
    <section className="chat-header-bar">
      <div className="chat-header-left">
        <span className="chat-header-session-title">{session?.title || 'Ny chat'}</span>
        <div className="chat-header-chips">
          <Chip color="#3d8f7c">L3</Chip>
          <Chip color="#d4963a">EXP</Chip>
          <Chip color="#4e5262">{provider}</Chip>
        </div>
      </div>

      <div className="chat-header-right">
        <div className={`chat-token-meter ${isStreaming ? 'active' : ''}`}>
          <Activity size={9} />
          <span className="mono">— tok/min</span>
        </div>

        <button className="icon-btn" onClick={onRefresh} title="Refresh">
          <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
        </button>
        <button className="icon-btn" title="Search"><Search size={14} /></button>
        <button className="icon-btn" title="Settings"><Settings size={14} /></button>
      </div>
    </section>
  )
}
