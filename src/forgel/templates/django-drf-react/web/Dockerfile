# Build the React SPA with esbuild, then serve the bundle from nginx, which
# also proxies /healthz to the api service (see nginx.conf).
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json /app/package.json
RUN npm install --no-audit --no-fund

COPY index.html /app/index.html
COPY src /app/src
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
