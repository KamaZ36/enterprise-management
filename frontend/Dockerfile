# syntax=docker/dockerfile:1

FROM node:24-alpine AS build

ENV CI=1

RUN npm install -g pnpm@12.10.1

WORKDIR /app

# Сначала манифесты: слой установки переиспользуется, пока не менялся lock-файл.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps ./apps

RUN pnpm install --frozen-lockfile

# Публичные адреса вшиваются в статику на этапе сборки.
ARG NUXT_PUBLIC_CAFE_APP_URL=""
ARG NUXT_PUBLIC_LANDING_URL=""
ENV NUXT_PUBLIC_CAFE_APP_URL=$NUXT_PUBLIC_CAFE_APP_URL \
    NUXT_PUBLIC_LANDING_URL=$NUXT_PUBLIC_LANDING_URL

RUN pnpm --filter @md/admin exec nuxt generate \
    && pnpm --filter @md/cafe exec nuxt generate \
    && pnpm --filter @md/landing exec nuxt generate

FROM caddy:2-alpine AS runtime

COPY --from=build /app/apps/landing/.output/public /srv/landing
COPY --from=build /app/apps/admin/.output/public /srv/admin
COPY --from=build /app/apps/cafe/.output/public /srv/cafe
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80 443
