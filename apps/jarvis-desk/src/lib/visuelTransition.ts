import { fjederTilCss, type FjederParametre } from './fjeder'

type TransitionBase = {
  /** Flag på den ene transition; der oprettes ikke et ekstra tekstlag. */
  crossfade: boolean
}

export type VarighedTransition = TransitionBase & {
  model: 'duration'
  durationMs: number
  curve?: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out'
  spring?: never
}

export type FjederTransition = TransitionBase & FjederParametre & {
  model: 'spring'
  durationMs?: never
  curve?: never
}

/** En transition vælger enten tid/kurve eller fjederparametre — aldrig begge. */
export type VisuelTransition = VarighedTransition | FjederTransition

export interface CssTransition {
  crossfade: boolean
  durationMs: number
  easing: string
}

export function visuelTransitionTilCss(transition: VisuelTransition): CssTransition {
  if (transition.model === 'duration') {
    if (!Number.isFinite(transition.durationMs) || transition.durationMs <= 0) {
      throw new Error(`Animation duration must be greater than 0. Provided: ${transition.durationMs}`)
    }
    return {
      crossfade: transition.crossfade,
      durationMs: transition.durationMs,
      easing: transition.curve ?? 'ease-in-out',
    }
  }
  return { crossfade: transition.crossfade, ...fjederTilCss(transition) }
}
