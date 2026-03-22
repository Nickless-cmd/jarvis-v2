import { RefreshCw } from 'lucide-react'

function uniqueProviders(selection) {
  return [...new Set(selection.availableConfiguredTargets.map((target) => target.provider))]
}

function modelOptions(selection, provider) {
  if (provider === 'ollama' && selection.ollamaModels?.length) {
    return selection.ollamaModels.map((item) => ({
      model: item.name,
      authProfile: '',
      readinessHint: selection.ollamaStatus || 'unknown',
    }))
  }

  return selection.availableConfiguredTargets.filter((target) => target.provider === provider)
}

export function ChatHeader({
  session,
  selection,
  onSelectionChange,
  onRefresh,
  isRefreshing,
}) {
  const providers = uniqueProviders(selection)
  const currentProvider = selection.currentProvider || providers[0] || ''
  const models = modelOptions(selection, currentProvider)
  const currentModel = models.some((item) => item.model === selection.currentModel)
    ? selection.currentModel
    : models[0]?.model || selection.currentModel || ''

  return (
    <section className="chat-header-bar panel">
      <div className="chat-header-copy">
        <p className="eyebrow">Jarvis · Chat</p>
        <strong>{session?.title || 'New chat'}</strong>
      </div>

      <div className="chat-header-controls">
        <select
          className="header-select"
          value={currentProvider}
          onChange={(e) => {
            const nextProvider = e.target.value
            const first = modelOptions(selection, nextProvider)[0]
            if (!first) return
            onSelectionChange({
              provider: nextProvider,
              model: first.model,
              authProfile: first.authProfile || '',
            })
          }}
        >
          {providers.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>

        <select
          className="header-select header-model-select"
          value={currentModel}
          onChange={(e) => {
            const nextModel = e.target.value
            const candidate = models.find((item) => item.model === nextModel)
            onSelectionChange({
              provider: currentProvider,
              model: nextModel,
              authProfile: candidate?.authProfile || '',
            })
          }}
        >
          {models.map((item) => (
            <option key={item.model} value={item.model}>{item.model}</option>
          ))}
        </select>

        <button className="icon-btn header-refresh-btn" onClick={onRefresh} title="Refresh runtime truth">
          <RefreshCw size={15} className={isRefreshing ? 'spin' : ''} />
        </button>

        <div className="header-status-pill">
          <span>{selection.currentProvider || 'unknown'}</span>
          <strong>{selection.currentModel || 'unknown'}</strong>
        </div>
      </div>
    </section>
  )
}
