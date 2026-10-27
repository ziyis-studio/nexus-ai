export default defineNuxtPlugin(() => {
  const { appearance, setAppearance } = useAppearance()
  let stored: string | null = null
  try {
    stored = localStorage.getItem('nexus.appearance')
  } catch {
    /* Storage is optional. */
  }
  if (stored === 'light' || stored === 'dark' || stored === 'system') appearance.value = stored
  setAppearance(appearance.value)
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (appearance.value === 'system') setAppearance('system')
  })
})
