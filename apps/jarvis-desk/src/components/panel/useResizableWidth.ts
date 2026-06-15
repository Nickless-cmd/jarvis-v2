import { useEffect, useRef, useState, useCallback } from 'react'

/** Trækbar bredde med vedholdenhed (localStorage).
 *
 *  side='left'  → håndtaget sidder i elementets VENSTRE kant; bredden måles fra
 *                 elementets højre kant til musen (panel til højre der vokser
 *                 mod venstre — fx code-mode preview-panelet).
 *  side='right' → håndtaget sidder i elementets HØJRE kant; bredden måles fra
 *                 elementets venstre kant til musen (kolonne til venstre der
 *                 vokser mod højre — fx fil-træet).
 */
export function useResizableWidth(opts: {
  initial: number
  min: number
  max: number
  side: 'left' | 'right'
  storageKey?: string
}) {
  const { initial, min, max, side, storageKey } = opts
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState<number>(() => {
    if (storageKey) {
      try {
        const v = Number(localStorage.getItem(storageKey))
        if (v && v >= min && v <= max) return v
      } catch { /* localStorage utilgængelig */ }
    }
    return initial
  })
  const [dragging, setDragging] = useState(false)
  // Persistér KUN efter brugeren faktisk har trukket — ellers ville den initiale
  // default blive skrevet til localStorage ved mount og fryse fremtidige
  // default-ændringer (Bjørn så ikke nye proportioner før dette).
  const touched = useRef(false)

  useEffect(() => {
    if (storageKey && touched.current) {
      try { localStorage.setItem(storageKey, String(Math.round(width))) } catch { /* noop */ }
    }
  }, [width, storageKey])

  const startDrag = useCallback(() => { touched.current = true; setDragging(true) }, [])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: MouseEvent) => {
      const el = ref.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const raw = side === 'left' ? rect.right - e.clientX : e.clientX - rect.left
      setWidth(Math.max(min, Math.min(raw, max)))
    }
    const onUp = () => setDragging(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    // Forhindr tekst-markering mens man trækker.
    const prevSelect = document.body.style.userSelect
    document.body.style.userSelect = 'none'
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      document.body.style.userSelect = prevSelect
    }
  }, [dragging, side, min, max])

  return { ref, width, dragging, startDrag }
}
