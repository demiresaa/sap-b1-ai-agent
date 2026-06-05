import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Nötr ink skalası (warm gray)
        ink: {
          50: "#F7F7F4",
          100: "#EFEEE8",
          200: "#E2E0D6",
          300: "#C9C6B5",
          400: "#9F9C8A",
          500: "#75726A",
          600: "#5C5A52",
          700: "#3F3E38",
          800: "#222220",
          900: "#0E0F0C",
        },
        // Birincil marka rengi (B1 Agent yeşili)
        accent: {
          DEFAULT: "#0E6F4E",
          50: "#F1F8F4",
          100: "#D6EFE0",
          500: "#0A5B40",
        },
        info: {
          DEFAULT: "#1E66D6",
          50: "#F0F6FF",
          100: "#DBE7FB",
        },
        warn: {
          DEFAULT: "#C76A11",
          50: "#FDF5EB",
          100: "#FAE5C8",
        },
        danger: {
          DEFAULT: "#B5321D",
          50: "#FCF1EF",
          100: "#F8D6CF",
        },
        paper: "#FAFAF6",
        surface: "#FFFFFF",
        // Eski AI rozetleri geriye dönük uyum için tutuluyor
        ai: {
          filled: "#dcfce7",
          uncertain: "#fef9c3",
          empty: "#ffffff",
        },
      },
      boxShadow: {
        card: "0 1px 0 rgba(15, 16, 14, 0.04), 0 1px 2px rgba(15, 16, 14, 0.04)",
        pop: "0 12px 32px -8px rgba(15, 16, 14, 0.18), 0 4px 12px -2px rgba(15, 16, 14, 0.08)",
      },
      letterSpacing: {
        tightish: "-0.005em",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(2px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-dot": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(14, 111, 78, 0.4)" },
          "50%": { boxShadow: "0 0 0 6px rgba(14, 111, 78, 0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 180ms ease-out",
        "pulse-dot": "pulse-dot 1.8s ease-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
