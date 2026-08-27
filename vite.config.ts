import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import { resolve } from 'path'

export default defineConfig({
  plugins: [uni()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@antv/f2': resolve(__dirname, 'node_modules/@antv/f2/lib/index.js'),
      '@antv/util/lib/type/is-array': resolve(__dirname, 'node_modules/@antv/util/lib/is-array.js'),
      '@antv/util/lib/type/is-nil': resolve(__dirname, 'node_modules/@antv/util/lib/is-nil.js'),
      '@antv/util/lib/array/merge': resolve(__dirname, 'node_modules/@antv/util/lib/merge.js'),
      '@antv/util/lib/math/max-by': resolve(__dirname, 'node_modules/@antv/util/lib/max-by.js'),    },
  },
  server: {
    port: 5173,
    host: true,
    // 代理 API 请求到后端 FastAPI
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 全局注入 uni.scss 和自定义变量
        additionalData: '@import "@/styles/variables.scss";\n@import "@/uni.scss";\n',
      },
    },
  },
})
