import { registerRootComponent } from 'expo'
import App from './src/App'

// Standard Expo-entry: registrér rod-komponenten fra src/App (appen ligger i src/,
// så Expo's default expo/AppEntry.js's '../../App' fejlede i release-bundlen).
registerRootComponent(App)
