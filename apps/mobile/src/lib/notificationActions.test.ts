import { notificationActionsFor, STOP_RUN_ACTION_ID, OPEN_RUN_ACTION_ID, APPROVE_ACTION_ID, DENY_ACTION_ID } from './notificationActions'

it('adds open and stop actions to active run notifications', () => {
  expect(notificationActionsFor({ kind: 'run_in_progress', run_id: 'r1' }).map((a) => a.pressAction.id))
    .toEqual([OPEN_RUN_ACTION_ID, STOP_RUN_ACTION_ID])
})

it('adds approve and deny actions to approval notifications', () => {
  expect(notificationActionsFor({ kind: 'approval_requested', request_id: 'ap1' }).map((a) => a.pressAction.id))
    .toEqual([APPROVE_ACTION_ID, DENY_ACTION_ID])
})

it('keeps reply actions away from explicit decision notifications', () => {
  expect(notificationActionsFor({ kind: 'approval_requested' }).some((a) => a.input)).toBe(false)
})
