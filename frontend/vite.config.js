import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      // @ 指向 src/ —— shadcn 组件之间用 @/components 互相引用, 必须配
      '@': path.resolve(__dirname, './src'),
    },
  },
})