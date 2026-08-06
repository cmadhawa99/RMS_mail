/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './letters/templates/**/*.html',
    './letters/**/*.py',
    './templates/**/*.html',
    './**/templates/**/*.html',
  ],
  safelist: [
    'badge-sector-GOVERNING',
    'badge-sector-HEALTH',
    'badge-sector-DEVELOPMENT',
    'badge-sector-INCOME',
    'badge-sector-ACCOUNTS',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Noto Serif Sinhala"', 'sans-serif'],
      },
      colors: {
        primary: '#3b82f6',
      }
    }
  },
  plugins: [],
}