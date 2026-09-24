import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      // @ 指向 src/ —— shadcn 组件之间用 @/components 互相引用, 必须配
      // 用 import.meta.url: 配置文件是 ES module, __dirname 在 ESM 里并不存在(Vite 恰好兜底)
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})