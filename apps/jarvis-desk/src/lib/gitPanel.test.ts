import { describe, expect, it } from 'vitest'
import {
  commitKlar, diffModeForSektion, filNavn, grupperFiler, kanPushe, parseDiff, statusEtiket,
  trackingTekst, type GitFil,
} from './gitPanel'

const fil = (o: Partial<GitFil> & { path: string }): GitFil => ({
  old_path: '', index: ' ', worktree: ' ', untracked: false,
  staged: false, unstaged: false, conflict: false, ...o,
})

describe('grupperFiler', () => {
  it('en fil staged og ændret igen står i BEGGE sektioner', () => {
    const g = grupperFiler([fil({ path: 'a.ts', index: 'M', worktree: 'M', staged: true, unstaged: true })])
    expect(g.staged.map((f) => f.path)).toEqual(['a.ts'])
    expect(g.aendret.map((f) => f.path)).toEqual(['a.ts'])
  })

  it('ukendte filer og konflikter havner ikke i staged/ændret', () => {
    const g = grupperFiler([
      fil({ path: 'ny.ts', index: '?', worktree: '?', untracked: true, unstaged: true }),
      fil({ path: 'k.ts', index: 'U', worktree: 'U', conflict: true, staged: true, unstaged: true }),
    ])
    expect(g.nye.map((f) => f.path)).toEqual(['ny.ts'])
    expect(g.konflikt.map((f) => f.path)).toEqual(['k.ts'])
    expect(g.staged).toEqual([])
    expect(g.aendret).toEqual([])
  })
})

describe('statusEtiket', () => {
  it('læser index-kolonnen for staged og working-tree-kolonnen for ændret', () => {
    const f = fil({ path: 'x', index: 'A', worktree: 'D', staged: true, unstaged: true })
    expect(statusEtiket(f, 'staged')).toBe('Tilføjet')
    expect(statusEtiket(f, 'aendret')).toBe('Slettet')
  })
  it('har danske etiketter for ny og konflikt', () => {
    const f = fil({ path: 'x' })
    expect(statusEtiket(f, 'nye')).toBe('Ny')
    expect(statusEtiket(f, 'konflikt')).toBe('Konflikt')
  })
  it('falder tilbage til «Ændret» for en ukendt kode', () => {
    expect(statusEtiket(fil({ path: 'x', worktree: 'Z' }), 'aendret')).toBe('Ændret')
  })
})

describe('diffModeForSektion', () => {
  it('staged diffes mod HEAD-indekset, resten mod working tree', () => {
    expect(diffModeForSektion('staged')).toBe('staged')
    expect(diffModeForSektion('aendret')).toBe('unstaged')
    expect(diffModeForSektion('nye')).toBe('unstaged')
  })
})

describe('parseDiff', () => {
  const DIFF = [
    'diff --git a/f.txt b/f.txt',
    'index 111..222 100644',
    '--- a/f.txt',
    '+++ b/f.txt',
    '@@ -1,2 +1,3 @@',
    ' uændret',
    '-gammel',
    '+ny',
    '+endnu en',
    '\\ No newline at end of file',
    '',
  ].join('\n')

  it('typer linjerne og tæller kun rigtige tilføjelser/fjernelser', () => {
    const r = parseDiff(DIFF)
    expect(r.tilfoejet).toBe(2)
    expect(r.fjernet).toBe(1)
    const typer = r.linjer.map((l) => l.type)
    expect(typer.slice(0, 4)).toEqual(['meta', 'meta', 'meta', 'meta'])
    expect(typer[4]).toBe('hunk')
    expect(typer[typer.length - 1]).toBe('meta') // «\ No newline»
  })

  it('--- og +++ i filhovedet tælles ikke som ændringer', () => {
    const r = parseDiff('--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n')
    expect([r.tilfoejet, r.fjernet]).toEqual([1, 1])
  })

  it('en fjernet linje der selv starter med «--» tælles som fjernet i en hunk', () => {
    const r = parseDiff('@@ -1 +0,0 @@\n--- kommentar\n')
    expect(r.fjernet).toBe(1)
  })

  it('tom diff giver ingen linjer', () => {
    expect(parseDiff('')).toEqual({ linjer: [], tilfoejet: 0, fjernet: 0 })
  })

  it('en ny hunk-gruppe i næste fil nulstiller hunk-tilstanden', () => {
    const r = parseDiff('@@ -1 +1 @@\n-a\n+b\ndiff --git a/y b/y\n--- a/y\n+++ b/y\n')
    expect([r.tilfoejet, r.fjernet]).toEqual([1, 1])
  })
})

describe('commitKlar', () => {
  const med = (staged: number, filer: GitFil[] = []) => ({ staged_count: staged, files: filer })

  it('afviser uden status, uden staged, uden besked og ved konflikt — med dansk grund', () => {
    expect(commitKlar(null, 'x').klar).toBe(false)
    expect(commitKlar(med(0), 'x').grund).toBe('Stage mindst én fil først')
    expect(commitKlar(med(1), '   ').grund).toBe('Skriv en commit-besked')
    const k = commitKlar(med(1, [fil({ path: 'k', conflict: true })]), 'x')
    expect(k).toEqual({ klar: false, grund: 'Løs konflikterne først' })
  })

  it('godkender staged + besked', () => {
    expect(commitKlar(med(2), 'feat: noget')).toEqual({ klar: true, grund: '' })
  })
})

describe('trackingTekst / kanPushe', () => {
  const s = (o: Partial<{ upstream: string; ahead: number; behind: number; detached: boolean; branch: string }>) =>
    ({ upstream: 'origin/main', ahead: 0, behind: 0, detached: false, branch: 'main', ...o })

  it('beskriver foran/bagud/ajour/ingen upstream/afkoblet', () => {
    expect(trackingTekst(s({ ahead: 2, behind: 1 }))).toBe('2 foran, 1 bagud origin/main')
    expect(trackingTekst(s({}))).toBe('Ajour med origin/main')
    expect(trackingTekst(s({ upstream: '' }))).toMatch(/Ingen upstream/)
    expect(trackingTekst(s({ detached: true }))).toBe('Afkoblet HEAD')
  })

  it('kan kun pushe når der er noget at pushe — eller upstream mangler', () => {
    expect(kanPushe(s({}))).toBe(false)
    expect(kanPushe(s({ ahead: 1 }))).toBe(true)
    expect(kanPushe(s({ upstream: '' }))).toBe(true)
    expect(kanPushe(s({ detached: true, ahead: 3 }))).toBe(false)
  })
})

describe('filNavn', () => {
  it('deler sti i navn og mappe', () => {
    expect(filNavn('a/b/c.ts')).toEqual({ navn: 'c.ts', mappe: 'a/b' })
    expect(filNavn('c.ts')).toEqual({ navn: 'c.ts', mappe: '' })
  })
})
