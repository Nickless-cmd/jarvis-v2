import { useEffect, useState, useCallback } from 'react'
import { Check, X, RefreshCw, FileEdit, Database, Sparkles, AlertCircle } from 'lucide-react'
import { s, T } from '../../shared/theme/tokens'
import { backend } from '../../lib/adapters'

const KIND_ICONS = {
  'source-edit': FileEdit,
  'memory-rewrite': Database,
}

function kindIcon(kind) {
  const Icon = KIND_ICONS[kind] || Sparkles
  return <Icon size={14} />
}

function formatBytesDelta(delta) {
  if (delta === undefined || delta === null) return ''
  const n = Number(delta)
  if (!Number.isFinite(n)) return ''
  const sign = n >= 0 ? '+' : ''
  return `${sign}${n} bytes`
}

function ProposalRow({ proposal, onApprove, onReject, busy }) {
  const [showPayload, setShowPayload] = useState(false)
  const [note, setNote] = useState('')
  const kind = String(proposal.kind || 'unknown')
  const payload = proposal.payload || {}
  const status = String(proposal.status || 'pending')
  const isPending = status === 'pending'

  return (
    <div
      style={s({
        border: `1px solid ${T.border0}`,
        borderRadius: 8,
        padding: 12,
        background: T.bgRaised,
        marginBottom: 10,
      })}
    >
      <div style={s({ display: 'flex', alignItems: 'flex-start', gap: 10 })}>
        <div style={s({ color: T.accent, paddingTop: 2 })}>{kindIcon(kind)}</div>
        <div style={s({ flex: 1, minWidth: 0 })}>
          <div
            style={s({
              fontSize: 12,
              fontWeight: 500,
              color: T.text1,
              marginBottom: 2,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            })}
          >
            {proposal.title || '(untitled)'}
          </div>
          <div
            style={s({
              fontSize: 10,
              color: T.text3,
              fontFamily: T.mono,
              display: 'flex',
              gap: 10,
              flexWrap: 'wrap',
            })}
          >
            <span>kind={kind}</span>
            <span>id={String(proposal.proposal_id || '').slice(0, 18)}</span>
            <span>status={status}</span>
            {payload.bytes_delta !== undefined && (
              <span>{formatBytesDelta(payload.bytes_delta)}</span>
            )}
            {payload.relative_path && (
              <span>{String(payload.relative_path).slice(0, 60)}</span>
            )}
          </div>
          {proposal.rationale && (
            <div
              style={s({
                fontSize: 11,
                color: T.text2,
                marginTop: 6,
                lineHeight: 1.4,
              })}
            >
              {proposal.rationale}
            </div>
          )}
          <button
            onClick={() => setShowPayload((v) => !v)}
            style={s({
              marginTop: 6,
              background: 'transparent',
              border: 'none',
              color: T.text3,
              fontSize: 10,
              cursor: 'pointer',
              padding: 0,
            })}
          >
            {showPayload ? '▼ hide payload' : '▶ show payload'}
          </button>
          {showPayload && (
            <pre
              style={s({
                marginTop: 6,
                padding: 8,
                background: T.bgSurface,
                borderRadius: 4,
                fontSize: 10,
                fontFamily: T.mono,
                color: T.text2,
                overflow: 'auto',
                maxHeight: 200,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              })}
            >
              {JSON.stringify(payload, null, 2)}
            </pre>
          )}
          {isPending && (
            <div style={s({ marginTop: 10, display: 'flex', gap: 6, alignItems: 'center' })}>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="optional note"
                style={s({
                  flex: 1,
                  padding: '4px 8px',
                  fontSize: 11,
                  background: T.bgSurface,
                  border: `1px solid ${T.border0}`,
                  borderRadius: 4,
                  color: T.text1,
                })}
              />
              <button
                onClick={() => onApprove(proposal.proposal_id, note)}
                disabled={busy}
                style={s({
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '4px 10px',
                  background: T.accent,
                  color: T.accentText || '#fff',
                  border: 'none',
                  borderRadius: 4,
                  fontSize: 11,
                  cursor: busy ? 'not-allowed' : 'pointer',
                  opacity: busy ? 0.5 : 1,
                })}
              >
                <Check size={12} /> Approve
              </button>
              <button
                onClick={() => onReject(proposal.proposal_id, note)}
                disabled={busy}
                style={s({
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '4px 10px',
                  background: 'transparent',
                  color: T.text2,
                  border: `1px solid ${T.border0}`,
                  borderRadius: 4,
                  fontSize: 11,
                  cursor: busy ? 'not-allowed' : 'pointer',
                  opacity: busy ? 0.5 : 1,
                })}
              >
                <X size={12} /> Reject
              </button>
            </div>
          )}
          {!isPending && proposal.resolution_note && (
            <div
              style={s({
                marginTop: 6,
                fontSize: 10,
                color: T.text3,
                fontStyle: 'italic',
              })}
            >
              {status}: {proposal.resolution_note}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function AutonomyProposalsPanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await backend.getAutonomyProposals(30)
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [load])

  const handleApprove = useCallback(
    async (proposalId, note) => {
      setBusyId(proposalId)
      try {
        await backend.approveAutonomyProposal(proposalId, note)
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setBusyId('')
      }
    },
    [load]
  )

  const handleReject = useCallback(
    async (proposalId, note) => {
      setBusyId(proposalId)
      try {
        await backend.rejectAutonomyProposal(proposalId, note)
        await load()
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setBusyId('')
      }
    },
    [load]
  )

  const pending = (data?.items || []).filter((p) => String(p.status || '') === 'pending')
  const recent = (data?.recent || []).filter((p) => String(p.status || '') !== 'pending').slice(0, 10)

  return (
    <div
      style={s({
        border: `1px solid ${T.border0}`,
        borderRadius: 10,
        padding: 16,
        background: T.bgSurface,
      })}
    >
      <div
        style={s({
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
        })}
      >
        <div>
          <div style={s({ fontSize: 13, fontWeight: 500, color: T.text1 })}>
            Autonomy Proposals
          </div>
          <div style={s({ fontSize: 11, color: T.text3, marginTop: 2 })}>
            {data?.summary || 'Loading...'}
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={s({
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 10px',
            background: 'transparent',
            color: T.text2,
            border: `1px solid ${T.border0}`,
            borderRadius: 4,
            fontSize: 11,
            cursor: loading ? 'not-allowed' : 'pointer',
          })}
        >
          <RefreshCw size={12} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {error && (
        <div
          style={s({
            padding: 8,
            marginBottom: 10,
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 4,
            color: '#ef4444',
            fontSize: 11,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          })}
        >
          <AlertCircle size={12} /> {error}
        </div>
      )}

      {data?.registered_kinds && (
        <div
          style={s({
            fontSize: 10,
            color: T.text3,
            fontFamily: T.mono,
            marginBottom: 10,
          })}
        >
          executors: {data.registered_kinds.join(', ') || 'none'}
        </div>
      )}

      {pending.length === 0 && !loading && (
        <div
          style={s({
            padding: 20,
            textAlign: 'center',
            color: T.text3,
            fontSize: 11,
            fontStyle: 'italic',
          })}
        >
          No pending proposals
        </div>
      )}

      {pending.length > 0 && (
        <div style={s({ marginBottom: 16 })}>
          <div
            style={s({
              fontSize: 10,
              color: T.text3,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 6,
            })}
          >
            Pending ({pending.length})
          </div>
          {pending.map((proposal) => (
            <ProposalRow
              key={proposal.proposal_id}
              proposal={proposal}
              onApprove={handleApprove}
              onReject={handleReject}
              busy={busyId === proposal.proposal_id}
            />
          ))}
        </div>
      )}

      {recent.length > 0 && (
        <div>
          <div
            style={s({
              fontSize: 10,
              color: T.text3,
              textTransform: 'uppercase',
              letterSpacing: 1,
              marginBottom: 6,
            })}
          >
            Recent ({recent.length})
          </div>
          {recent.map((proposal) => (
            <ProposalRow
              key={proposal.proposal_id}
              proposal={proposal}
              onApprove={handleApprove}
              onReject={handleReject}
              busy={false}
            />
          ))}
        </div>
      )}
    </div>
  )
}
