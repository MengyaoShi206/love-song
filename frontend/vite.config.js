// import { defineConfig } from 'vite'
// import vue from '@vitejs/plugin-vue'

// export default defineConfig({
//   plugins: [vue()],
//   server: {
//     host: '0.0.0.0',
//     port: 5173,
//   }
// })
// // export default defineConfig({
// //   plugins: [vue()],
// //   server: {
// //     port: 5173,
// //     host: true
// //   }
// // })
// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: { host: true, port: 5173 }
})
