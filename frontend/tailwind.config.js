/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Risk level colors
        'risk-safe': '#22c55e',
        'risk-observe': '#eab308',
        'risk-danger': '#f97316',
        'risk-freeze': '#ef4444',
        // Brand colors
        'primary': '#3b82f6',
        'secondary': '#6366f1',
      },
    },
  },
  plugins: [],
}
