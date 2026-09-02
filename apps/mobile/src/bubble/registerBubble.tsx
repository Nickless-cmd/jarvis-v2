import { AppRegistry } from 'react-native'
import { BubbleChatRoot } from './BubbleChat'

// Registrér boble-roden ved siden af 'main'. BubbleActivity renderer denne.
AppRegistry.registerComponent('JarvisBubble', () => BubbleChatRoot)
