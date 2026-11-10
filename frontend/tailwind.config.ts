import type { Config } from "tailwindcss";
const config: Config = { content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"], theme: { extend: { colors: { forest: "#173E32", harvest: "#E8B95F", warm: "#F7F5ED" }, fontFamily: { sans: ["var(--font-ui)", "sans-serif"] } } }, plugins: [] };
export default config;
