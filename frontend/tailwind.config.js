/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Remap Tailwind's blue scale to the Stadler palette so existing
        // hardcoded blue-* usages rebrand automatically.
        blue: {
          50: '#F0F7FE',
          100: '#D6E6F5',
          200: '#AECCEB',
          300: '#7FAEDC',
          400: '#4B8BCB',
          500: '#007BC0', // Stadler Light Blue — focus rings
          600: '#1E5A9A', // Stadler Blue — primary
          700: '#0B3F75', // Stadler Dark Blue — hover / dark
          800: '#093059',
          900: '#07223F',
        },
        // Semantic aliases for new on-brand styling.
        brand: {
          DEFAULT: '#1E5A9A',
          dark: '#0B3F75',
          light: '#007BC0',
          accent: '#FFBD00',
          surface: '#F0F7FE',
        },
      },
      fontFamily: {
        sans: ['Arial', 'Helvetica', 'sans-serif'],
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(-45deg, #007BC0, #0B3F75)',
      },
    },
  },
  plugins: [],
}
