import { useEffect, useRef, type ReactNode } from 'react'

/** Shared page rhythm for the grouped Arbejde destinations. */
export function CategoryPage({
  title, description, children, wide = false, focusSection,
}: {
  title: string
  description: string
  children: ReactNode
  wide?: boolean
  focusSection?: string
}) {
  const root = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!focusSection) return
    const section = [...(root.current?.querySelectorAll<HTMLElement>('[data-section]') ?? [])]
      .find((element) => element.dataset.section === focusSection)
    section?.scrollIntoView?.({ block: 'start' })
  }, [focusSection])
  return (
    <div ref={root} className={`category-page${wide ? ' category-page--wide' : ''}`}>
      <header className="category-page-head">
        <h1>{title}</h1>
        <p>{description}</p>
      </header>
      <div className="category-page-content">{children}</div>
    </div>
  )
}

export function CategorySection({ id, title, description, children }: {
  id?: string
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="category-section" data-section={id}>
      <div className="category-section-head">
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      <div className="category-section-body">{children}</div>
    </section>
  )
}
