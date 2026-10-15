import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  afventendeFindes, findLinuxAppImage, markérAfventende, rydAfventende,
  rulTilbage, sikkerSwap, wireUpdater, type SwapFs,
} from './autoUpdate'

const MAAL = '/home/bs/Applications/J.A.R.V.I.S.AppImage'
const HENTET = '/home/bs/.cache/jarvis-desktop-updater/pending/J.A.R.V.I.S-0.6.238.AppImage'

function fakeUpdater() {
  const handlers: Record<string, (x: unknown) => void> = {}
  return {
    autoDownload: true,
    on: (ev: string, cb: (x: unknown) => void) => { handlers[ev] = cb },
    checkForUpdates: vi.fn(),
    downloadUpdate: vi.fn(),
    quitAndInstall: vi.fn(),
    _emit: (ev: string, x?: unknown) => handlers[ev]?.(x),
  }
}

function fakeFs(over: Partial<SwapFs> = {}): SwapFs {
  return {
    existsSync: () => true,
    copyFileSync: vi.fn(),
    chmodSync: vi.fn(),
    renameSync: vi.fn(),
    unlinkSync: vi.fn(),
    writeFileSync: vi.fn(),
    ...over,
  }
}

describe('sikkerSwap', () => {
  it('kopierer til temp, goer executable og renameR atomisk over maalet', () => {
    const fs = fakeFs()
    expect(sikkerSwap(HENTET, MAAL, fs)).toEqual({ ok: true, sti: MAAL })
    expect(fs.copyFileSync).toHaveBeenCalledWith(HENTET, `${MAAL}.ny`)
    expect(fs.chmodSync).toHaveBeenCalledWith(`${MAAL}.ny`, 0o755)
    // Renamen sker SIDST: indtil da er maalet uroert og findes stadig.
    expect(fs.renameSync).toHaveBeenCalledWith(`${MAAL}.ny`, MAAL)
    expect(fs.unlinkSync).not.toHaveBeenCalled()
  })

  it('roerer ikke maalet naar den hentede fil mangler', () => {
    const fs = fakeFs({ existsSync: () => false })
    expect(sikkerSwap(HENTET, MAAL, fs).ok).toBe(false)
    expect(fs.copyFileSync).not.toHaveBeenCalled()
    expect(fs.renameSync).not.toHaveBeenCalled()
  })

  it('efterlader maalet uroert naar renaming fejler — den gamle AppImage staar', () => {
    // Det er hele poenget: fejler swap'en, er der stadig en AppImage at starte.
    const fs = fakeFs({ renameSync: vi.fn(() => { throw new Error('EXDEV') }) })
    const r = sikkerSwap(HENTET, MAAL, fs)
    expect(r.ok).toBe(false)
    expect(fs.unlinkSync).toHaveBeenCalledWith(`${MAAL}.ny`)
  })

  it('afviser tom sti', () => {
    const fs = fakeFs()
    expect(sikkerSwap(null, MAAL, fs).ok).toBe(false)
    expect(sikkerSwap('', MAAL, fs).ok).toBe(false)
  })
})

describe('wireUpdater', () => {
  const foer = process.env.APPIMAGE
  beforeEach(() => { process.env.APPIMAGE = MAAL })
  afterEach(() => {
    if (foer === undefined) delete process.env.APPIMAGE
    else process.env.APPIMAGE = foer
  })

  it('update-available → send til renderer; download kun ved kald', () => {
    const up = fakeUpdater()
    const sent: unknown[] = []
    const api = wireUpdater(up as never, (ch, p) => sent.push([ch, p]), undefined, fakeFs())
    expect(up.autoDownload).toBe(false)
    up._emit('update-available', { version: '0.3.0' })
    expect(sent).toContainEqual(['update:available', { version: '0.3.0' }])
    expect(up.downloadUpdate).not.toHaveBeenCalled()
    api.download()
    expect(up.downloadUpdate).toHaveBeenCalled()
  })

  it('installNow laegger filen sikkert paa plads — og kalder ALDRIG quitAndInstall', async () => {
    // Hele fixet: electron-updaters egen install sletter den koerende AppImage
    // FOER den tjekker at der er en ny fil. Vi overtager swap'en i stedet.
    const up = fakeUpdater()
    const genstart = vi.fn()
    const fs = fakeFs()
    const api = wireUpdater(up as never, () => {}, genstart, fs)
    up._emit('update-downloaded', { version: '0.3.0', downloadedFile: HENTET })
    await api.installNow()
    expect(fs.renameSync).toHaveBeenCalledWith(`${MAAL}.ny`, MAAL)
    expect(genstart).toHaveBeenCalledWith(MAAL)
    expect(up.quitAndInstall).not.toHaveBeenCalled()
  })

  it('Installér nu tjekker, henter og installerer i raekkefoelge', async () => {
    const up = fakeUpdater()
    up.checkForUpdates.mockResolvedValue({ updateInfo: { version: '0.3.0' } })
    up.downloadUpdate.mockResolvedValue([HENTET])
    const genstart = vi.fn()
    const api = wireUpdater(up as never, () => {}, genstart, fakeFs())
    await api.downloadAndInstall()
    expect(up.checkForUpdates).toHaveBeenCalledOnce()
    expect(genstart).toHaveBeenCalledWith(MAAL)
    expect(up.quitAndInstall).not.toHaveBeenCalled()
  })

  it('genstarter ikke hvis hentningen fejler', async () => {
    const up = fakeUpdater()
    up.checkForUpdates.mockResolvedValue({ updateInfo: { version: '0.3.0' } })
    up.downloadUpdate.mockRejectedValue(new Error('Netværksfejl'))
    const genstart = vi.fn()
    const api = wireUpdater(up as never, () => {}, genstart, fakeFs())
    await expect(api.downloadAndInstall()).rejects.toThrow('Netværksfejl')
    expect(genstart).not.toHaveBeenCalled()
    expect(up.quitAndInstall).not.toHaveBeenCalled()
  })

  it('kaster og roerer intet naar swap\'en fejler — appen kan stadig starte', async () => {
    const up = fakeUpdater()
    const genstart = vi.fn()
    const fs = fakeFs({ renameSync: vi.fn(() => { throw new Error('EXDEV') }) })
    const api = wireUpdater(up as never, () => {}, genstart, fs)
    up._emit('update-downloaded', { version: '0.3.0', downloadedFile: HENTET })
    await expect(api.installNow()).rejects.toThrow(/blev ikke lagt på plads/)
    expect(genstart).not.toHaveBeenCalled()
  })

  it('naegter at installere naar APPIMAGE-stien mangler', async () => {
    delete process.env.APPIMAGE
    const up = fakeUpdater()
    const api = wireUpdater(up as never, () => {}, vi.fn(), fakeFs())
    await expect(api.installNow()).rejects.toThrow(/APPIMAGE/)
  })
})

