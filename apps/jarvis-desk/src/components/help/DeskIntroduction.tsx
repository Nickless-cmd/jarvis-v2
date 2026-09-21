import { useEffect, useRef } from 'react'
import { MessageCircle, Code2, LayoutGrid, X } from 'lucide-react'
import { emitZone } from '../../lib/coworkZone'

export const INTRO_EVENT = 'jarvis:open-introduction'
export type IntroSurface = 'chat' | 'code' | 'cowork'

export function IntroductionButton() {
  return <button type="button" onClick={() => window.dispatchEvent(new Event(INTRO_EVENT))}>Vis introduktion til Desk</button>
}

/** Native modal provides focus containment, Escape and background inertness. */
export function DeskIntroduction({ onClose, onNavigate }: {
  onClose: () => void
  onNavigate?: (surface: IntroSurface) => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    const node = dialog.current
    if (node?.showModal) node.showModal()
    else node?.setAttribute('open', '')
    return () => { node?.close?.(); before?.focus() }
  }, [])
  const choose = (surface: IntroSurface) => {
    if (surface === 'cowork') emitZone('mc')
    onClose(); onNavigate?.(surface)
  }
  return (
    <dialog ref={dialog} className="desk-introduction" aria-labelledby="desk-intro-title" onCancel={event => { event.preventDefault(); onClose() }} onKeyDown={event => {
      if (event.key !== 'Tab') return
      const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'))
      const first = buttons[0], last = buttons[buttons.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }}>
      <button type="button" className="intro-close" onClick={onClose} aria-label="Luk introduktion"><X size={18} /></button>
      <p className="intro-eyebrow">Kom godt i gang</p>
      <h2 id="desk-intro-title">Velkommen til Desk</h2>
      <p>Vælg den flade, der passer til det, du vil gøre. Du kan skifte undervejs i menuen øverst til venstre.</p>
      <div className="intro-options">
        <section><MessageCircle aria-hidden="true" size={23} /><h3>Chat</h3>
          <p>Stil spørgsmål, del en fil eller få hjælp til at undersøge og formulere noget.</p>
          <p className="intro-example">Prøv: “Hjælp mig med at planlægge min uge.”</p>
          <button type="button" onClick={() => choose('chat')}>Åbn Chat</button>
        </section>
        <section><Code2 aria-hidden="true" size={23} /><h3>Code</h3>
          <p>Arbejd med et projekt. Vælg arbejdsmappe, få hjælp til kode, og gennemgå ændringerne.</p>
          <p className="intro-example">Prøv: “Forklar, hvordan dette projekt er bygget op.”</p>
          <button type="button" onClick={() => choose('code')}>Åbn Code</button>
        </section>
        <section><LayoutGrid aria-hidden="true" size={23} /><h3>Arbejde</h3>
          <p>Følg opgaver og godkendelser, forbind værktøjer, og tilpas Desk under Indstillinger.</p>
          <p className="intro-example">Start med oversigten, eller vælg Generelt i sidemenuen.</p>
          <button type="button" onClick={() => choose('cowork')}>Åbn Arbejde</button>
        </section>
      </div>
      <p className="intro-help">Puls-mærket bevæger sig, når Jarvis arbejder. Brug stopknappen ved skrivefeltet for at afbryde et svar. Tilladelser afhænger af samtalens valgte niveau.</p>
      <footer><span>Du finder introduktionen igen under Arbejde → Om og hjælp.</span><button type="button" onClick={onClose}>Kom i gang</button></footer>
    </dialog>
  )
}
