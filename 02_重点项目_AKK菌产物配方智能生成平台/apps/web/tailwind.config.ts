import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(214 32% 91%)",
        background: "hsl(0 0% 100%)",
        foreground: "hsl(222 47% 11%)",
        muted: "hsl(210 40% 96%)",
        "muted-foreground": "hsl(215 16% 47%)",
        primary: "hsl(173 58% 28%)",
        "primary-foreground": "hsl(0 0% 100%)",
        accent: "hsl(42 88% 55%)",
        destructive: "hsl(0 72% 51%)"
      }
    }
  },
  plugins: [],
};

export default config;
