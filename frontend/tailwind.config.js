/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: {
          DEFAULT: '#161923',
          50:  '#f0f2f7',
          100: '#e3e6ed',
          200: '#cbd0dc',
          300: '#abb2c3',
          400: '#868da2',
          500: '#5f667a',
          600: '#353a49',
          700: '#272b38',
          800: '#1e2230',
          900: '#1a1d29',
          950: '#161923',
        },
        accent: {
          DEFAULT: '#6b86b3',
          hover:   '#5a7aa6',
          glow:    'rgba(107,134,179,0.15)',
          muted:   'rgba(107,134,179,0.08)',
        },
        severity: {
          critical: '#c14953',
          high:     '#b8753a',
          medium:   '#b59441',
          low:      '#5f8c6e',
          info:     '#5a87a8',
        },
        red: {
          300: '#e08b93',
          400: '#d46570',
          500: '#c14953',
          600: '#a63a44',
          700: '#8a2f38',
        },
        orange: {
          300: '#d9a478',
          400: '#d18b4d',
          500: '#b8753a',
          600: '#9a6028',
          700: '#7d4d1c',
        },
        yellow: {
          300: '#d9bd7a',
          400: '#ccab54',
          500: '#b59441',
          600: '#9a7d2d',
          700: '#7f6620',
        },
        green: {
          300: '#92bca0',
          400: '#78a68a',
          500: '#5f8c6e',
          600: '#4d7359',
          700: '#3d5b46',
        },
        cyan: {
          300: '#9bbcd2',
          400: '#7aa3bf',
          500: '#5a87a8',
          600: '#476d8a',
          700: '#375670',
        },
        blue: {
          400: '#7a95c2',
          500: '#6b86b3',
          600: '#5a7aa6',
          700: '#4a6894',
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
        'fade-in':    'fadeIn 200ms ease-out',
        'slide-up':   'slideUp 250ms ease-out',
        'flash-row':  'flashRow 2s ease-out',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.4' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        flashRow: {
          '0%':   { backgroundColor: 'rgba(181,148,65,0.15)' },
          '100%': { backgroundColor: 'transparent' },
        },
      },
    },
  },
  plugins: [],
};
