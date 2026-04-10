/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0a0a0a',
          surface: '#0f0f0f',
          panel: '#111111',
          border: '#D4A017',
          'border-dim': '#5a4510',
          amber: '#D4A017',
          'amber-bright': '#FFD700',
          'amber-dim': '#8B7215',
          'amber-muted': '#6B5B10',
          'amber-faint': '#2a2210',
          green: '#2B3623',
          'green-bright': '#4a6b3a',
          'green-text': '#6B8E5A',
          red: '#8B2500',
          'red-bright': '#B33A00',
          'red-text': '#CC4422',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'glow': '0 0 8px rgba(212,160,23,0.3)',
        'glow-sm': '0 0 4px rgba(212,160,23,0.2)',
        'glow-bright': '0 0 12px rgba(212,160,23,0.5)',
        'glow-red': '0 0 8px rgba(139,37,0,0.4)',
        'glow-green': '0 0 8px rgba(43,54,35,0.4)',
      },
      animation: {
        'scan': 'scan 8s linear infinite',
        'flicker': 'flicker 0.15s infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        flicker: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.97' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    function({ addUtilities }) {
      addUtilities({
        '.scrollbar-none': {
          '-ms-overflow-style': 'none',
          'scrollbar-width': 'none',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
        '.text-glow': {
          'text-shadow': '0 0 8px rgba(212,160,23,0.6), 0 0 2px rgba(212,160,23,0.3)',
        },
        '.text-glow-sm': {
          'text-shadow': '0 0 4px rgba(212,160,23,0.4)',
        },
        '.border-glow': {
          'box-shadow': '0 0 6px rgba(212,160,23,0.2), inset 0 0 6px rgba(212,160,23,0.05)',
        },
      });
    },
  ],
};
