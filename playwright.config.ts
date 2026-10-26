import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './apps/web/tests',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 60000,
  use: { baseURL: process.env.E2E_WEB_URL || 'http://127.0.0.1:3000', trace: 'retain-on-failure' },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
  ],
  reporter: [['list'], ['html', { open: 'never' }]],
})
