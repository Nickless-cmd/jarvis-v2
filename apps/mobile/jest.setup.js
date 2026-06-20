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

jest.mock('expo-intent-launcher', () => ({
  __esModule: true,
  startActivityAsync: jest.fn(async () => undefined),
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
