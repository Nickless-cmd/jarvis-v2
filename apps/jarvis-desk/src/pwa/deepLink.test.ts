/**
 * Deep-link fra web-push (6/11-2026).
 *
 * Beviset der betyder noget: service workeren sender `/?session=<id>`, og
 * APPEN SKAL LAESE DEN. Foer fixet fandtes `?session=` kun i service-worker.ts
 * — nul laesere i appen — saa et klik paa en notifikation fokuserede vinduet,
 * navigerede til en URL appen ignorerede, og notifikationen lukkede sig.
 *
 * Derfor to slags tests her:
 *  1. funktionerne selv (parse + ryd),
 *  2. at App.tsx FAKTISK kalder dem — en test paa funktionen alene ville vaere
 *     groen selv om koblingen blev fjernet. Det er praecis den fejlform
 *     `?session=` selv var et eksempel paa.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { sessionFraUrl, urlUdenSession } from './deepLink'

describe('sessionFraUrl', () => {
  it('finder session-id i query', () => {
    expect(sessionFraUrl('?session=chat-abc123')).toBe('chat-abc123')
  })

  it('returnerer null naar parameteren mangler', () => {
    expect(sessionFraUrl('')).toBeNull()
    expect(sessionFraUrl('?foo=bar')).toBeNull()
  })

  it('afviser tom og blank vaerdi', () => {
    expect(sessionFraUrl('?session=')).toBeNull()
    expect(sessionFraUrl('?session=%20%20')).toBeNull()
  })

  it('dekoder URL-kodede ider', () => {
    expect(sessionFraUrl('?session=chat%2Dabc')).toBe('chat-abc')
  })
})

describe('urlUdenSession', () => {
  it('fjerner session og bevarer andre parametre', () => {
    expect(urlUdenSession('?session=chat-abc&foo=bar', '/', '')).toBe('/?foo=bar')
  })

  it('efterlader en ren sti naar session var den eneste', () => {
    expect(urlUdenSession('?session=chat-abc', '/', '')).toBe('/')
  })

  it('bevarer hash', () => {
    expect(urlUdenSession('?session=chat-abc', '/', '#zone')).toBe('/#zone')
  })
})

describe('koblingen til App.tsx', () => {
  // Laes kilden som tekst: vi vil bevise at APPEN kalder funktionerne, ikke at
  // de kan kaldes. Stien er relativ til denne testfil (src/pwa/).
  const appKilde = readFileSync(resolve(__dirname, '..', 'App.tsx'), 'utf8')

  it('App.tsx importerer deep-link-hjaelperne', () => {
    expect(appKilde).toContain('sessionFraUrl')
    expect(appKilde).toContain('urlUdenSession')
  })

  it('App.tsx kalder select() med sessionen fra URL', () => {
    // Uden dette kald ville parameteren blive laest og smidt vaek.
    expect(appKilde).toMatch(/select\(fraPush\)/)
  })

  it('App.tsx rydder parameteren efter brug', () => {
    // Ellers springer et refresh til den samme samtale igen.
    expect(appKilde).toContain('replaceState')
  })
})
