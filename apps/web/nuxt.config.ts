import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2026-10-27',
  srcDir: '.',
  ssr: false,
  devtools: { enabled: false },
  css: ['~/assets/main.css'],
  vite: { plugins: [tailwindcss()] },
  runtimeConfig: {
    public: {
      apiBase: 'http://127.0.0.1:8000',
      supabaseUrl: '',
      supabasePublishableKey: '',
    },
  },
  app: {
    head: {
      title: 'NEXUS AI · Ticket intelligence',
      meta: [
        {
          name: 'description',
          content: 'A clear workspace for customer support, grounded AI analysis and human decisions.',
        },
      ],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },
  typescript: { strict: true },
})
