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
        'float-soft': 'floatSoft 3s ease-in-out infinite',
        'gradient-shift': 'gradientShift 8s ease infinite',
        'scale-in': 'scaleIn 220ms cubic-bezier(0.34, 1.56, 0.64, 1)',
        'glow-ring': 'glowRing 2.4s ease-in-out infinite',
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
        floatSoft: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-3px)' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.92)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        glowRing: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(168,85,247,0.0)' },
          '50%': { boxShadow: '0 0 0 6px rgba(168,85,247,0.18)' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(0)' },
          '15%': { transform: 'rotate(-12deg)' },
          '30%': { transform: 'rotate(10deg)' },
          '45%': { transform: 'rotate(-8deg)' },
          '60%': { transform: 'rotate(6deg)' },
          '75%': { transform: 'rotate(-3deg)' },
        },
      },
    },
  },
  plugins: [],
};
