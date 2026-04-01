import { Loader2, CheckCircle2 } from 'lucide-react'

export function WorkingIndicator({ steps }) {
  if (!steps || steps.length === 0) return null

  const doneSteps = steps.filter(s => s.status === 'done')
  const currentStep = steps.find(s => s.status === 'running')

  if (!currentStep && doneSteps.length === 0) return null

  return (
    <div className="working-indicator">
      <div className="working-indicator-spinner">
        <Loader2 size={13} />
      </div>
      <div className="working-indicator-steps">
        {doneSteps.map((step, i) => (
          <div key={i} className="working-step done">
            <CheckCircle2 size={9} />
            <span className="mono">{step.action}</span>
          </div>
        ))}
        {currentStep && (
          <>
            <div className="working-step current">
              <span className="mono">{currentStep.action}</span>
            </div>
            <div className="working-step-detail mono">{currentStep.detail}</div>
          </>
        )}
      </div>
    </div>
  )
}
