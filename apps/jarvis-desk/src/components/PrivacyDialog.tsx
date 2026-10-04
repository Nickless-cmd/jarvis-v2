import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import { DataPrivacyPanel } from './DataPrivacyPanel'
import '../styles/privacy-dialog.css'

export function PrivacyDialog({ config, onClose }: { config?: ApiConfig; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const dialog = ref.current
    if (dialog?.showModal) dialog.showModal()
    else dialog?.setAttribute('open', '')
    return () => { dialog?.close?.(); previous?.focus() }
  }, [])

  return <dialog ref={ref} className="privacy-dialog" aria-label="Privatliv og cookies"
    onCancel={(event) => { event.preventDefault(); onClose() }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <div className="privacy-dialog-content">
      <button type="button" className="privacy-dialog-close" aria-label="Luk privatliv og cookies" onClick={onClose}>
        <X size={18} />
      </button>
      <DataPrivacyPanel config={config} />
    </div>
  </dialog>
}
