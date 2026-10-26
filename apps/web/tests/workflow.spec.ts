import { test, expect } from '@playwright/test'

const password = process.env.E2E_PASSWORD || 'Nexus-demo-2026!'
const login = async (page: import('@playwright/test').Page, email: string) => {
  await page.goto('/login')
  await page.getByLabel('Work email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in to workspace' }).click()
  await expect(page.getByRole('heading', { name: 'Where would you like to work?' })).toBeVisible()
}

test('complete ticket → analysis → approval → tenant isolation journey', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await login(page, process.env.E2E_EMAIL || 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await expect(page.getByRole('heading', { name: 'All tickets' })).toBeVisible()
  const subject = `Delivery delayed · browser ${Date.now()}`
  await page.getByRole('button', { name: 'Create ticket' }).click()
  await page.getByLabel('Subject', { exact: true }).fill(subject)
  await page
    .getByLabel('Customer message')
    .fill('My order has been delayed for five days. Could you please check delivery status?')
  await page.getByRole('dialog').getByRole('button', { name: 'Create ticket' }).click()
  await expect(page.getByRole('heading', { name: subject })).toBeVisible()
  await page.getByRole('button', { name: 'Analyze with AI' }).click()
  await expect(page.getByRole('heading', { name: 'Suggested response' })).toBeVisible({ timeout: 40000 })
  await expect(page.getByText('Delivery support procedure', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Approve draft' }).click()
  await expect(page.getByText('Approved for use. No message has been sent.', { exact: false })).toBeVisible()
  await page.reload()
  await expect(page.getByText('Approved for use. No message has been sent.', { exact: false })).toBeVisible()
  await page.getByRole('link', { name: /Acme Corporation Workspace/ }).click()
  await page.getByRole('button', { name: /Nova Technologies/ }).click()
  await expect(page.getByRole('heading', { name: 'All tickets' })).toBeVisible()
  await expect(page.getByText(subject, { exact: true })).toHaveCount(0)
  await expect(page.getByText('Private Nova ticket', { exact: true })).toBeVisible()
  expect(errors).toEqual([])
})

test('viewer sees read-only tickets and cannot manage knowledge', async ({ page }) => {
  await login(page, 'viewer@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await expect(page.getByRole('button', { name: 'Create ticket' })).toHaveCount(0)
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click()
  await expect(page.getByRole('button', { name: 'New document' })).toHaveCount(0)
  await page.getByRole('button', { name: /Delivery support procedure/ }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save document' })).toHaveCount(0)
})

test('admin knowledge editing, archiving and audit', async ({ page }) => {
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click()
  await page.getByRole('button', { name: 'New document' }).click()
  const title = `Export support guide ${Date.now()}`
  await page.getByLabel('Title', { exact: true }).fill(title)
  await page
    .getByLabel('Content', { exact: true })
    .fill('For export errors, collect the error code and contact the technical support team.')
  await page.getByRole('button', { name: 'Save document' }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
  await page.getByRole('button', { name: new RegExp(title) }).click()
  await page.getByLabel('Active · available to AI retrieval').uncheck()
  await page.getByRole('button', { name: 'Save document' }).click()
  await expect(page.getByRole('button', { name: new RegExp(title) })).toContainText('archived')
  await page.getByRole('link', { name: 'Organization settings' }).click()
  await expect(page.getByRole('heading', { name: 'Workspace members' })).toBeVisible()
  await expect(page.getByText('knowledge · updated').first()).toBeVisible()
})

test('mobile layout, session restoration, keyboard and logout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await expect(page.getByRole('heading', { name: 'All tickets' })).toBeVisible()
  await page.locator('tbody tr').first().waitFor()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'All tickets' })).toBeVisible()
  await page.getByRole('button', { name: 'Create ticket' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.getByRole('button', { name: 'Toggle navigation' }).click()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible()
})

test('network interruption after acceptance reuses the same analysis operation', async ({ page }) => {
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await page.getByRole('button', { name: 'Create ticket' }).click()
  const subject = `Network recovery ${Date.now()}`
  await page.getByLabel('Subject', { exact: true }).fill(subject)
  await page.getByLabel('Customer message').fill('Please help confirm the status of a delayed delivery.')
  await page.getByRole('dialog').getByRole('button', { name: 'Create ticket' }).click()
  await expect(page.getByRole('heading', { name: subject })).toBeVisible()
  const keys: string[] = []
  page.on('request', (request) => {
    if (request.url().endsWith('/analyze')) keys.push(request.headers()['idempotency-key'] || '')
  })
  let interrupted = false
  await page.route(/\/api\/v1\/tenants\/[^/]+\/runs\/[^/?]+$/, async (route) => {
    if (!interrupted) {
      interrupted = true
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'TEST_UNAVAILABLE',
            message: 'Temporary network interruption. Try again.',
            request_id: crypto.randomUUID(),
          },
        }),
      })
    } else await route.continue()
  })
  const first = page.waitForResponse((response) => response.url().endsWith('/analyze'))
  await page.getByRole('button', { name: 'Analyze with AI' }).click()
  const accepted = await (await first).json()
  await expect(page.getByRole('alert')).toContainText('Temporary network interruption')
  const retry = page.waitForResponse((response) => response.url().endsWith('/analyze'))
  await page.getByRole('button', { name: 'Analyze with AI' }).click()
  const recovered = await (await retry).json()
  expect(recovered.run_id).toBe(accepted.run_id)
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBeTruthy()
  expect(keys[0]).toBe(keys[1])
  await expect(page.getByRole('heading', { name: 'Suggested response' })).toBeVisible({ timeout: 40000 })
})
