import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#FAFAF9",
          subtle: "#F5F4F1",
          elevated: "#FFFFFF",
        },
        ink: {
          DEFAULT: "#1A1A1A",
          muted: "#5C5C5C",
          subtle: "#8A8A8A",
          line: "#E8E6E1",
        },
        accent: {
          DEFAULT: "#6366F1",
          soft: "#EEF0FF",
          ring: "#A5B4FC",
        },
        epistemic: {
          axiomatic: "#10B981",
          experimental: "#6366F1",
          framework: "#F59E0B",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "-apple-system",
          "system-ui",
          "Inter",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(20,20,20,0.04), 0 4px 16px rgba(20,20,20,0.04)",
        glow: "0 0 0 1px rgba(99,102,241,0.18), 0 8px 24px rgba(99,102,241,0.10)",
      },
      borderRadius: {
        xl: "14px",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        shimmer: "shimmer 2s linear infinite",
        fadeUp: "fadeUp 240ms ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