describe('findLinuxAppImage', () => {
  it('genfinder den installerede AppImage når launcheren har tabt APPIMAGE', () => {
    const exists = vi.fn((path: string) => path === '/home/bjorn/Applications/J.A.R.V.I.S.AppImage')
    expect(findLinuxAppImage({ HOME: '/home/bjorn' }, exists)).toBe(
      '/home/bjorn/Applications/J.A.R.V.I.S.AppImage',
    )
  })

  it('bevarer launcherens egen absolutte APPIMAGE-sti', () => {
    const exists = vi.fn(() => true)
    expect(findLinuxAppImage({ APPIMAGE: '/opt/Jarvis.AppImage', HOME: '/home/bjorn' }, exists))
      .toBe('/opt/Jarvis.AppImage')
  })
})

// ── En defekt release maa ikke kunne laase appen ude af sin opdatering ───────
//
// Maalt 15/10-2026: 0.6.240 blev swappet ind, kastede i renderer ved HVER
// start, og opdaterings-UI'et laa selv i renderer — Bjørn sad fast i en doed
// app der pegede paa sin egen defekte version. Tre dele lukker hullet: en
// bevarede kopi af den koerende version, en atomisk tilbagerulning, og en
// markoer main kan skelne paa ved naeste start.

describe('sikkerSwap bevarer den koerende version', () => {
  it('kopierer maalet til .forrige FOER swap', () => {
    const fs = fakeFs()
    sikkerSwap(HENTET, MAAL, fs)
    expect(fs.copyFileSync).toHaveBeenCalledWith(MAAL, `${MAAL}.forrige`)
  })

  it('swapper alligevel hvis backup-kopien fejler — opdateringen blokeres ikke', () => {
    const fs = fakeFs({
      copyFileSync: vi.fn((fra: string, til: string) => {
        if (til.endsWith('.forrige')) throw new Error('disk fuld')
      }),
    })
    expect(sikkerSwap(HENTET, MAAL, fs).ok).toBe(true)
  })
})

describe('rulTilbage', () => {
  it('laegger .forrige atomisk tilbage over maalet', () => {
    const fs = fakeFs()
    expect(rulTilbage(MAAL, fs)).toEqual({ ok: true, sti: MAAL })
    expect(fs.copyFileSync).toHaveBeenCalledWith(`${MAAL}.forrige`, `${MAAL}.ny`)
    expect(fs.renameSync).toHaveBeenCalledWith(`${MAAL}.ny`, MAAL)
  })

  it('roerer intet naar der ingen forrige version er', () => {
    const fs = fakeFs({ existsSync: vi.fn(() => false) })
    expect(rulTilbage(MAAL, fs).ok).toBe(false)
    expect(fs.renameSync).not.toHaveBeenCalled()
  })

  it('efterlader maalet uroert naar tilbagerulningen fejler', () => {
    const fs = fakeFs({ renameSync: vi.fn(() => { throw new Error('EXDEV') }) })
    expect(rulTilbage(MAAL, fs).ok).toBe(false)
    expect(fs.unlinkSync).toHaveBeenCalledWith(`${MAAL}.ny`)
  })
})

describe('afventende-markoeren', () => {
  it('skrives ved swap og kan ryddes igen', () => {
    const fs = fakeFs()
    markérAfventende(MAAL, fs)
    expect(fs.writeFileSync).toHaveBeenCalledWith(`${MAAL}.afventer`, expect.any(String))
    rydAfventende(MAAL, fs)
    expect(fs.unlinkSync).toHaveBeenCalledWith(`${MAAL}.afventer`)
  })

  it('findes kun naar filen er der', () => {
    expect(afventendeFindes(MAAL, fakeFs({ existsSync: () => true }))).toBe(true)
    expect(afventendeFindes(MAAL, fakeFs({ existsSync: () => false }))).toBe(false)
  })

  it('installNow skriver markoeren — saa main kan opdage en crash ved naeste start', async () => {
    const foer = process.env.APPIMAGE
    process.env.APPIMAGE = MAAL
    try {
      const up = fakeUpdater()
      const fs = fakeFs()
      const api = wireUpdater(up as never, () => {}, vi.fn(), fs)
      up._emit('update-downloaded', { version: '0.3.0', downloadedFile: HENTET })
      await api.installNow()
      expect(fs.writeFileSync).toHaveBeenCalledWith(`${MAAL}.afventer`, expect.any(String))
    } finally {
      if (foer === undefined) delete process.env.APPIMAGE
      else process.env.APPIMAGE = foer
    }
  })
})
