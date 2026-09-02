import * as FileSystem from 'expo-file-system/legacy'
import * as IntentLauncher from 'expo-intent-launcher'
import type { ApiConfig } from './types'
import type { UpdateManifest } from './appUpdate'

const GRANT_READ_URI_PERMISSION = 1

/**
 * Henter APK'en fra /mobile/download (med auth-header, progress via onProgress)
 * og fyrer systemets install-intent. Kaster ved fejl (UI viser fejl-toast).
 *
 * Bruger den klassiske file-system-API fra expo-file-system/legacy (i SDK 56
 * er den nye File/Directory-API default i roden — download-resumable + content-URI
 * lever i /legacy).
 */
export async function downloadAndInstall(
  config: ApiConfig,
  manifest: UpdateManifest,
  onProgress?: (fraction: number) => void
): Promise<void> {
  const url = new URL('/mobile/download', config.apiBaseUrl).toString()
  const dest = `${FileSystem.documentDirectory}${manifest.filename}`
  const task = FileSystem.createDownloadResumable(
    url,
    dest,
    { headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {} },
    (p) => {
      if (onProgress && p.totalBytesExpectedToWrite > 0) {
        onProgress(p.totalBytesWritten / p.totalBytesExpectedToWrite)
      }
    }
  )
  const result = await task.downloadAsync()
  if (!result?.uri) throw new Error('download gav ingen fil')
  const contentUri = await FileSystem.getContentUriAsync(result.uri)
  await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
    data: contentUri,
    flags: GRANT_READ_URI_PERMISSION,
    type: 'application/vnd.android.package-archive',
  })
}
