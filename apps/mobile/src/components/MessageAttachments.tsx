import { Image, StyleSheet, Text, View } from 'react-native'
import { FileText } from 'lucide-react-native'
import { useAuth } from '../state/AuthContext'
import type { PersistedBlock } from '../lib/persistedBlocks'
import { tokens } from '../theme/tokens'

/**
 * Vedhæftninger på en brugerbesked — tegnet OVER boblen, ikke inde i den.
 *
 * Sådan gør ChatGPT: billedet står som en stor afrundet flade, og teksten
 * ligger som sin egen boble nedenunder. Det er den rigtige vej rundt, fordi
 * billedet ofte ER beskeden, og en boble omkring et billede bare tilføjer en
 * ramme ingen har brug for.
 *
 * Blokkene bærer kun en REFERENCE. Billedet hentes over det user-scopede
 * /attachments/image/{id} med brugerens eget token — ingen billeddata har
 * nogensinde ligget i beskeden, og adgangskontrollen bliver derfor spurgt
 * hver gang.
 */
export function MessageAttachments({ items }: { items: PersistedBlock[] }) {
  const { config } = useAuth()
  if (!items.length) return null

  return (
    <View style={styles.wrap}>
      {items.map((b) => {
        const id = String(b.attachment_id ?? '')
        if (b.type === 'image' && config?.apiBaseUrl) {
          const uri = new URL(
            `/attachments/image/${encodeURIComponent(id)}`,
            config.apiBaseUrl
          ).toString()
          return (
            <Image
              key={id}
              testID={`attachment-image-${id}`}
              source={{
                uri,
                headers: config.authToken
                  ? { Authorization: `Bearer ${config.authToken}` }
                  : undefined
              }}
              style={styles.image}
              resizeMode="cover"
            />
          )
        }
        return (
          <View key={id} testID={`attachment-file-${id}`} style={styles.file}>
            <FileText size={18} color={tokens.color.fg2} strokeWidth={1.8} />
            <Text style={styles.fileName} numberOfLines={1}>
              {b.filename || 'fil'}
            </Text>
            {typeof b.size_bytes === 'number' && b.size_bytes > 0 ? (
              <Text style={styles.fileSize}>{formatSize(b.size_bytes)}</Text>
            ) : null}
          </View>
        )
      })}
    </View>
  )
}

/** 1536 → «1,5 kB». Dansk komma, og aldrig flere cifre end nogen orker at læse. */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['kB', 'MB', 'GB']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i++
  }
  const rounded = Math.round(value * 10) / 10
  const text = Number.isInteger(rounded) ? String(rounded) : String(rounded).replace('.', ',')
  return `${text} ${units[i]}`
}

const styles = StyleSheet.create({
  wrap: {
    alignSelf: 'flex-end',
    alignItems: 'flex-end',
    gap: tokens.spacing.sm,
    marginHorizontal: tokens.spacing.lg,
    marginBottom: tokens.spacing.xs,
    maxWidth: '82%'
  },
  image: {
    width: 240,
    height: 240,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg2
  },
  file: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    backgroundColor: tokens.color.bg2,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
    maxWidth: '100%'
  },
  fileName: { color: tokens.color.fg1, fontSize: 14, flexShrink: 1 },
  fileSize: { color: tokens.color.fg3, fontSize: 12 }
})
