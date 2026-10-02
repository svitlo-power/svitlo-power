import { defineConfig } from 'vite'
import { visualizer } from "rollup-plugin-visualizer";
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5005',
        changeOrigin: true,
        secure: false,
      },
      '/version': {
        target: 'http://localhost:5005',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]',
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('@mantine')
                || id.includes('tanstack')
                || id.includes('dnd-kit')
                || id.includes('floating-ui')
                || id.includes('remark-gfm')
                || id.includes('react-markdown')
                || id.includes('imask'))
              return 'ui-partial';
            if (id.includes('codemirror') || id.includes('lezer')) return 'codemirror';
            if (id.includes('fontawesome')) return 'fontawesome';
            return 'vendor';
          }
        },
      },
      plugins: [
        visualizer({ filename: "stats.html" })
      ],
    },
    chunkSizeWarningLimit: 1600,
  }
})
