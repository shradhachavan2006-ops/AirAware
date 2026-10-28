import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// All API path prefixes served by the FastAPI backend
const BACKEND_PATHS = [
  '/meta',
  '/dashboard',
  '/observations',
  '/trends',
  '/statistics',
  '/evaluation',
  '/health',
  '/docs',
  '/openapi.json',
  '/redoc',
]

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // If 5173 is taken, use next available port rather than crashing
    strictPort: false,
    proxy: Object.fromEntries(
      BACKEND_PATHS.map(path => [
        path,
        {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          // Preserve the exact path — no rewriting needed
        },
      ])
    ),
  },
})
