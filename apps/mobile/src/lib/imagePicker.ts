import * as ImagePicker from 'expo-image-picker'
import type { CapturedPhoto } from '../screens/CameraCapture'

/**
 * Vælg et billede fra galleriet. Returnerer en CapturedPhoto (samme form som
 * in-app-kameraet) eller null hvis annulleret / nægtet tilladelse.
 */
export async function pickImageFromGallery(): Promise<CapturedPhoto | null> {
  try {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!perm.granted) return null
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.9
    })
    if (res.canceled || !res.assets || res.assets.length === 0) return null
    const a = res.assets[0]!
    const name = a.fileName || `billede-${a.uri.split('/').pop() || 'foto.jpg'}`
    return { uri: a.uri, name, mime: a.mimeType || 'image/jpeg' }
  } catch {
    return null
  }
}
