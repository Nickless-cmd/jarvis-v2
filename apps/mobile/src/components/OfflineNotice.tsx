import { StyleSheet, Text, View } from 'react-native'
import type { Connectivity } from '../lib/useConnectivity'
import { useI18n } from '../i18n/I18nContext'
import { useStyles, type Theme } from '../theme/ThemeContext'

export function OfflineNotice({
  connectivity,
  reconnecting,
  outboxCount,
}: {
  connectivity: Connectivity
  reconnecting: boolean
  outboxCount: number
}) {
  const styles = useStyles(makeStyles)
  const { t } = useI18n()
  const visible = connectivity !== 'connected' || reconnecting || outboxCount > 0
  if (!visible) return null

  const kind = connectivity === 'offline'
    ? 'offline'
    : connectivity === 'reconnecting'
      ? 'reconnecting'
      : 'stream'
  const warn = kind !== 'stream'

  return (
    <View style={[styles.root, warn ? styles.warn : styles.info]}>
      <Text style={styles.title}>{t(`offline.title.${kind}`)}</Text>
      <Text style={styles.body}>{t(`offline.body.${kind}`)}</Text>
      {outboxCount > 0 ? (
        <Text style={styles.queue}>{t('offline.queue', { count: outboxCount })}</Text>
      ) : null}
    </View>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  root: {
    paddingVertical: 9,
    paddingHorizontal: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: tokens.color.glassLine,
    gap: 2,
  },
  warn: { backgroundColor: tokens.color.bg2 },
  info: { backgroundColor: tokens.color.bg2 },
  title: { color: tokens.color.fg1, fontSize: 13, fontWeight: '800' },
  body: { color: tokens.color.fg2, fontSize: 12.5, lineHeight: 17 },
  queue: { color: tokens.color.warn, fontSize: 12.5, fontWeight: '700', marginTop: 2 },
})
