/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Neutral blue scale (standard). Existing hardcoded blue-* usages
        // pick this up automatically.
        blue: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6', // focus rings
          600: '#2563EB', // primary
          700: '#1D4ED8', // hover / dark
          800: '#1E40AF',
          900: '#1E3A8A',
        },
        // Semantic aliases for on-brand styling.
        brand: {
          DEFAULT: '#2563EB',
          dark: '#1E3A8A',
          light: '#3B82F6',
          accent: '#F59E0B',
          surface: '#EFF6FF',
        },
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(-45deg, #3B82F6, #1E3A8A)',
      },
    },
  },
  plugins: [],
}
