// Globale mocks for native push-moduler, så komponenter der importerer dem
// (ChatScreen, App) kan loades i jest uden native bro.
jest.mock('@notifee/react-native', () => ({
  __esModule: true,
  default: {
    createChannel: jest.fn(async () => 'jarvis'),
    displayNotification: jest.fn(async () => undefined),
    onForegroundEvent: jest.fn(() => () => undefined),
    getInitialNotification: jest.fn(async () => null),
  },
  AndroidImportance: { HIGH: 4 },
  AndroidStyle: { BIGTEXT: 1 },
  EventType: { PRESS: 1, DISMISSED: 0, ACTION_PRESS: 2 },
}))

jest.mock('@react-native-firebase/messaging', () => ({
  __esModule: true,
  default: () => ({
    requestPermission: jest.fn(async () => 1),
    getToken: jest.fn(async () => 'mock-token'),
    onTokenRefresh: jest.fn(() => () => undefined),
    onMessage: jest.fn(() => () => undefined),
    setBackgroundMessageHandler: jest.fn(),
  }),
}))

jest.mock('@react-native-community/netinfo', () => ({
  __esModule: true,
  default: {
    addEventListener: jest.fn(() => () => undefined),
    fetch: jest.fn(async () => ({ type: 'wifi' })),
  },
}))

jest.mock('expo-application', () => ({
  __esModule: true,
  nativeBuildVersion: '28',
}))

jest.mock('expo-file-system/legacy', () => ({
  __esModule: true,
  documentDirectory: 'file:///doc/',
  createDownloadResumable: jest.fn(() => ({
    downloadAsync: jest.fn(async () => ({ uri: 'file:///doc/app.apk' })),
  })),
  getContentUriAsync: jest.fn(async () => 'content://app.apk'),
}))

// expo-file-system (ny API). Lyd-uploadet går NATIVT gennem File.upload —
// ikke gennem fetch — fordi Expos fetch ikke kan læse en fil-uri i FormData.
jest.mock('expo-file-system', () => ({
  __esModule: true,
  UploadType: { BINARY_CONTENT: 0, MULTIPART: 1 },
  File: jest.fn().mockImplementation((uri) => ({
    uri,
    upload: jest.fn(async () => ({ status: 200, body: '{"status":"ok","text":"hej"}', headers: {} })),
  })),
}))

jest.mock('expo-intent-launcher', () => ({
  __esModule: true,
  startActivityAsync: jest.fn(async () => undefined),
}))

jest.mock('expo-image-picker', () => ({
  __esModule: true,
  requestMediaLibraryPermissionsAsync: jest.fn(async () => ({ granted: true })),
  launchImageLibraryAsync: jest.fn(async () => ({ canceled: true, assets: [] })),
}))

jest.mock('expo-location', () => ({
  __esModule: true,
  Accuracy: { Balanced: 3 },
  requestForegroundPermissionsAsync: jest.fn(async () => ({ status: 'granted' })),
  getCurrentPositionAsync: jest.fn(async () => ({ coords: { latitude: 55.86, longitude: 10.39 } })),
}))

jest.mock('expo-audio', () => ({
  __esModule: true,
  RecordingPresets: { HIGH_QUALITY: {} },
  // getStatus() er dér niveauet FAKTISK kommer fra. Status-tilbagekaldet på
  // useAudioRecorder bærer ikke metering — det fyrer først når optagelsen
  // slutter — og hænderfri var bygget på det, så den stoppede aldrig selv.
  useAudioRecorder: jest.fn(() => ({
    uri: null,
    prepareToRecordAsync: jest.fn(async () => undefined),
    record: jest.fn(),
    stop: jest.fn(async () => undefined),
    getStatus: jest.fn(() => ({ isRecording: true, metering: -160, url: null })),
  })),
  // Afspilleren skal MELDE at lyden er færdig. Uden det kan en kø af replikker
  // aldrig komme videre til den næste, og en test af strømmende oplæsning ville
  // se ud som en fejl i køen frem for i mocken.
  createAudioPlayer: jest.fn(() => {
    const listeners = []
    return {
      addListener: jest.fn((_evt, cb) => { listeners.push(cb) }),
      pause: jest.fn(),
      play: jest.fn(() => {
        setTimeout(() => listeners.forEach((cb) => cb({ didJustFinish: true })), 0)
      }),
      remove: jest.fn(),
    }
  }),
  requestRecordingPermissionsAsync: jest.fn(async () => ({ granted: true })),
  setAudioModeAsync: jest.fn(async () => undefined),
}))

jest.mock('react-native-svg', () => {
  const React = require('react')
  const mk = (name) => (props) => React.createElement(name, props, props.children)
  return {
    __esModule: true,
    default: mk('Svg'),
    Svg: mk('Svg'),
    Circle: mk('Circle'),
    Rect: mk('Rect'),
    Defs: mk('Defs'),
    RadialGradient: mk('RadialGradient'),
    LinearGradient: mk('LinearGradient'),
    Stop: mk('Stop'),
  }
})

// lucide-react-native udgiver ESM (.mjs) som Jest ikke kan parse — uden denne
// mock fejler ENHVER testfil der transitivt importerer et ikon med
// «Unexpected token 'export'». Tests har ikke brug for de rigtige SVG-baner;
// de har brug for at komponenttræet kan renderes. Appen bruger uændret de
// ægte ikoner via Metro.
jest.mock('lucide-react-native', () => {
  const React = require('react')
  const { View } = require('react-native')
  return new Proxy(
    {},
    {
      get: (_target, name) => {
        if (name === '__esModule') return true
        const Icon = (props) => React.createElement(View, { ...props, testID: `icon-${String(name)}` })
        Icon.displayName = String(name)
        return Icon
      }
    }
  )
})

