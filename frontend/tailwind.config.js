/** @type {import('tailwindcss').Config} */
import colors from 'tailwindcss/colors';

export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      colors: {
        // The "Trellis" Brand Color
        primary: {
          50: colors.teal[50],
          100: colors.teal[100],
          500: colors.teal[500],
          600: colors.teal[600], // Main Action Color
          700: colors.teal[700],
        },
        // The "Technical" Gray Scale
        gray: colors.slate,
        // Semantic aliases
        danger: colors.rose,
        success: colors.emerald,
      }
    },
  },
  plugins: [],
}
