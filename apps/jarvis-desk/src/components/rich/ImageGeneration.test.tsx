import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { ImageAnalysisProgress, erEgenUpload } from './ImageGeneration'

/**
 * MÅLT 20/10-2026: 27 af 38 `analyze_image`-kald (71 %) pegede på
 * `~/.jarvis-v2/uploads/chat-<session>/…` — Bjørns EGET upload, som allerede
 * står i tråden i hans boble ovenover. Rammen viste derfor det samme billede
 * to gange: først uploadet, så igen som 148px-poster med en scanner henover.
 *
 * Bjørn: «billede analyse behøver ikk en animation.. det ligger allerede i
 * rundelinjens beskrivelse». Beslutningen er en BETINGELSE, ikke en variant:
 * eget upload → kun rundelinjen. Alt andet → rammen, fordi han ikke har set
 * det billede før og rammen dér ER ny information.
 */

const EGET_UPLOAD = '/home/bs/.jarvis-v2/uploads/chat-4651bd32cfd84355a3fd1b7fa4cc156b/foto.jpg'
const JARVIS_EGET = '/tmp/ss_mid.png'

describe('erEgenUpload', () => {
  it('genkender et upload fra Bjørns egen samtale', () => {
    expect(erEgenUpload(EGET_UPLOAD)).toBe(true)
  })

  it('genkender IKKE Jarvis eget skaermbillede i /tmp', () => {
    expect(erEgenUpload(JARVIS_EGET)).toBe(false)
  })

  it('taaler tom og manglende sti', () => {
    expect(erEgenUpload('')).toBe(false)
    expect(erEgenUpload(undefined)).toBe(false)
  })

  it('lader en sti der blot HEDDER uploads et andet sted vaere ukendt', () => {
    // Betingelsen skal maale paa mappen, ikke paa ordet: en fil der hedder
    // "uploads" i navnet er ikke et upload.
    expect(erEgenUpload('/tmp/uploads_noter.png')).toBe(false)
    expect(erEgenUpload('/var/vmail/uploads/x.jpg')).toBe(false)
  })
})

describe('ImageAnalysisProgress', () => {
  it('viser INGEN ramme naar billedet allerede staar i traaden', () => {
    const { container } = render(<ImageAnalysisProgress kilde="foto.jpg" sti={EGET_UPLOAD} />)
    // Rundelinjen skal stadig vaere der — den baerer beskrivelsen.
    expect(container.querySelector('.image-analysis-label')).not.toBeNull()
    // ...men rammen maa ikke gentage billedet.
    expect(container.querySelector('.image-analysis-ramme')).toBeNull()
  })

  it('BEHOLDER rammen naar billedet er et han ikke har set foer', () => {
    const { container } = render(<ImageAnalysisProgress kilde="ss_mid.png" sti={JARVIS_EGET} />)
    expect(container.querySelector('.image-analysis-label')).not.toBeNull()
    expect(container.querySelector('.image-analysis-ramme')).not.toBeNull()
  })

  it('viser rammen naar der ingen sti er — vi ved ikke bedre', () => {
    const { container } = render(<ImageAnalysisProgress kilde="" />)
    expect(container.querySelector('.image-analysis-ramme')).not.toBeNull()
  })
})
