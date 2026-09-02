/** Find første bruger-række fra `current` i `direction` (+1/-1). Null hvis ingen.
 *  Retnings-agnostisk så MessageList kan mappe "ældre/nyere" til den rigtige vej
 *  i en inverted FlatList. */
export function nextUserRow(
  isUserFlags: boolean[],
  current: number,
  direction: 1 | -1,
): number | null {
  let i = current + direction
  // Klamp et current uden for grænserne ind i rækkevidde, så vi stadig scanner
  // (fx current=99, direction=-1 → start ved sidste index).
  if (i >= isUserFlags.length) i = isUserFlags.length - 1
  if (i < 0) i = 0
  while (i >= 0 && i < isUserFlags.length) {
    if (isUserFlags[i]) return i
    i += direction
  }
  return null
}
