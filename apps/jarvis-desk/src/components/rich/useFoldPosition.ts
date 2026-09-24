import { useLayoutEffect, useRef, type RefObject } from 'react'

/** Hold den klikkede foldelinje på samme skærmposition, også når transcriptet
 * er forankret til bunden. Indholdet kommer dermed frem UNDER linjen. */
export function useFoldPosition(ref: RefObject<HTMLElement | null>, aaben: boolean): () => void {
  const foer = useRef<{ scroller: HTMLElement; top: number } | null>(null)

  const husk = () => {
    const element = ref.current
    const scroller = element?.closest<HTMLElement>('.transcript')
    if (element && scroller) foer.current = { scroller, top: element.getBoundingClientRect().top }
  }

  useLayoutEffect(() => {
    const gemt = foer.current
    const element = ref.current
    if (!gemt || !element) return
    foer.current = null
    gemt.scroller.scrollTop += element.getBoundingClientRect().top - gemt.top
  }, [aaben, ref])

  return husk
}
