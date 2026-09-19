import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useRaekkeFn, useSenesteFn } from './stabileHandlinger'

describe('stabile handlinger til memoiserede rækker', () => {
  it('useSenesteFn: samme identitet over renders, men kalder den SENESTE udgave', () => {
    const a = vi.fn(); const b = vi.fn()
    const { result, rerender } = renderHook(({ fn }) => useSenesteFn(fn), { initialProps: { fn: a } })
    const foerste = result.current
    rerender({ fn: b })
    expect(result.current).toBe(foerste)
    result.current('x')
    expect(b).toHaveBeenCalledWith('x')
    expect(a).not.toHaveBeenCalled()
  })

  it('useRaekkeFn: én stabil funktion pr. id, der kalder den seneste fn(id)', () => {
    const a = vi.fn(); const b = vi.fn()
    const { result, rerender } = renderHook(({ fn }) => useRaekkeFn(fn), { initialProps: { fn: a } })
    const m1 = result.current('m1')
    expect(result.current('m1')).toBe(m1)
    expect(result.current('m2')).not.toBe(m1)
    rerender({ fn: b })
    expect(result.current('m1')).toBe(m1)
    m1()
    expect(b).toHaveBeenCalledWith('m1')
  })
})

describe('transcriptets MessageRow får ingen nye props ved hver render', () => {
  // Profileret 19/9-2026: inline-funktioner og et nyt config-objekt pr. række
  // brød MessageRow's memo, så HELE samtalen (260 beskeder) blev renderet om
  // ved hver stream-opdatering.
  it.each(['ChatView', 'CodeView'])('%s', async (vis) => {
    const fs = await import('node:fs'); const path = await import('node:path'); const ts = await import('typescript')
    const kilde = fs.readFileSync(path.resolve(__dirname, `../views/${vis}.tsx`), 'utf8')
    const sf = ts.createSourceFile(`${vis}.tsx`, kilde, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    const syndere: string[] = []
    const erNy = (e: import('typescript').Expression): boolean => {
      if (ts.isArrowFunction(e) || ts.isFunctionExpression(e) || ts.isObjectLiteralExpression(e) || ts.isArrayLiteralExpression(e)) return true
      if (ts.isConditionalExpression(e)) return erNy(e.whenTrue) || erNy(e.whenFalse)
      if (ts.isParenthesizedExpression(e)) return erNy(e.expression)
      return false
    }
    const besoeg = (n: import('typescript').Node, iMap: boolean) => {
      // Kun rækkerne i .map() — den ENE levende besked må gerne have nye props.
      const map = ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === 'map'
      if (iMap && (ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n)) && n.tagName.getText(sf) === 'MessageRow') {
        for (const a of n.attributes.properties) {
          if (!ts.isJsxAttribute(a) || !a.initializer || !ts.isJsxExpression(a.initializer) || !a.initializer.expression) continue
          if (erNy(a.initializer.expression)) syndere.push(a.name.getText(sf))
        }
      }
      ts.forEachChild(n, (c) => besoeg(c, iMap || map))
    }
    besoeg(sf, false)
    expect(syndere).toEqual([])
  })
})
