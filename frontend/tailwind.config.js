/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Bebas Neue"', 'sans-serif'],
        ui: ['"Exo 2"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        bg: '#020d1a',
        'bg-deep': '#010810',
        cyan: {
          DEFAULT: '#00ccff',
          dim: '#005a7a',
          glow: 'rgba(0,204,255,0.35)',
        },
        sentinel: {
          green: '#00e87a',
          amber: '#ffaa00',
          red: '#ff3344',
          text: '#b8d4e8',
          'text-dim': '#3a6a8a',
          'text-bright': '#e8f4ff',
        },
      },
      backdropBlur: {
        glass: '22px',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04)',
        glow: '0 0 20px rgba(0,204,255,0.3)',
        'glow-green': '0 0 20px rgba(0,232,122,0.4)',
        'glow-red': '0 0 20px rgba(255,51,68,0.4)',
        'glow-amber': '0 0 20px rgba(255,170,0,0.4)',
      },
    },
  },
  plugins: [],
}
