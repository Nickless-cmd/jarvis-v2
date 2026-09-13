export type MobileRouteName =
  | 'settings'
  | 'senses'
  | 'artifacts'
  | 'images'
  | 'activity'

export interface MobileRoute {
  name: MobileRouteName
}

export function topRoute(stack: MobileRoute[]): MobileRoute | null {
  return stack[stack.length - 1] ?? null
}

export function pushRoute(stack: MobileRoute[], route: MobileRoute): MobileRoute[] {
  return [...stack.filter((item) => item.name !== route.name), route]
}

export function popRoute(stack: MobileRoute[]): MobileRoute[] {
  return stack.slice(0, Math.max(0, stack.length - 1))
}

export function replaceTopRoute(stack: MobileRoute[], route: MobileRoute): MobileRoute[] {
  if (!stack.length) return [route]
  return [...stack.slice(0, -1), route]
}
