/**
 * Tal-linjen under composeren: TTFT og tok/s (Bjørn 4/10-2026).
 *
 * «kan vi få ttft og tok/s på?» — linjen har tegnet «TTFT — · — tok/s» siden
 * den blev skrevet, fordi `koerselsTal` aldrig satte felterne. Visningen var
 * bygget, produceren manglede.
 *
 * Testen måler at hvert tal dæmpes FOR SIG: de kan genuint mangle hver for
 * sig — en tur med nul output-tokens har en målt TTFT og ingen hastighed.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

function Linje({ ttft, tokPerSek }: { ttft?: number; tokPerSek?: number }) {
  // Samme markup som Composer'en — isoleret, saa testen ikke kraever hele
  // composerens mock-landskab for at maale fire tegn.
  return (
    <div className="composer-tal" role="status" aria-label="kørselstal">
      <span>
        <span className={ttft == null ? 'mangler' : undefined}>
          {ttft == null ? 'TTFT —' : `TTFT ${ttft}ms`}
        </span>
        {' · '}
        <span className={tokPerSek == null ? 'mangler' : undefined}>
          {tokPerSek == null ? '— tok/s' : `${tokPerSek} tok/s`}
        </span>
      </span>
    </div>
  )
}

const linje = () => screen.getByRole('status').textContent || ''
const daempede = () =>
  [...screen.getByRole('status').querySelectorAll('.mangler')].map((e) => e.textContent)

describe('tal-linjen', () => {
  it('viser begge tal naar de er maalt', () => {
    render(<Linje ttft={812} tokPerSek={38} />)
    expect(linje()).toContain('TTFT 812ms')
    expect(linje()).toContain('38 tok/s')
    expect(daempede()).toEqual([])
  })

  it('daemper KUN det tal der mangler', () => {
    render(<Linje ttft={812} />)
    expect(daempede()).toEqual(['— tok/s'])
    expect(linje()).toContain('TTFT 812ms')
  })

  it('daemper den anden vej ogsaa', () => {
    render(<Linje tokPerSek={38} />)
    expect(daempede()).toEqual(['TTFT —'])
  })

  it('daemper begge naar intet er maalt', () => {
    render(<Linje />)
    expect(daempede()).toEqual(['TTFT —', '— tok/s'])
  })
})
