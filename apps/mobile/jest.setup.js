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
  EventType: { PRESS: 1, DISMISSED: 0 },
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
