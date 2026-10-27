import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const password = process.env.E2E_PASSWORD || 'Nexus-demo-2026!'
const login = async (page: import('@playwright/test').Page, email: string) => {
  await page.goto('/login')
  await page.getByLabel('Work email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in to workspace' }).click()
  await expect(page.getByRole('heading', { name: 'Where would you like to work?' })).toBeVisible()
}

test('core screens and create dialog satisfy automated WCAG checks', async ({ page }) => {
  const scan = async (screen: string) => {
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()
    expect(
      result.violations,
      screen +
        ': ' +
        JSON.stringify(
          result.violations.map((item) => ({
            id: item.id,
            impact: item.impact,
            targets: item.nodes.map((node) => node.target),
          })),
        ),
    ).toEqual([])
  }
  await page.goto('/login')
  await page.getByLabel('Work email').waitFor()
  await scan('Sign in')
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).waitFor()
  await scan('Workspaces')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await page.locator('tbody tr').first().waitFor()
  await scan('Ticket queue')
  await page.getByRole('button', { name: 'Create ticket', exact: true }).click()
  await expect(page.getByLabel('Subject', { exact: true })).toBeFocused()
  await scan('Create ticket dialog')
  await page.keyboard.press('Escape')
  await page.getByRole('link', { name: 'Knowledge base', exact: true }).click()
  await page.getByRole('heading', { name: 'Knowledge base', exact: true }).waitFor()
  await scan('Knowledge base')
  await page.getByRole('link', { name: 'Organization settings' }).click()
  await page.getByRole('tab', { name: 'Appearance', exact: true }).click()
  await scan('Appearance')
  await page.getByRole('button', { name: 'Dark', exact: true }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await scan('Dark appearance')
  await page.getByRole('button', { name: 'Light', exact: true }).click()
})

test('complete ticket → analysis → approval → tenant isolation journey', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await login(page, process.env.E2E_EMAIL || 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await expect(page.getByRole('heading', { name: 'Tickets', exact: true })).toBeVisible()
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
  await page.getByRole('button', { name: /^Switch workspace:/ }).click()
  await page.getByRole('menuitem', { name: /Nova Technologies/ }).click()
  await expect(page.getByRole('heading', { name: 'Tickets', exact: true })).toBeVisible()
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
  await expect(
    page.locator('[data-slot="card"]').filter({ has: page.getByRole('heading', { name: title }) }),
  ).toContainText('Archived')
  await page.getByRole('link', { name: 'Organization settings' }).click()
  await page.getByRole('tab', { name: 'Members', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Workspace members' })).toBeVisible()
  await page.getByRole('tab', { name: 'Audit trail', exact: true }).click()
  await expect(page.getByText('Knowledge updated', { exact: true }).first()).toBeVisible()
})

test('mobile layout, session restoration, keyboard and logout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await expect(page.getByRole('heading', { name: 'Tickets', exact: true })).toBeVisible()
  await page.locator('tbody tr').first().waitFor()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Tickets', exact: true })).toBeVisible()
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

test('quick navigation and appearance persist across reloads', async ({ page }) => {
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await expect(page.getByRole('heading', { name: 'Tickets', exact: true })).toBeVisible()
  await page.keyboard.press('ControlOrMeta+k')
  await expect(page.getByRole('dialog', { name: 'Quick navigation' })).toBeVisible()
  await page.getByPlaceholder('Find a page or workspace…').fill('Knowledge')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Knowledge base', exact: true })).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: 'Change appearance' }).click()
  await page.getByRole('menuitem', { name: 'Dark', exact: true }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await page.reload()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await expect(page.getByRole('heading', { name: 'Knowledge base', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Change appearance' }).click()
  await page.getByRole('menuitem', { name: 'Light', exact: true }).click()
  await expect(page.locator('html')).not.toHaveClass(/dark/)
})

test('ticket search recovers from an empty view and dialogs restore focus', async ({ page }) => {
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await page.locator('tbody tr').first().waitFor()
  await page.getByLabel('Search tickets').fill('no-match-' + Date.now())
  await expect(page.getByText('No matching tickets', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click()
  await expect(page.getByLabel('Search tickets')).toHaveValue('')
  await page.locator('tbody tr').first().waitFor()
  const create = page.getByRole('button', { name: 'Create ticket', exact: true })
  await create.click()
  await expect(page.getByLabel('Subject', { exact: true })).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  expect(await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]'))).toBe(true)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(create).toBeFocused()
})

test('ticket editing, final rejection and a narrow reduced-motion layout', async ({ page }) => {
  await login(page, 'admin@nexus.test')
  await page.getByRole('button', { name: /Acme Corporation/ }).click()
  await page.getByRole('button', { name: 'Create ticket', exact: true }).click()
  const subject = 'Priority review ' + Date.now()
  await page.getByLabel('Subject', { exact: true }).fill(subject)
  await page
    .getByLabel('Customer message')
    .fill('Please help investigate a delayed delivery and confirm the next steps.')
  await page.getByRole('dialog').getByRole('button', { name: 'Create ticket', exact: true }).click()
  await expect(page.getByRole('heading', { name: subject })).toBeVisible()
  await page.getByRole('button', { name: 'Edit ticket' }).click()
  await page.getByLabel('Priority', { exact: true }).selectOption('urgent')
  await page.getByLabel('Status', { exact: true }).selectOption('in_progress')
  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByText('Urgent', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Analyze with AI' }).click()
  await expect(page.getByRole('heading', { name: 'Suggested response' })).toBeVisible({ timeout: 40000 })
  await page.getByRole('tab', { name: 'Insights' }).click()
  await expect(page.getByRole('heading', { name: 'Decision rationale' })).toBeVisible()
  await page.getByRole('tab', { name: 'Response', exact: true }).click()
  await page.getByRole('button', { name: 'Reject', exact: true }).click()
  await expect(page.getByRole('alertdialog', { name: 'Reject this draft?' })).toBeVisible()
  await page.keyboard.press('ControlOrMeta+k')
  await expect(page.getByRole('dialog', { name: 'Quick navigation' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Keep reviewing' }).click()
  await expect(page.getByRole('button', { name: 'Approve draft' })).toBeEnabled()
  await page.getByRole('button', { name: 'Reject', exact: true }).click()
  await page.getByRole('button', { name: 'Reject draft', exact: true }).click()
  await expect(
    page.getByText('Rejected. Start a new analysis for another suggestion.', { exact: false }),
  ).toBeVisible()
  await page.reload()
  await expect(
    page.getByText('Rejected. Start a new analysis for another suggestion.', { exact: false }),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Approve draft' })).toHaveCount(0)
  await page.setViewportSize({ width: 320, height: 800 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
