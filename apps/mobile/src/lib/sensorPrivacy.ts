import { precisionLabel, type LocationPrecision } from './location'

export type SensorRisk = 'low' | 'medium' | 'high'

export interface SensorPrivacyState {
  cameraShutterSound: boolean
  locationPrecision: LocationPrecision
  batterySaver: boolean
  bubbleEnabled: boolean
  microphoneAvailable: boolean
}

export interface SensorPrivacyRow {
  id: 'camera' | 'microphone' | 'location' | 'background' | 'bubble' | 'battery'
  label: string
  value: string
  risk: SensorRisk
}

export function sensorRowsFromState(state: SensorPrivacyState): SensorPrivacyRow[] {
  const background = state.locationPrecision === 'background'
  return [
    {
      id: 'camera',
      label: 'Kamera',
      value: state.cameraShutterSound ? 'Shutter lyd slået til' : 'Shutter stille',
      risk: state.cameraShutterSound ? 'low' : 'medium'
    },
    {
      id: 'microphone',
      label: 'Mikrofon',
      value: state.microphoneAvailable ? 'Klar til voice' : 'Ikke godkendt',
      risk: state.microphoneAvailable ? 'medium' : 'low'
    },
    {
      id: 'location',
      label: 'Lokation',
      value: precisionLabel(state.locationPrecision),
      risk: state.locationPrecision === 'off' || state.locationPrecision === 'city' ? 'low' : 'high'
    },
    {
      id: 'background',
      label: 'Baggrund',
      value: background ? 'Lokation i baggrund' : 'Kun når appen er aktiv',
      risk: background ? 'high' : 'low'
    },
    {
      id: 'bubble',
      label: 'Boble',
      value: state.bubbleEnabled ? 'Kan ligge oven på andre apps' : 'Slået fra',
      risk: state.bubbleEnabled ? 'medium' : 'low'
    },
    {
      id: 'battery',
      label: 'Batteri',
      value: state.batterySaver ? 'Optimeret' : 'Maksimal livefølelse',
      risk: state.batterySaver ? 'low' : 'medium'
    }
  ]
}
