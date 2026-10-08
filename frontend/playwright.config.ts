import { defineConfig, devices } from '@playwright/test'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'

const apiUrl = 'http://127.0.0.1:8001'
const e2eDatabase = resolve(tmpdir(), `skillsetu-review-e2e-${Date.now()}.db`).replaceAll('\\', '/')

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5175',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: `${process.env.PYTHON ?? 'python'} -m uvicorn app.main:app --host 127.0.0.1 --port 8001`,
      cwd: '../backend',
      url: `${apiUrl}/health`,
      env: { SKILLSETU_DB_URL: `sqlite:///${e2eDatabase}`, SECOND_REVIEW_SAMPLE_RATE: '0.2' },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5175 --strictPort',
      url: 'http://127.0.0.1:5175',
      env: { VITE_API_BASE_URL: apiUrl },
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
})
