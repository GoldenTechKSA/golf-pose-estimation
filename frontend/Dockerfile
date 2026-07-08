# SwingLens web frontend — multi-stage build to a minimal standalone runtime.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* values are inlined at build time.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S swinglens && adduser -S swinglens -G swinglens
COPY --from=build --chown=swinglens:swinglens /app/.next/standalone ./
COPY --from=build --chown=swinglens:swinglens /app/.next/static ./.next/static
COPY --from=build --chown=swinglens:swinglens /app/public ./public
USER swinglens
EXPOSE 3000
CMD ["node", "server.js"]
