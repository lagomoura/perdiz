FROM node:20-alpine AS build
WORKDIR /repo

COPY package.json package-lock.json* ./
COPY apps/web/package.json ./apps/web/
COPY packages/api-client/package.json ./packages/api-client/
RUN npm ci --workspaces --include-workspace-root

COPY packages/api-client ./packages/api-client
COPY apps/web ./apps/web
ARG VITE_API_BASE_URL=https://api.perdiz.local/v1
ARG VITE_APP_ENV=production
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_ENV=$VITE_APP_ENV
RUN npm --workspace apps/web run build

FROM alpine:3.19 AS final
COPY --from=build /repo/apps/web/dist /srv/web
