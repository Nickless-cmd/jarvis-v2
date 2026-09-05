import { StyleSheet, Text, View } from 'react-native'
import { GitPullRequestDraft } from 'lucide-react-native'
import { formatRelativeTime } from '../lib/relativeDate'
import type { WorkReview } from '../lib/workReviewApi'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function WorkReviewCard({ review, now }: { review: WorkReview; now?: Date }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <View style={styles.card} accessibilityRole="summary">
      <View style={styles.head}>
        <GitPullRequestDraft size={15} color={tokens.color.fg2} strokeWidth={1.8} />
        <Text style={styles.tag}>Review</Text>
        <View style={styles.spacer} />
        {review.updatedAt ? <Text style={styles.age}>{formatRelativeTime(review.updatedAt, now ?? new Date())}</Text> : null}
      </View>
      <Text style={styles.title} numberOfLines={2}>{review.title}</Text>
      {review.branch ? <Text style={styles.branch} numberOfLines={1}>{review.branch}</Text> : null}
      {review.summary ? (
        <View style={styles.stats}>
          <Text style={styles.stat}>{review.filesChanged} filer</Text>
          <Text style={[styles.stat, styles.add]}>+{review.additions}</Text>
          <Text style={[styles.stat, styles.del]}>-{review.deletions}</Text>
        </View>
      ) : (
        <Text style={styles.empty}>Ingen diff endnu.</Text>
      )}
      <Text style={styles.status}>{review.status}</Text>
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.color.line,
    padding: tokens.spacing.md,
    gap: 7
  },
  head: { flexDirection: 'row', alignItems: 'center', gap: tokens.spacing.sm },
  tag: { color: tokens.color.fg2, fontSize: 12, fontWeight: '700' },
  spacer: { flex: 1 },
  age: { color: tokens.color.fg3, fontSize: 11 },
  title: { color: tokens.color.fg1, fontSize: 14, fontWeight: '700', lineHeight: 20 },
  branch: { color: tokens.color.fg3, fontSize: 12 },
  stats: { flexDirection: 'row', gap: tokens.spacing.sm, alignItems: 'center' },
  stat: { color: tokens.color.fg2, fontSize: 12, fontWeight: '700' },
  add: { color: tokens.color.accentText },
  del: { color: tokens.color.warn },
  empty: { color: tokens.color.fg3, fontSize: 12 },
  status: { color: tokens.color.fg3, fontSize: 11 }
})
