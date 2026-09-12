import { useState } from 'react'
import { Image, Pressable, StyleSheet, Text, View } from 'react-native'
import { planlaegPreview } from '../lib/filePreview'
import { aabnUdgivetFil, blokUrl } from '../lib/aabnFil'
import { FileText } from 'lucide-react-native'
import { useAuth } from '../state/AuthContext'
import type { PersistedBlock } from '../lib/persistedBlocks'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'
import { FullscreenImagePreview } from './FullscreenImagePreview'

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
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const [preview, setPreview] = useState<{ uri: string; title: string; headers?: Record<string, string> } | null>(null)
  if (!items.length) return null

  return (
    <View style={styles.wrap}>
      {items.map((b) => {
        // En UDGIVET fil har ingen attachment_id — den baerer sin egen url.
        // Noeglen maa derfor falde tilbage paa navnet, ellers ville alle
        // udgivne filer i samme tur dele noeglen '' og React tegne én.
        const id = String(b.attachment_id ?? '') || String(b.filename ?? '')
        if (b.type === 'image' && config?.apiBaseUrl) {
          const uri = blokUrl(b, config.apiBaseUrl)
          const headers = config.authToken
            ? { Authorization: `Bearer ${config.authToken}` }
            : undefined
          return (
            <Pressable
              key={id}
              testID={`attachment-open-${id}`}
              accessibilityRole="imagebutton"
              accessibilityLabel={`Åbn ${b.filename || 'billede'}`}
              onPress={() => setPreview({ uri, title: b.filename || 'Billede', headers })}
            >
              <Image
                testID={`attachment-image-${id}`}
                source={{ uri, headers }}
                style={styles.image}
                resizeMode="cover"
              />
            </Pressable>
          )
        }
        // Codex lavede billeder. Resten fik et generisk ikon uden at sige HVAD
        // det var — en PDF og en zip så ens ud. Planen siger nu typen, og om
        // filen kan vises inde i appen eller hører til i systemets fremviser.
        const plan = planlaegPreview(String(b.filename || ''), String((b as { mime_type?: string }).mime_type || ''), Number(b.size_bytes || 0))
        // TRYKBAR. Kortet viste foer navn og type og kunne ikke aabnes — en
        // fil man kan se og ikke naa. `/files` kraever token, saa et browser-
        // tryk ville give 401; appen henter den selv og viser telefonens kopi.
        const filUrl = config?.apiBaseUrl ? blokUrl(b, config.apiBaseUrl) : ''
        return (
          <Pressable
            key={id}
            testID={`attachment-file-${id}`}
            accessibilityRole={filUrl ? 'button' : undefined}
            accessibilityLabel={filUrl ? `Åbn ${b.filename || 'fil'}` : undefined}
            disabled={!filUrl}
            onPress={() => {
              if (!filUrl || !config) return
              void aabnUdgivetFil(
                config, filUrl, String(b.filename || 'fil'),
                String((b as { mime_type?: string }).mime_type || ''),
              ).catch(() => undefined)
            }}
            style={styles.file}
          >
            <FileText size={18} color={tokens.color.fg2} strokeWidth={1.8} />
            <View style={styles.fileMeta}>
              <Text style={styles.fileName} numberOfLines={1}>
                {b.filename || 'fil'}
              </Text>
              <Text testID={`attachment-kind-${id}`} style={styles.fileKind}>
                {plan.etiket}
                {plan.slags === 'system' ? ' · åbnes i telefonen' : ''}
              </Text>
            </View>
            {typeof b.size_bytes === 'number' && b.size_bytes > 0 ? (
              <Text style={styles.fileSize}>{formatSize(b.size_bytes)}</Text>
            ) : null}
          </Pressable>
        )
      })}
      {preview ? (
        <FullscreenImagePreview
          visible
          uri={preview.uri}
          title={preview.title}
          headers={preview.headers}
          onClose={() => setPreview(null)}
        />
      ) : null}
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

const makestyles = (tokens: Theme) => StyleSheet.create({
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
  fileMeta: { flex: 1, minWidth: 0 },
  fileKind: { color: tokens.color.fg3, fontSize: 11 },
  fileName: { color: tokens.color.fg1, fontSize: 14, flexShrink: 1 },
  fileSize: { color: tokens.color.fg3, fontSize: 12 }
})
