/** Pure geometry for the desktop figure. All coordinates are Electron DIP. */
export type BobleSide = 'over' | 'under'

export interface WorkArea { x: number; y: number; width: number; height: number }

export function bobleSide(figureY: number, workArea: WorkArea): BobleSide {
  return figureY < workArea.y + workArea.height / 2 ? 'under' : 'over'
}

/** Keep the figure at the same screen Y while the window grows or the bubble flips. */
export function vindueTop(
  figureY: number,
  windowHeight: number,
  contentHeight: number,
  figureCenterInContent: number,
  side: BobleSide,
): number {
  const figureOffset = figureCenterInContent + (side === 'over' ? windowHeight - contentHeight : 0)
  return Math.round(figureY - figureOffset)
}
