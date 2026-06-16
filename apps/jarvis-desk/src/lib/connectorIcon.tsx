import {
  Github, Command, Globe, Volume2, Sparkles, Mail, Calendar, Blocks,
  type LucideIcon,
} from 'lucide-react'

/** Map connector.icon-streng → lucide-ikon. Fallback: Blocks. */
const ICONS: Record<string, LucideIcon> = {
  github: Github,
  command: Command,
  globe: Globe,
  'volume-2': Volume2,
  sparkles: Sparkles,
  mail: Mail,
  calendar: Calendar,
}

export function connectorIcon(name: string): LucideIcon {
  return ICONS[name] ?? Blocks
}
