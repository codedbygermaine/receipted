import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// base matches the GitHub Pages path (https://codedbygermaine.github.io/receipted/); hash routing means no 404s.
export default defineConfig({
  base: "/receipted/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
})
