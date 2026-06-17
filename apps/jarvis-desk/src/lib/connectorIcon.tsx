import {
  Github, Command, Globe, Volume2, Sparkles, Mail, Calendar, Blocks,
  HardDrive, FileText, Table, Presentation, Code, Cpu, Brain, File,
  Music, MessageSquare, BookOpen, StickyNote,
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
  'hard-drive': HardDrive,
  'file-text': FileText,
  table: Table,
  presentation: Presentation,
  code: Code,
  cpu: Cpu,
  brain: Brain,
  file: File,
  music: Music,
  'message-square': MessageSquare,
  'book-open': BookOpen,
  'sticky-note': StickyNote,
}

export function connectorIcon(name: string): LucideIcon {
  return ICONS[name] ?? Blocks
}

/** Brand-farve pr. connector-id → giver ikon-badgen et genkendeligt brand-look.
 *  Tom streng = ingen brand (brug standard-baggrund + fg-farve). */
const BRAND: Record<string, string> = {
  gmail: '#EA4335',
  'google-calendar': '#4285F4',
  'google-drive': '#1FA463',
  'google-docs': '#4285F4',
  'google-sheets': '#0F9D58',
  'google-slides': '#F4B400',
  github: '#6e7681',
  slack: '#4A154B',
  spotify: '#1DB954',
  notion: '#2f2f2f',
  huggingface: '#FFB000',
  'openai-models': '#10A37F',
}

export function connectorBrandColor(id: string): string {
  return BRAND[id] ?? ''
}
