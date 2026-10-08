import { expect, test } from '@playwright/test'

const API = process.env.PLAYWRIGHT_API_URL ?? 'http://127.0.0.1:8001'

async function login(page: import('@playwright/test').Page, username: string, password: string, destination = '/assessor/score') {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL(new RegExp(`${destination.replaceAll('/', '\\/')}$`))
}

test('scores blindly, runs second review, and records moderation', async ({ page, request }) => {
  test.setTimeout(90_000)
  const workerLogin = await request.post(`${API}/api/auth/login`, {
    data: { username: 'worker1', password: 'worker123' },
  })
  expect(workerLogin.ok()).toBeTruthy()
  const workerToken = (await workerLogin.json()).access_token as string
  const assessmentResponse = await request.post(`${API}/api/assessments`, {
    headers: { Authorization: `Bearer ${workerToken}` },
    data: { text: 'Evidence of practical electrical installation and safety work.', matches: [] },
  })
  expect(assessmentResponse.ok()).toBeTruthy()
  const assessmentId = (await assessmentResponse.json()).id as number
  const rubricResponse = await request.get(`${API}/api/competencies`)
  const competencyCount = (await rubricResponse.json()).competencies.length as number
  const evidenceResponse = await request.post(`${API}/api/evidence`, {
    headers: { Authorization: `Bearer ${workerToken}` },
    data: {
      title: 'Playwright review evidence',
      sha256: 'a'.repeat(64),
      timestamp: new Date().toISOString(),
      required_steps: ['Verify work safety'],
      steps: [],
      quality: { brightness: 120, blur: 0.1, is_blurry: false },
    },
  })
  expect(evidenceResponse.ok()).toBeTruthy()

  await login(page, 'assessor1', 'assessor123')
  await expect(page.getByText(/Your round:/)).toBeVisible()
  await page.getByLabel('Assessment ID').fill(String(assessmentId))
  await page.getByRole('button', { name: 'Load assessment' }).click()
  const primaryCards = page.locator('.score-card')
  await expect(primaryCards).toHaveCount(competencyCount)
  for (const card of await primaryCards.all()) {
    await card.getByRole('button', { name: '2', exact: true }).click()
    await card.getByLabel('Reason for overriding the hidden AI draft (if required)').fill('Recorded evidence does not meet the safety descriptor.')
    await card.getByRole('button', { name: 'Submit independent score' }).click()
    await expect(card.getByText(/AI draft revealed after submission/)).toBeVisible()
  }
  await expect(page.getByText(/second assessor has been assigned/i)).toBeVisible()

  await login(page, 'assessor2', 'assessor123')
  await expect(page.getByText(/Your round:/)).toBeVisible()
  await page.getByLabel('Assessment ID').fill(String(assessmentId))
  await page.getByRole('button', { name: 'Load assessment' }).click()
  await expect(page.getByText(/independent second review/)).toBeVisible()
  await expect(page.getByText('Your score: 2/5')).toHaveCount(0)
  const secondCards = page.locator('.score-card')
  await expect(secondCards).toHaveCount(competencyCount)
  for (const card of await secondCards.all()) {
    await card.getByRole('button', { name: '5', exact: true }).click()
    await card.getByLabel('Reason for overriding the hidden AI draft (if required)').fill('Direct observation supports the advanced descriptor.')
    await card.getByRole('button', { name: 'Submit independent score' }).click()
    await expect(card.getByText(/Your score: 5\/5/)).toBeVisible()
  }

  await login(page, 'moderator1', 'moderator123', '/')
  await page.goto('/moderation')
  await page.getByLabel('Assessment ID').fill(String(assessmentId))
  await page.getByRole('button', { name: 'Load moderation' }).click()
  await expect(page.getByText(/primary 2 \/ 5 · second assessor 5 \/ 5/).first()).toBeVisible()
  await expect(page.getByText(/AI draft: 3 \/ 5/).first()).toBeVisible()
  for (const reason of await page.getByLabel('Override reason if final score differs from either assessor').all()) {
    await reason.fill('Moderator resolution based on the complete evidence record.')
  }
  await page.getByLabel('Moderation rationale (required)').fill('Both assessor scores and the supporting evidence were reviewed against the rubric.')
  await page.getByRole('button', { name: 'Save rationale and sign off' }).click()
  await expect(page.getByText('Moderation rationale and final scores saved. The assessment is signed off.')).toBeVisible()
  await expect(page.getByText(/signed off/).first()).toBeVisible()
})
