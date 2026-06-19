import { AccessibilityInfo } from 'react-native'
import { renderHook, waitFor } from '@testing-library/react-native'
import { useReducedMotion } from './useReducedMotion'

describe('useReducedMotion', () => {
  it('returnerer true når systemet har reduceret bevægelse', async () => {
    jest.spyOn(AccessibilityInfo, 'isReduceMotionEnabled').mockResolvedValue(true)
    jest.spyOn(AccessibilityInfo, 'addEventListener').mockReturnValue({ remove: jest.fn() } as never)
    const { result } = await renderHook(() => useReducedMotion())
    await waitFor(() => expect(result.current).toBe(true))
  })
})
