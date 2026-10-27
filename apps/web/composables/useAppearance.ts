export type Appearance = 'light' | 'dark' | 'system'

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
    document.documentElement.classList.toggle('dark', dark)
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
  }
  return { appearance, setAppearance }
}
