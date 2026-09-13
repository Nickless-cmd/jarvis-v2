import { filnavnMedEndelse, gemTilGalleriet } from './gemBillede'

jest.mock('expo-media-library/legacy', () => ({
  requestPermissionsAsync: jest.fn(async () => ({ granted: true })),
  saveToLibraryAsync: jest.fn(async () => undefined),
}))

const galleri = () => require('expo-media-library/legacy') as {
  requestPermissionsAsync: jest.Mock
  saveToLibraryAsync: jest.Mock
}

beforeEach(() => {
  jest.clearAllMocks()
  galleri().requestPermissionsAsync.mockResolvedValue({ granted: true })
  galleri().saveToLibraryAsync.mockResolvedValue(undefined)
})

describe('filnavnMedEndelse', () => {
  it('beholder endelsen der er der i forvejen', () => {
    expect(filnavnMedEndelse('lanterne.png')).toBe('lanterne.png')
    expect(filnavnMedEndelse('foto.JPEG')).toBe('foto.JPEG')
  })

  it('laaner endelsen fra mime-typen naar navnet ingen har', () => {
    // Praecis det tilfaelde der gik galt: AuthImage navngiver sin kopi efter
    // attachment-id'et, og en fil uden endelse bliver AFVIST af galleriet.
    expect(filnavnMedEndelse('1e48fd12747b4c3f', 'image/jpeg')).toBe('1e48fd12747b4c3f.jpg') // pragma: allowlist secret — et opdigtet attachment-id, ikke en hemmelighed
    expect(filnavnMedEndelse('billede', 'image/webp')).toBe('billede.webp')
  })

  it('falder tilbage til .png og et navn naar intet er oplyst', () => {
    expect(filnavnMedEndelse()).toBe('billede.png')
    expect(filnavnMedEndelse('', '')).toBe('billede.png')
  })

  it('renser navnet saa stien ikke kan stikke af', () => {
    expect(filnavnMedEndelse('../../etc/passwd')).toBe('.._.._etc_passwd.png')
  })

  it('ignorerer en charset-parameter i mime-typen', () => {
    expect(filnavnMedEndelse('x', 'image/png; charset=binary')).toBe('x.png')
  })
})

describe('gemTilGalleriet', () => {
  it('gemmer og melder «gemt»', async () => {
    expect(await gemTilGalleriet('file:///cache/img-lanterne.png')).toBe('gemt')
    expect(galleri().saveToLibraryAsync).toHaveBeenCalledWith('file:///cache/img-lanterne.png')
  })

  it('melder «afvist» naar brugeren sagde nej OG filen ikke kunne skrives', async () => {
    galleri().requestPermissionsAsync.mockResolvedValue({ granted: false })
    galleri().saveToLibraryAsync.mockRejectedValue(new Error('nope'))
    expect(await gemTilGalleriet('file:///cache/img.png')).toBe('afvist')
  })

  it('melder «gemt» ogsaa naar tilladelsen blev afvist — hvis filen FAKTISK blev gemt', async () => {
    // Android 13+ skriver appens EGNE billeder gennem MediaStore uden
    // tilladelse. Et nej til dialogen er derfor ikke et nej til at gemme, og
    // udfaldet skal komme fra handlingen — ikke fra tilladelsen.
    galleri().requestPermissionsAsync.mockResolvedValue({ granted: false })
    expect(await gemTilGalleriet('file:///cache/img.png')).toBe('gemt')
  })

  it('melder «fejlet» naar tilladelsen VAR der og filen alligevel ikke kunne skrives', async () => {
    galleri().saveToLibraryAsync.mockRejectedValue(new Error('disk full'))
    expect(await gemTilGalleriet('file:///cache/img.png')).toBe('fejlet')
  })

  it('melder «fejlet» naar der ikke er nogen fil at gemme', async () => {
    expect(await gemTilGalleriet('')).toBe('fejlet')
    expect(galleri().saveToLibraryAsync).not.toHaveBeenCalled()
  })
})
