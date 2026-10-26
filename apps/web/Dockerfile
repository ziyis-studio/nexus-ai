FROM node:24.22.1-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm ci --ignore-scripts
COPY apps/web ./apps/web
ARG NUXT_PUBLIC_API_BASE
ARG NUXT_PUBLIC_SUPABASE_URL
ARG NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
ENV NUXT_PUBLIC_API_BASE=$NUXT_PUBLIC_API_BASE NUXT_PUBLIC_SUPABASE_URL=$NUXT_PUBLIC_SUPABASE_URL NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=$NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
RUN npm run build --workspace apps/web
FROM node:24.22.1-bookworm-slim
WORKDIR /app
COPY --from=build --chown=node:node /app/apps/web/.output ./.output
USER node
ENV HOST=0.0.0.0 PORT=3000
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
