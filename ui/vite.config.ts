import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/tokens" as *;\n`,
      },
    },
  },
  server: {
    proxy: {
      '/ws': {
        target: 'ws://127.0.0.1:18765',
        ws: true,
      },
    },
  },
})
