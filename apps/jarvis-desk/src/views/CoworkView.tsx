import { useSettings } from '../hooks/useSettings'
import { useCoworkData } from '../hooks/useCoworkData'
import { ApprovalQueue } from '../components/cowork/ApprovalQueue'
import { PlansPane } from '../components/cowork/PlansPane'
import { TodoPane } from '../components/cowork/TodoPane'
import { ChannelsPane } from '../components/cowork/ChannelsPane'

/** Cowork: rolle-bevidst arbejd-sammen-dashboard. Owner ser fire ruder; member
 *  ser tre (ingen kanaler). Ren oversigt + godkend/afvis — ingen chat-lane. */
export function CoworkView({ role = 'owner' }: { role?: 'owner' | 'member' | 'guest' }) {
  const { settings } = useSettings()
  const isOwner = role === 'owner'
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const { queue, plans, todos, channels, resolve } = useCoworkData(config, isOwner)

  return (
    <div className="coworkview">
      <div className="cowork-grid">
        <section className="cowork-pane">
          <div className="cowork-pane-head">Godkendelser <span className="cowork-count">{queue.length}</span></div>
          <ApprovalQueue items={queue} onResolve={resolve} />
        </section>
        <section className="cowork-pane">
          <div className="cowork-pane-head">Planer <span className="cowork-count">{plans.length}</span></div>
          <PlansPane plans={plans} />
        </section>
        <section className="cowork-pane">
          <div className="cowork-pane-head">Todo &amp; initiativer</div>
          <TodoPane todos={todos} />
        </section>
        {isOwner && (
          <section className="cowork-pane">
            <div className="cowork-pane-head">Kanaler</div>
            <ChannelsPane channels={channels} />
          </section>
        )}
      </div>
    </div>
  )
}
