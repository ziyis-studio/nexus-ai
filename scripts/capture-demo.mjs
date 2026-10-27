// Local-only product evidence. Auth and model output are explicit QA fixtures.
import { chromium, expect } from '@playwright/test'
import { mkdir, rename } from 'node:fs/promises'
import { setTimeout } from 'node:timers/promises'

const web = 'http://127.0.0.1:3000'
const api = 'http://127.0.0.1:8000/api/v1'
const auth = 'http://127.0.0.1:54321'
await mkdir('docs/screenshots', { recursive: true })
await mkdir('docs/demo', { recursive: true })
const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: '.local/demo-video', size: { width: 1440, height: 1000 } },
  reducedMotion: 'reduce',
})
const credentials = { email: 'admin@nexus.test', password: 'Nexus-demo-2026!' }
const signedIn = await context.request.post(auth + '/auth/v1/token?grant_type=password', {
  headers: { apikey: 'sandbox-public-key' },
  data: credentials,
})
if (!signedIn.ok()) throw new Error('Start the local synthetic QA environment before capturing.')
const token = (await signedIn.json()).access_token
const call = async (path, method = 'GET', data) => {
  const response = await context.request.fetch(api + path, {
    method,
    data,
    headers: { Authorization: 'Bearer ' + token },
  })
  if (!response.ok()) throw new Error('Synthetic fixture setup failed: ' + response.status())
  return response.json()
}
const tenants = await call('/me/tenants')
const acme = tenants.find((tenant) => tenant.slug === 'acme')
if (!acme) throw new Error('The local Acme QA workspace is missing.')
const prefix = '/tenants/' + acme.id
const samples = [
  [
    'Thanks for the quick resolution',
    'Morgan Reed',
    'resolved',
    'low',
    'Thank you for helping resolve the account issue. Everything is working again.',
  ],
  [
    'Update the delivery address',
    'Riley Park',
    'open',
    'normal',
    'Could you update the delivery address before the order is dispatched? I can confirm the new details.',
  ],
  [
    'Questions about the enterprise plan',
    'Casey Williams',
    'open',
    'normal',
    'Our team is growing. Could you explain which enterprise plan features are available to us?',
  ],
  [
    'Export stops before completion',
    'Taylor Brooks',
    'in_progress',
    'high',
    'The application closes when exporting a large report. The same export worked last week.',
  ],
  [
    'Unable to reset account password',
    'Jamie Chen',
    'open',
    'high',
    'I requested a password reset but the link has expired. Please help me regain access to my account.',
  ],
  [
    'Duplicate charge on October renewal',
    'Sam Rivera',
    'open',
    'high',
    'The October renewal appears twice on my statement. Could you investigate the duplicate billing?',
  ],
  [
    'Production integration is blocked',
    'Jordan Lee',
    'in_progress',
    'urgent',
    'Our production integration stopped accepting requests this morning. Please help our team investigate.',
  ],
  [
    'Delivery delayed for five days',
    'Alex Morgan',
    'open',
    'high',
    'My order has been delayed for five days. Could you check the delivery status and let me know the next steps?',
  ],
]
let previewTicket
for (const [subject, customer_name, status, priority, description] of samples) {
  const existing = await call(prefix + '/tickets?q=' + encodeURIComponent(subject))
  const previous = existing.items.find(
    (item) => item.subject === subject && item.external_reference === 'synthetic-ui-walkthrough',
  )
  const ticket =
    previous ||
    (await call(prefix + '/tickets', 'POST', {
      subject,
      description,
      customer_name,
      external_reference: 'synthetic-ui-walkthrough',
    }))
  await call(prefix + '/tickets/' + ticket.id, 'PATCH', { status, priority })
  previewTicket = ticket
}
const documents = [
  [
    'Refund request checklist',
    'policy',
    'For refund requests, collect the order reference and the reason for the request. Ask the billing team to verify eligibility before promising a refund.',
    true,
  ],
  [
    'Account access FAQ',
    'faq',
    'If an account access link expires, ask the customer to request a fresh link. Never request their password or authentication codes.',
    true,
  ],
  [
    'Enterprise workspace guide',
    'product_information',
    'Enterprise workspaces keep tickets and knowledge separate by organization. Contact the account team to discuss additional requirements.',
    true,
  ],
  [
    'Previous fulfilment procedure',
    'general_reference',
    'Archived example: this previous fulfilment procedure is retained for historical reference and is not available to new analyses.',
    false,
  ],
]
for (const [title, document_type, content, is_active] of documents) {
  const existing = await call(prefix + '/knowledge?q=' + encodeURIComponent(title))
  if (!existing.items.some((item) => item.title === title))
    await call(prefix + '/knowledge', 'POST', { title, document_type, content, is_active })
}
const page = await context.newPage()
const errors = []
page.on('pageerror', (error) => errors.push(error.message))
const shot = async (name, fullPage = false) => {
  await page.evaluate(() => document.fonts.ready)
  await expect(page.locator('[data-sonner-toast]')).toHaveCount(0, { timeout: 7000 })
  await page.screenshot({ path: 'docs/screenshots/' + name + '.png', fullPage })
  await setTimeout(900)
}
await page.goto(web + '/login')
await page.getByRole('heading', { name: 'Welcome back.' }).waitFor()
await shot('login')
await page.getByLabel('Work email').fill(credentials.email)
await page.getByLabel('Password', { exact: true }).fill(credentials.password)
await page.getByRole('button', { name: 'Sign in to workspace' }).click()
await page.getByRole('button', { name: /Acme Corporation/ }).waitFor()
await shot('workspaces')
await page.getByRole('button', { name: /Acme Corporation/ }).click()
await page.locator('tbody tr').first().waitFor()
await shot('tickets')
await page.locator('a[href="/t/' + acme.id + '/tickets/' + previewTicket.id + '"]').click()
await page.getByRole('heading', { name: 'AI workspace', exact: true }).waitFor()
await page.getByRole('button', { name: /Analyze with AI|Run a new analysis/ }).click()
await page.getByRole('heading', { name: 'Suggested response' }).waitFor({ timeout: 30000 })
await page.getByText('Delivery support procedure', { exact: true }).waitFor()
await expect(page.getByRole('button', { name: 'Run a new analysis' })).toBeEnabled()
await shot('analysis', true)
await page.getByRole('button', { name: 'Approve draft' }).click()
await page.getByText('Approved for use. No message has been sent.', { exact: false }).waitFor()
await setTimeout(900)
await page.getByRole('link', { name: 'Knowledge base', exact: true }).click()
await page.getByRole('heading', { name: 'Delivery support procedure', exact: true }).waitFor()
await shot('knowledge')
await page.getByRole('link', { name: 'Organization settings' }).click()
await page.getByRole('heading', { name: 'Workspace details', exact: true }).waitFor()
await shot('settings')
await page.getByRole('link', { name: 'Execution history', exact: true }).click()
await page.locator('tbody tr').first().waitFor()
await shot('history')
await page.keyboard.press('ControlOrMeta+k')
await page.getByPlaceholder('Find a page or workspace…').fill('Nova')
await page.keyboard.press('Enter')
await page.getByText('Private Nova ticket', { exact: true }).waitFor()
await page.setViewportSize({ width: 390, height: 844 })
await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
await shot('mobile', true)
await page.getByRole('button', { name: 'Toggle navigation' }).click()
await page.getByRole('link', { name: 'Knowledge base', exact: true }).waitFor()
await shot('mobile-navigation')
await page.keyboard.press('Escape')
await page.setViewportSize({ width: 1440, height: 1000 })
await page.getByRole('button', { name: /^Switch workspace:/ }).click()
await page.getByRole('menuitem', { name: /Acme Corporation/ }).click()
await page.locator('tbody tr').first().waitFor()
await page.getByRole('button', { name: 'Change appearance' }).click()
await page.getByRole('menuitem', { name: 'Dark', exact: true }).click()
await shot('dark')
await page.getByRole('button', { name: 'Change appearance' }).click()
await page.getByRole('menuitem', { name: 'Light', exact: true }).click()
expect(errors).toEqual([])
await context.close()
await rename(await page.video().path(), 'docs/demo/product-walkthrough.webm')
await browser.close()
console.log('Captured ten redesigned views and the local synthetic workflow walkthrough.')
