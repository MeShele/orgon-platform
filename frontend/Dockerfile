FROM node:20-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# `NEXT_PUBLIC_API_URL` is baked into the client bundle — leave it
# empty so client-side fetches use relative URLs (and the Next.js
# node server proxies them via the rewrite rule).
# `BACKEND_INTERNAL_URL` is consumed only by the rewrite() in
# next.config.ts at build time and survives into runtime via the
# generated routes manifest.
ARG BACKEND_INTERNAL_URL=http://localhost:8890
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# BACKEND_INTERNAL_URL must be present at runtime as well — it's
# referenced by the rewrites function each time the standalone
# server starts.
ARG BACKEND_INTERNAL_URL=http://localhost:8890
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
