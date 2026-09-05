import { render } from '@testing-library/react-native'
import { WorkReviewCard } from './WorkReviewCard'
import type { WorkReview } from '../lib/workReviewApi'

const review: WorkReview = {
  id: 'task-1',
  kind: 'dispatch',
  title: 'Ret mobil review',
  status: 'running',
  branch: 'claude/task-1',
  updatedAt: '2026-09-05T10:00:00Z',
  summary: '2 files changed, 38 insertions(+), 12 deletions(-)',
  filesChanged: 2,
  additions: 38,
  deletions: 12
}

it('viser review-status, branch og diff-tal', async () => {
  const s = await render(<WorkReviewCard review={review} now={new Date('2026-09-05T10:05:00Z')} />)

  expect(s.getByText('Review')).toBeTruthy()
  expect(s.getByText('Ret mobil review')).toBeTruthy()
  expect(s.getByText('claude/task-1')).toBeTruthy()
  expect(s.getByText('+38')).toBeTruthy()
  expect(s.getByText('-12')).toBeTruthy()
})

it('viser ærlig tom diff når der ikke er ændringer', async () => {
  const s = await render(<WorkReviewCard review={{ ...review, summary: '', filesChanged: 0, additions: 0, deletions: 0 }} />)
  expect(s.getByText('Ingen diff endnu.')).toBeTruthy()
})
