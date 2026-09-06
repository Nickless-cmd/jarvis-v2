import * as SecureStore from 'expo-secure-store'

const CAMERA_PREFS_KEY = 'jarvis.mobile.cameraPrefs'

export type CameraFacing = 'front' | 'back'
export type CameraFlash = 'off' | 'on' | 'auto'

export interface CameraPrefs {
  facing: CameraFacing
  flash: CameraFlash
  shutterSound: boolean
}

const DEFAULT_PREFS: CameraPrefs = {
  facing: 'back',
  flash: 'off',
  shutterSound: true
}

function parsePrefs(raw: string | null): CameraPrefs {
  if (!raw) return DEFAULT_PREFS
  try {
    const data = JSON.parse(raw) as Partial<CameraPrefs>
    return {
      facing: data.facing === 'front' ? 'front' : 'back',
      flash: data.flash === 'on' || data.flash === 'auto' ? data.flash : 'off',
      shutterSound: typeof data.shutterSound === 'boolean' ? data.shutterSound : true
    }
  } catch {
    return DEFAULT_PREFS
  }
}

export async function loadCameraPrefs(): Promise<CameraPrefs> {
  try {
    return parsePrefs(await SecureStore.getItemAsync(CAMERA_PREFS_KEY))
  } catch {
    return DEFAULT_PREFS
  }
}

export async function saveCameraPrefs(prefs: CameraPrefs): Promise<void> {
  try {
    await SecureStore.setItemAsync(CAMERA_PREFS_KEY, JSON.stringify(prefs))
  } catch {
    /* best-effort */
  }
}
