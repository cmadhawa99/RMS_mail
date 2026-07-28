/** @type {import('tailwindcss').Config} */
module.exports = {
  // This enables the dark mode toggle you built
  darkMode: 'class',
  content: [
    './letters/templates/**/*.html',
    './letters/**/*.py',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Noto Sans Sinhala"', 'sans-serif'],
      },
      colors: {
        primary: '#3b82f6',
      }
    }
  },
  plugins: [],
}