/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0D0F',
        panel: {
          DEFAULT: '#121518',
          subtle: '#16191D',
          light: '#1B2024',
          border: '#252A2E',
        },
        brand: {
          DEFAULT: '#10E575',
          dark: '#0AA852',
          light: '#4EFA9D',
          dim: 'rgba(16, 229, 117, 0.12)',
        },
        amber: {
          DEFAULT: '#F59E0B',
          dim: 'rgba(245, 158, 11, 0.12)',
        },
        danger: {
          DEFAULT: '#EF4444',
          dim: 'rgba(239, 68, 68, 0.12)',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'glow-brand': '0 0 20px -5px rgba(16, 229, 117, 0.25)',
        'glow-amber': '0 0 20px -5px rgba(245, 158, 11, 0.25)',
      }
    },
  },
  plugins: [],
}
