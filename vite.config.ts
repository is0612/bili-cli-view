import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端（FastAPI）跑在 8811，前端 dev 走 5199，/api 一律转发过去
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5199,
    strictPort: true,
    // 后端是 Python，Vite 盯它既没用、又会被 uvicorn/编辑器的临时文件搞崩
    // （EBUSY: resource busy or locked → 整个 dev 进程退出）
    watch: {
      ignored: ['**/backend/**', '**/.venv/**', '**/runtime/**'],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8811',
        changeOrigin: true,
      },
    },
  },
})
