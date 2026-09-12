import { render } from '@testing-library/react-native'
import { CodeTitle } from './CodeTitle'
import type { GitStatus } from '../lib/apiClient'

const g = (o: Partial<GitStatus> = {}): GitStatus => ({
  branch: 'main', dirty: 0, added: 0, removed: 0, isGit: true,
  repo: 'jarvis-v2', host: 'CheifOne', link: 'ok', ...o,
})

it('viser hvilket repo paa hvilken maskine', async () => {
  const screen = await render(<CodeTitle titel="Diagnose WLED" git={g()} />)
  expect(screen.getByText('Diagnose WLED')).toBeTruthy()
  expect(screen.getByText('jarvis-v2')).toBeTruthy()
  expect(screen.getByText('CheifOne')).toBeTruthy()
})

it('forbundet er GROEN', async () => {
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'ok' })} />)
  expect(screen.getByTestId('link-ok')).toBeTruthy()
  const { StyleSheet } = require('react-native')
  expect(StyleSheet.flatten(screen.getByTestId('link-ok').props.style).backgroundColor)
    .toBe('#4CAF50')
})

it('GENFORBINDER er gul, ikke roed', async () => {
  // En desk der genstarter staar registreret et oejeblik endnu. Roedt hver
  // gang nogen genstartede sin app ville laere én at se bort fra farven.
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'genforbinder' })} />)
  const { StyleSheet } = require('react-native')
  expect(StyleSheet.flatten(screen.getByTestId('link-genforbinder').props.style).backgroundColor)
    .toBe('#FFB347')
})

it('ingen forbindelse er ROED', async () => {
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'nede' })} />)
  const { StyleSheet } = require('react-native')
  expect(StyleSheet.flatten(screen.getByTestId('link-nede').props.style).backgroundColor)
    .toBe('#ff8080')
})

it('de tre farver er FORSKELLIGE — ellers siger prikken ingenting', async () => {
  const { StyleSheet } = require('react-native')
  const farve = async (link: GitStatus['link']) => {
    const s = await render(<CodeTitle titel="x" git={g({ link })} />)
    return StyleSheet.flatten(s.getByTestId(`link-${link}`).props.style).backgroundColor
  }
  // ÉN render pr. kald ville normalt braekke oprydningen; her hentes farven
  // og traeet forlades med det samme, og RNTL rydder mellem tests - saa det
  // er ét trae ad gangen paa naer i selve loekken. Derfor laeses vaerdien FOER
  // naeste render.
  const a = await farve('ok')
  const b = await farve('genforbinder')
  const c = await farve('nede')
  expect(new Set([a, b, c]).size).toBe(3)
})

it('prikken siger ogsaa sin tilstand med ord', async () => {
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'genforbinder' })} />)
  expect(screen.getByLabelText('Genforbinder')).toBeTruthy()
})

it('UDEN git-status er der ingen kontekstlinje', async () => {
  const screen = await render(<CodeTitle titel="x" git={null} />)
  expect(screen.queryByTestId('link-ok')).toBeNull()
  expect(screen.getByText('x')).toBeTruthy()
})
