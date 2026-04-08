import { useEffect, useMemo, useRef, useState } from 'react'
import { backend } from '../../lib/adapters'

export function MainAgentPanel({ selection, onSave, embedded = false }) {
  const [provider, setProvider] = useState(selection.currentProvider)
  const [model, setModel] = useState(selection.currentModel)
  const [authProfile, setAuthProfile] = useState(selection.currentAuthProfile)
  const [liveProviderModels, setLiveProviderModels] = useState([])
  const providerModelsRequestRef = useRef(0)

  useEffect(() => {
    setProvider(selection.currentProvider)
    setModel(selection.currentModel)
    setAuthProfile(selection.currentAuthProfile)
  }, [selection.currentProvider, selection.currentModel, selection.currentAuthProfile])

  const configuredTargets = selection.availableConfiguredTargets || []

  const configuredModels = useMemo(
    () => configuredTargets.filter((x) => x.provider === provider),
    [configuredTargets, provider]
  )

  async function refreshProviderModels(nextProvider, nextAuthProfile) {
    if (!nextProvider) {
      setLiveProviderModels([])
      return []
    }
    const requestId = providerModelsRequestRef.current + 1
    providerModelsRequestRef.current = requestId
    try {
      const payload = await backend.getProviderModels({
        provider: nextProvider,
        authProfile: nextAuthProfile || '',
      })
      if (providerModelsRequestRef.current !== requestId) return []
      const models = (payload.models || []).map((item) => ({
        model: item.id,
        label: item.label || item.id,
        authProfile: payload.authProfile || nextAuthProfile || '',
      }))
      setLiveProviderModels(models)
      return models
    } catch {
      if (providerModelsRequestRef.current === requestId) {
        setLiveProviderModels([])
      }
      return []
    }
  }

  useEffect(() => {
    void refreshProviderModels(selection.currentProvider, selection.currentAuthProfile)
  }, [selection.currentProvider, selection.currentAuthProfile])

  const providers = useMemo(
    () => [...new Set([selection.currentProvider || '', ...configuredTargets.map((x) => x.provider)].filter(Boolean))],
    [configuredTargets, selection.currentProvider]
  )
  const models = useMemo(
    () => (liveProviderModels.length ? liveProviderModels : configuredModels.map((item) => ({
      model: item.model,
      label: item.model,
      authProfile: item.authProfile || '',
    }))),
    [configuredModels, liveProviderModels]
  )

  return (
    <section className={embedded ? 'authority-card embedded' : 'support-card authority-card'}>
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
          void (async () => {
            setProvider(next)
            const configured = configuredTargets.find((x) => x.provider === next)
            const nextAuthProfile = configured?.authProfile || (next === selection.currentProvider ? selection.currentAuthProfile || '' : '')
            setAuthProfile(nextAuthProfile)
            const liveModels = await refreshProviderModels(next, nextAuthProfile)
            const options = liveModels.length ? liveModels : configuredTargets
              .filter((x) => x.provider === next)
              .map((item) => ({
                model: item.model,
                label: item.model,
                authProfile: item.authProfile || '',
              }))
            setModel(options[0]?.model || '')
          })()
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
          {models.map((item) => <option key={item.model} value={item.model}>{item.label || item.model}</option>)}
        </select>
      </label>

      <label>
        <span>Auth profile</span>
        <input value={authProfile} onChange={(e) => setAuthProfile(e.target.value)} />
      </label>

      <button className="primary-btn" onClick={() => onSave({ provider, model, authProfile })}>Save selection</button>

      {!embedded ? (
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
      ) : null}
    </section>
  )
}
