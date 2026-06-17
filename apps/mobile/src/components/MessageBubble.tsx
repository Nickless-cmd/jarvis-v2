import Markdown from 'react-native-markdown-display'
import { StyleSheet, Text, View } from 'react-native'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <View style={[styles.root, isUser ? styles.user : styles.assistant]}>
      {message.role === 'assistant' ? (
        <Markdown
          style={{
            body: styles.text,
            paragraph: styles.paragraph,
            text: styles.text
          }}
        >
          {message.content}
        </Markdown>
      ) : (
        <Text style={styles.text}>{message.content}</Text>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    marginHorizontal: tokens.spacing.md,
    marginVertical: tokens.spacing.xs,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md
  },
  assistant: {
    marginRight: 48,
    backgroundColor: tokens.color.bg1
  },
  user: {
    marginLeft: 48,
    backgroundColor: tokens.color.userBubble
  },
  text: {
    color: tokens.color.fg1,
    fontSize: 16,
    lineHeight: 23
  },
  paragraph: {
    marginTop: 0,
    marginBottom: 0
  }
})
