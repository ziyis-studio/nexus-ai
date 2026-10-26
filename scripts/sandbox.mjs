// One-command portable QA launcher. This uses synthetic identity and LLM fixtures.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import process from 'node:process'

const children = []
const env = {
  ...process.env,
  NUXT_PUBLIC_API_BASE: 'http://127.0.0.1:8000',
  NUXT_PUBLIC_SUPABASE_URL: 'http://127.0.0.1:54321',
  NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: 'sandbox-public-key',
}
let closing = false
const shutdown = () => {
  if (closing) return
  closing = true
  for (const child of children.reverse()) {
    if (process.platform === 'win32')
      spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore', windowsHide: true })
    else child.kill('SIGTERM')
  }
  process.exit(0)
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
const start = (command, args, readyText) =>
  new Promise((resolve, reject) => {
    const child = spawn(command, args, { env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    children.push(child)
    child.on('error', reject)
    let output = ''
    const log = (data) => {
      const text = data.toString()
      process.stdout.write(text)
      output += text
      if (readyText && output.includes(readyText)) resolve(child)
    }
    child.stdout.on('data', log)
    child.stderr.on('data', log)
    child.on('exit', (code) => {
      if (readyText && !closing) reject(new Error(`Service exited before readiness (${code})`))
    })
    if (!readyText) resolve(child)
  })
const wait = async (url, ready = (r) => r.ok) => {
  for (let i = 0; i < 90; i++) {
    try {
      const response = await fetch(url)
      if (ready(response)) return
    } catch {
      /* service starting */
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error(`Service did not become ready: ${url}`)
}
try {
  console.log(
    'NEXUS portable QA: real PostgreSQL / PostgREST; synthetic auth, Redis test double and fixture LLM. Never expose this harness publicly.',
  )
  if (
    !existsSync(
      process.platform === 'win32' ? '.local/postgrest/postgrest.exe' : '.local/postgrest/postgrest',
    )
  ) {
    const result = spawnSync('uv', ['run', 'python', 'scripts/download-postgrest.py'], {
      stdio: 'inherit',
      windowsHide: true,
    })
    if (result.status !== 0) throw new Error('Could not install the pinned official PostgREST binary.')
  }
  await start(process.execPath, ['scripts/sandbox-db.mjs'], 'Native PostgreSQL QA database ready')
  await start('uv', ['run', 'python', 'scripts/sandbox_auth.py'])
  await wait('http://127.0.0.1:54321/auth/v1/user', (r) => r.status === 401)
  await start('uv', ['run', 'python', 'scripts/sandbox-services.py'])
  await wait('http://127.0.0.1:8000/health/ready')
  await start(process.execPath, ['node_modules/nuxt/bin/nuxt.mjs', 'dev', 'apps/web', '--host', '127.0.0.1'])
  await wait('http://127.0.0.1:3000/login')
  console.log(
    '\nReady: http://127.0.0.1:3000 · admin@nexus.test / Nexus-demo-2026!\nSynthetic QA data only. Ctrl+C stops the owned services.\n',
  )
} catch (error) {
  console.error(error.message)
  shutdown()
}
