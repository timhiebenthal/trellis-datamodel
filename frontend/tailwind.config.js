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
        primary: colors.teal,
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
