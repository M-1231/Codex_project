import type { Config } from "tailwindcss";
const config: Config = { content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"], theme: { extend: { colors: { accent: "#4f46e5" }, fontFamily: { sans: ["var(--font-inter)", "sans-serif"] } } }, plugins: [] };
export default config;
