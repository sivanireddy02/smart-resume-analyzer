/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Core palette
        void:    '#0A0F1E',   // page background
        surface: '#111827',   // card background
        raised:  '#1A2236',   // elevated surfaces
        border:  '#1F2D45',   // subtle borders

        // Accent system
        cyan:    { DEFAULT: '#22D3EE', dim: '#0E7490' },
        emerald: { DEFAULT: '#10B981', dim: '#065F46', bright: '#34D399' },
        amber:   { DEFAULT: '#F59E0B', dim: '#78350F' },
        rose:    { DEFAULT: '#F43F5E', dim: '#881337' },

        // Typography
        ink:     '#F1F5F9',   // primary text
        muted:   '#64748B',   // secondary text
        ghost:   '#334155',   // placeholder text
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body:    ['"Inter"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'scan':        'scan 2s linear infinite',
        'fade-in':     'fadeIn 0.4s ease-out',
        'slide-up':    'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer':     'shimmer 1.8s linear infinite',
        'score-ring':  'scoreRing 1.2s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
      },
      keyframes: {
        scan: {
          '0%':   { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(400%)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(24px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        scoreRing: {
          from: { strokeDashoffset: '440' },
        },
      },
      backgroundImage: {
        'grid-pattern': `
          linear-gradient(rgba(34,211,238,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(34,211,238,0.03) 1px, transparent 1px)
        `,
        'shimmer-gradient': 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)',
      },
      backgroundSize: {
        'grid': '32px 32px',
      },
      boxShadow: {
        'glow-cyan':    '0 0 20px rgba(34,211,238,0.15)',
        'glow-emerald': '0 0 20px rgba(16,185,129,0.2)',
        'glow-rose':    '0 0 20px rgba(244,63,94,0.15)',
        'card':         '0 1px 3px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.3)',
      },
    },
  },
  plugins: [],
}
