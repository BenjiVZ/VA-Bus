import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5001,
    strictPort: true,
    // Un host que empieza con '.' permite el dominio y todos sus subdominios.
    allowedHosts: ['ardvf.aplicacionesdamasco.com', '.masterslogic.com'],
  },
})
