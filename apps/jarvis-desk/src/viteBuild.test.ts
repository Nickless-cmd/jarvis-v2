// @vitest-environment node
import { describe, expect, it } from 'vitest'
import viteConfig from '../vite.config'

async function configFor(mode: string) {
  return typeof viteConfig === 'function'
    ? await viteConfig({ command: 'build', mode, isSsrBuild: false, isPreview: false })
    : viteConfig
}

describe('renderer build targets', () => {
  it('puts web assets at the site root in a separate output directory', async () => {
    const config = await configFor('web')
    expect(config.base).toBe('/')
    expect(config.build?.outDir).toBe('dist-web')
    expect(config.define?.__WEB_BUILD__).toBe('true')
  })

  it('keeps relative assets and the existing Desk output', async () => {
    const config = await configFor('production')
    expect(config.base).toBe('./')
    expect(config.build?.outDir).toBe('dist')
    expect(config.define?.__WEB_BUILD__).toBe('false')
  })
})
