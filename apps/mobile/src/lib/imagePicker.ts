import * as DocumentPicker from 'expo-document-picker'
import * as ImagePicker from 'expo-image-picker'
import type { CapturedPhoto } from '../screens/CameraCapture'

/**
 * Vælg billeder fra galleriet — FLERE ad gangen.
 *
 * Den gamle version returnerede ét billede og gjorde det umuligt at sende to
 * skærmbilleder i samme besked; man skulle sende to beskeder, og så mistede
 * Jarvis sammenhængen mellem dem.
 */
export async function pickImagesFromGallery(): Promise<CapturedPhoto[]> {
  try {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (!perm.granted) return []
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      quality: 0.9
    })
    if (res.canceled || !res.assets?.length) return []
    return res.assets.map((a) => ({
      uri: a.uri,
      name: a.fileName || `billede-${a.uri.split('/').pop() || 'foto.jpg'}`,
      mime: a.mimeType || 'image/jpeg'
    }))
  } catch {
    return []
  }
}

/**
 * Vælg vilkårlige FILER — dokumenter, arkiver, hvad som helst.
 *
 * Serveren tager imod alle typer: den scanner dem med ClamAV, og arkiver pakkes
 * ud i en sandkasse ved modtagelsen. Klienten skal derfor ikke selv sortere i
 * hvad der «må» sendes — det ville bare være en gætteleg oven på en kontrol der
 * allerede findes, og som er langt bedre informeret.
 */
export async function pickDocuments(): Promise<CapturedPhoto[]> {
  try {
    const res = await DocumentPicker.getDocumentAsync({
      type: '*/*',
      multiple: true,
      copyToCacheDirectory: true
    })
    if (res.canceled || !res.assets?.length) return []
    return res.assets.map((a) => ({
      uri: a.uri,
      name: a.name || 'fil',
      mime: a.mimeType || 'application/octet-stream'
    }))
  } catch {
    return []
  }
}

/** Bagudkompatibel enkeltvalgs-variant (bruges hvor kun ét billede giver mening). */
export async function pickImageFromGallery(): Promise<CapturedPhoto | null> {
  const many = await pickImagesFromGallery()
  return many[0] ?? null
}
