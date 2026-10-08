import { expect, test } from '@playwright/test'

const API = process.env.PLAYWRIGHT_API_URL ?? 'http://127.0.0.1:8001'

async function apiLogin(request: import('@playwright/test').APIRequestContext, username: string, password: string) {
  const response = await request.post(`${API}/api/auth/login`, { data: { username, password } })
  expect(response.ok()).toBeTruthy()
  return (await response.json()).access_token as string
}

function authorization(token: string) {
  return { Authorization: 'Bearer ' + token }
}

async function browserLogin(
  page: import('@playwright/test').Page,
  username: string,
  password: string,
  destination = '/assessor/score',
) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL(new RegExp(`${destination.replaceAll('/', '\\/')}$`))
}

test('presents a signed QR certificate, impact charts and tamper detection', async ({ page, request }, testInfo) => {
  test.setTimeout(90_000)
  const workerToken = await apiLogin(request, 'worker1', 'worker123')
  const assessmentResponse = await request.post(`${API}/api/assessments`, {
    headers: authorization(workerToken),
    data: { text: 'Demo electrical installation and worksite safety assessment.', matches: [] },
  })
  expect(assessmentResponse.ok()).toBeTruthy()
  const assessmentId = (await assessmentResponse.json()).id as number

  const evidence = await request.post(`${API}/api/evidence`, {
    headers: authorization(workerToken),
    data: {
      title: 'Presentation demo evidence',
      sha256: 'b'.repeat(64),
      timestamp: new Date().toISOString(),
      required_steps: ['Verify isolation'],
      steps: [],
    },
  })
  expect(evidence.ok()).toBeTruthy()

  const assessorToken = await apiLogin(request, 'assessor1', 'assessor123')
  const competenciesResponse = await request.get(`${API}/api/competencies`)
  const competencies = (await competenciesResponse.json()).competencies as Array<{ id: string }>
  let secondReviewerId: number | null = null
  for (const competency of competencies) {
    const response = await request.post(`${API}/api/score`, {
      headers: authorization(assessorToken),
      data: {
        assessment_id: assessmentId,
        competency_id: competency.id,
        score: 4,
        explanation: 'Presentation demo rating based on the declared evidence.',
        override_reason: 'Independent rating based on the evidence record.',
      },
    })
    if (!response.ok()) throw new Error(`Primary score failed: ${response.status()} ${await response.text()}`)
    expect(response.ok()).toBeTruthy()
    const result = await response.json()
    secondReviewerId = result.assigned_assessor_id ?? secondReviewerId
  }
  expect(secondReviewerId).toBeTruthy()

  const secondAssessorNumber = secondReviewerId! - 2
  expect(secondAssessorNumber).toBeGreaterThan(1)
  const secondToken = await apiLogin(request, `assessor${secondAssessorNumber}`, 'assessor123')
  for (const competency of competencies) {
    const response = await request.post(`${API}/api/score`, {
      headers: authorization(secondToken),
      data: {
        assessment_id: assessmentId,
        competency_id: competency.id,
        score: 4,
        explanation: 'Independent presentation demo review.',
        override_reason: 'Independent rating based on the evidence record.',
      },
    })
    if (!response.ok()) throw new Error(`Second score failed: ${response.status()} ${await response.text()}`)
    expect(response.ok()).toBeTruthy()
  }

  await browserLogin(page, 'assessor1', 'assessor123')
  await page.goto('/certificate')
  await page.getByLabel('Assessment ID').fill(String(assessmentId))
  await page.getByRole('button', { name: 'Issue and verify' }).click()
  await expect(page.getByRole('img', { name: `QR code linking to verify assessment ${assessmentId}` })).toBeVisible()
  await expect(page.getByText('Verified', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('certificate.png'), fullPage: true })
  const pdfDownload = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download PDF' }).click()
  expect((await pdfDownload).suggestedFilename()).toContain(String(assessmentId))

  await page.goto(`/verify/${assessmentId}`)
  await expect(page.getByRole('heading', { name: 'Credential verified' })).toBeVisible()
  await expect(page.getByText('Ed25519 signature check: Passed')).toBeVisible()
  await expect(page.getByText('Evidence chain check: Passed')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('public-verification.png'), fullPage: true })

  await page.goto('/impact')
  await expect(page.getByRole('heading', { name: 'Impact dashboard' })).toBeVisible()
  await expect(page.getByText('Assessment stage funnel')).toBeVisible()
  await expect(page.getByText('Fairness view')).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('impact-dashboard.png'), fullPage: true })

  await browserLogin(page, 'admin', 'admin123')
  await page.goto('/admin/packs')
  await page.getByRole('button', { name: 'Simulate tampering' }).click()
  await expect(page.getByText('Broken evidence link detected')).toBeVisible()
  await expect(page.getByText(/Evidence #\d+: record_hash_mismatch/)).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('tamper-detection.png'), fullPage: true })
})
