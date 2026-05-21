FROM node:20-alpine AS deps
WORKDIR /app/frontend
ARG NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
COPY frontend/package*.json ./
RUN npm ci \
  --registry="${NPM_CONFIG_REGISTRY}" \
  --fetch-retries=5 \
  --fetch-retry-mintimeout=20000 \
  --fetch-retry-maxtimeout=120000

FROM node:20-alpine AS builder
WORKDIR /app/frontend
COPY --from=deps /app/frontend/node_modules ./node_modules
COPY frontend ./
ARG NEXT_PUBLIC_API_BASE=/api
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app/frontend
ENV NODE_ENV=production
ENV PORT=3000
COPY --from=builder /app/frontend/.next ./.next
COPY --from=builder /app/frontend/package*.json ./
COPY --from=builder /app/frontend/node_modules ./node_modules
COPY --from=builder /app/frontend/public ./public

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
