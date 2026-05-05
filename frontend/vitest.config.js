import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    globals: true,
    exclude: [
      'node_modules/**',
      'tests/e2e/**',        // Playwright E2E tests — not for Vitest
      '**/*.spec.js',        // Playwright spec files
      '**/*.spec.ts',
    ],
  },
})