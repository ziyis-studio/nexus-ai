export type Appearance = 'light' | 'dark' | 'system'
let themeFrame: number | undefined

export const useAppearance = () => {
  const appearance = useState<Appearance>('appearance', () => 'light')
  const setAppearance = (value: Appearance) => {
    appearance.value = value
    try {
      localStorage.setItem('nexus.appearance', value)
    } catch {
      /* Storage is optional. */
    }
    const dark =
      value === 'dark' || (value === 'system' && matchMedia('(prefers-color-scheme: dark)').matches)
    const root = document.documentElement
    if (themeFrame !== undefined) cancelAnimationFrame(themeFrame)
    root.setAttribute('data-theme-changing', '')
    root.classList.toggle('dark', dark)
    root.style.colorScheme = dark ? 'dark' : 'light'
    // Commit the palette together so inherited text cannot outrun background transitions.
    void root.offsetHeight
    themeFrame = requestAnimationFrame(() => {
      root.removeAttribute('data-theme-changing')
      themeFrame = undefined
    })
  }
  return { appearance, setAppearance }
}
