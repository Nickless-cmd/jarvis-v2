import type { Config } from 'tailwindcss'

// ClawX-inspired dark palette. Token names match what we'll use in the
// renderer so designers can theme the whole shell from one file.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Background tiers
        bg0: '#0d1117',   // app background
        bg1: '#161b22',   // panels
        bg2: '#1c2128',   // raised cards
        // Borders
        line: '#21262d',
        line2: '#30363d',
        // Text
        fg: '#e6edf3',
        fg2: '#9da7b3',
        fg3: '#6e7681',
        // Accents (Jarvis green + ClawX blue + warning amber)
        accent: '#5ab8a0',
        accent2: '#58a6ff',
        warn: '#d29922',
        danger: '#f85149',
        ok: '#3fb950',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.25s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config
