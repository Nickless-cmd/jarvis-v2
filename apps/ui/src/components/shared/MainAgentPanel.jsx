import { useEffect, useMemo, useState } from 'react'

export function MainAgentPanel({ selection, onSave }) {
  const [provider, setProvider] = useState(selection.currentProvider)
  const [model, setModel] = useState(selection.currentModel)
  const [authProfile, setAuthProfile] = useState(selection.currentAuthProfile)

  useEffect(() => {
    setProvider(selection.currentProvider)
    setModel(selection.currentModel)
    setAuthProfile(selection.currentAuthProfile)
  }, [selection])

  const providers = useMemo(() => [...new Set(selection.availableConfiguredTargets.map((x) => x.provider))], [selection])
  const models = useMemo(() => selection.availableConfiguredTargets.filter((x) => x.provider === provider), [selection, provider])

  return (
    <section className="support-card authority-card">
      <div className="panel-header stacked">
        <div>
          <h3>Main agent</h3>
          <p className="muted">Future UI-ready selection surface</p>
        </div>
      </div>

      <label>
        <span>Provider</span>
        <select value={provider} onChange={(e) => {
          const next = e.target.value
          setProvider(next)
          const first = selection.availableConfiguredTargets.find((x) => x.provider === next)
          if (first) {
            setModel(first.model)
            setAuthProfile(first.authProfile || '')
          }
        }}>
          {providers.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>

      <label>
        <span>Model</span>
        <select value={model} onChange={(e) => {
          const next = e.target.value
          setModel(next)
          const candidate = models.find((x) => x.model === next)
          if (candidate) setAuthProfile(candidate.authProfile || '')
        }}>
          {models.map((item) => <option key={item.model} value={item.model}>{item.model}</option>)}
        </select>
      </label>

      <label>
        <span>Auth profile</span>
        <input value={authProfile} onChange={(e) => setAuthProfile(e.target.value)} />
      </label>

      <button className="primary-btn" onClick={() => onSave({ provider, model, authProfile })}>Save selection</button>

      <div className="candidate-list">
        {selection.availableConfiguredTargets.map((target) => (
          <div key={`${target.provider}:${target.model}`} className="candidate-row">
            <div>
              <strong>{target.provider}</strong>
              <span>{target.model}</span>
            </div>
            <small className={`hint ${target.readinessHint}`}>{target.readinessHint}</small>
          </div>
        ))}
      </div>
    </section>
  )
}
