/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0f',
        foreground: '#ffffff',
        primary: '#3b82f6',
        secondary: '#1e293b',
        accent: '#8b5cf6',
      }
    },
  },
  plugins: [],
}
