/** @type {import('tailwindcss').Config} */
export default {
  /** Toggle manually via `<html class="dark">` — see `applyThemeToDocument` */
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: {
          DEFAULT: 'var(--base-900)',
          50: 'var(--base-50)',
          100: 'var(--base-100)',
          200: 'var(--base-200)',
          300: 'var(--base-300)',
          400: 'var(--base-400)',
          500: 'var(--base-500)',
          600: 'var(--base-600)',
          700: 'var(--base-700)',
          800: 'var(--base-800)',
          900: 'var(--base-900)',
          950: 'var(--base-950)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          muted: 'var(--accent-muted)',
        },
        severity: {
          critical: '#ef4444',
          high: 'var(--base-400)',
          medium: 'var(--base-500)',
          low: 'var(--base-600)',
          info: 'var(--base-500)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['10px', '14px'],
      },
      borderRadius: {
        inherit: 'inherit',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'fade-in': 'fadeIn 200ms ease-out',
        'slide-up': 'slideUp 250ms ease-out',
        'flash-row': 'flashRow 1.4s ease-out',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        flashRow: {
          '0%': { backgroundColor: 'rgba(255,255,255,0.06)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
    },
  },
  plugins: [],
};
