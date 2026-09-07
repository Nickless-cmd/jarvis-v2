jest.mock('expo-location', () => ({
  getForegroundPermissionsAsync: jest.fn(async () => ({ status: 'granted' })),
  getCurrentPositionAsync: jest.fn(async () => ({
    coords: { latitude: 55.6, longitude: 12.5, accuracy: 8, altitude: 12, speed: 0 },
    timestamp: 1757000000000
  })),
  Accuracy: { High: 5, Balanced: 3, Low: 1 }
}))
jest.mock('expo-clipboard', () => ({
  getStringAsync: jest.fn(async () => 'på klippet'),
  setStringAsync: jest.fn(async () => undefined)
}))
jest.mock('expo-speech', () => ({ speak: jest.fn() }))
jest.mock('expo-file-system/legacy', () => ({
  documentDirectory: 'file:///data/app/',
  cacheDirectory: 'file:///cache/',
  writeAsStringAsync: jest.fn(async () => undefined),
  readAsStringAsync: jest.fn(async () => 'indhold'),
  readDirectoryAsync: jest.fn(async () => ['a.txt', 'b.png'])
}))
jest.mock('./bubbleModule', () => ({
  bubble: { isSupported: jest.fn(async () => true), showConversationBubble: jest.fn() }
}))

import * as Location from 'expo-location'
import * as Clipboard from 'expo-clipboard'
import * as Speech from 'expo-speech'
import * as FileSystem from 'expo-file-system/legacy'
import { Share } from 'react-native'
import {
  HANDLERE, KAN_UDFOERE, udfoerVaerktoej, samlSti, saetKamera, saetOptager
} from './telefonHandlere'

// Hele 'react-native' må IKKE mockes: jest-expo's preset bygger på det ægte
// modul, og en fuld mock vælter setup'et før en eneste test kører.
let delSpion: jest.SpyInstance
beforeEach(() => {
  delSpion = jest.spyOn(Share, 'share').mockResolvedValue({ action: 'sharedAction' } as never)
})
afterEach(() => { saetKamera(null); saetOptager(null); delSpion.mockRestore(); jest.clearAllMocks() })

describe('kontrakten med serveren', () => {
  it('melder præcis de værktøjer der findes', () => {
    // capabilities ER routingen: melder vi et navn vi ikke kan, sender
    // serveren kaldet hertil og får en fejl i stedet for til computeren.
    expect(KAN_UDFOERE.sort()).toEqual(Object.keys(HANDLERE).sort())
    expect(KAN_UDFOERE).toContain('phone_location')
  })

  it('et ukendt værktøj fejler tydeligt i stedet for at tie', async () => {
    await expect(udfoerVaerktoej('phone_ingenting', {})).rejects.toThrow('ukendt_vaerktoej')
  })
})

describe('stier holdes inde i appens område', () => {
  it('samler relativt mod appens mappe', () => {
    expect(samlSti('noter.txt')).toBe('file:///data/app/noter.txt')
    expect(samlSti('/noter.txt')).toBe('file:///data/app/noter.txt')
  })

  it('afviser .. — en model der gætter en sti skal ikke kunne ramme udenfor', () => {
    expect(() => samlSti('../../etc/passwd')).toThrow('sti_uden_for_appen')
    expect(() => samlSti('undermappe/../../ud')).toThrow('sti_uden_for_appen')
  })

  it('men et filnavn med to punktummer er ikke en udbrudsforsøg', () => {
    expect(samlSti('min..fil.txt')).toBe('file:///data/app/min..fil.txt')
  })
})

describe('position', () => {
  it('giver koordinater i et fladt svar', async () => {
    const r = await HANDLERE.phone_location!({ noejagtighed: 'high' }) as Record<string, unknown>
    expect(r.breddegrad).toBe(55.6)
    expect(r.tidspunkt).toBe('2025-09-04T15:33:20.000Z')
    expect((Location.getCurrentPositionAsync as jest.Mock).mock.calls[0][0].accuracy).toBe(5)
  })

  it('siger det ærligt når tilladelsen mangler', async () => {
    ;(Location.getForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ status: 'denied' })
    await expect(HANDLERE.phone_location!({})).rejects.toThrow('lokation_ikke_tilladt')
  })
})

describe('kamera', () => {
  it('fejler med grunden når appen ligger i baggrunden', async () => {
    // Android tillader ikke kamera fra baggrunden. Uden den her besked ville
    // Jarvis vente til serveren timer ud og ikke vide hvorfor.
    await expect(HANDLERE.phone_photo!({})).rejects.toThrow('kamera_ikke_klar')
    await expect(HANDLERE.phone_photo!({})).rejects.toThrow('forgrunden')
  })

  it('tager billedet når kameraet er monteret', async () => {
    saetKamera({ takePictureAsync: async () => ({ base64: 'AAAA' }) })
    const r = await HANDLERE.phone_photo!({}) as Record<string, unknown>
    expect(r.jpeg_base64).toBe('AAAA')
  })

  it('gemmer i appens område når der bedes om det', async () => {
    saetKamera({ takePictureAsync: async () => ({ base64: 'AAAA' }) })
    const r = await HANDLERE.phone_photo!({ gem_sti: 'billede.jpg' }) as Record<string, unknown>
    expect(r.gem_sti).toBe('file:///data/app/billede.jpg')
    expect(FileSystem.writeAsStringAsync).toHaveBeenCalledWith(
      'file:///data/app/billede.jpg', 'AAAA', { encoding: 'base64' }
    )
  })
})

describe('lyd', () => {
  it('fejler tydeligt uden optager', async () => {
    await expect(HANDLERE.phone_record_audio!({ sekunder: 3 })).rejects.toThrow('optager_ikke_klar')
  })

  it('optager i det antal sekunder der blev bedt om', async () => {
    const set: number[] = []
    saetOptager(async (s) => { set.push(s); return { base64: 'BBBB' } })
    const r = await HANDLERE.phone_record_audio!({ sekunder: 3 }) as Record<string, unknown>
    expect(set).toEqual([3])
    expect(r.lyd_base64).toBe('BBBB')
  })
})

describe('resten', () => {
  it('siger noget højt', async () => {
    await HANDLERE.phone_speak!({ tekst: 'hej Bjørn' })
    expect(Speech.speak).toHaveBeenCalledWith('hej Bjørn', { language: 'da-DK' })
  })

  it('nægter at sige ingenting', async () => {
    await expect(HANDLERE.phone_speak!({ tekst: '' })).rejects.toThrow('tekst_mangler')
  })

  it('læser og skriver udklipsholderen', async () => {
    expect(await HANDLERE.phone_clipboard_read!({})).toBe('på klippet')
    await HANDLERE.phone_clipboard_write!({ tekst: 'ny' })
    expect(Clipboard.setStringAsync).toHaveBeenCalledWith('ny')
  })

  it('lister filer', async () => {
    expect(await HANDLERE.phone_list_files!({})).toEqual(['a.txt', 'b.png'])
  })

  it('deling åbner arket og lover ikke at have sendt noget', async () => {
    const r = await HANDLERE.phone_share!({ tekst: 'se her' }) as Record<string, unknown>
    expect(delSpion).toHaveBeenCalledWith({ message: 'se her' })
    expect(r.ark_aabnet).toBe(true)
    expect(r).not.toHaveProperty('sendt')
  })
})
