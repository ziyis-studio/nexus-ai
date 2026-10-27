import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2026-10-27',
  srcDir: '.',
  ssr: false,
  devtools: { enabled: false },
  modules: ['shadcn-nuxt'],
  shadcn: { prefix: 'Ui', componentDir: './components/ui' },
  components: [{ path: '~/components', ignore: ['ui/**'] }],
  css: ['~/assets/main.css'],
  vite: { plugins: [tailwindcss()] },
  runtimeConfig: {
    public: { apiBase: 'http://127.0.0.1:8000', supabaseUrl: '', supabasePublishableKey: '' },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'en' },
      title: 'Nexus · Support intelligence',
      meta: [
        {
          name: 'description',
          content: 'A focused workspace for customer support, grounded AI drafts and human decisions.',
        },
      ],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },
  typescript: { strict: true },
})
