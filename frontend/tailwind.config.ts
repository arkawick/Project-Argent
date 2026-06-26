import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom surface shades for the dark dashboard
        surface: {
          DEFAULT: "#111827",  // gray-900
          raised: "#1f2937",   // gray-800
          border: "#374151",   // gray-700
        },
      },
    },
  },
  plugins: [],
}

export default config
