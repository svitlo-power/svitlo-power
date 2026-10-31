FROM node:latest AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . ./
COPY --from=shared i18n /shared/i18n

RUN npm run build

FROM nginx:latest

# Version argument (injected at build time)
ARG VERSION=0000.00.00
RUN mkdir -p /var/www/front-end && echo "${VERSION}" > /var/www/front-end/VERSION

# Install gettext for envsubst
RUN apt-get update && apt-get install -y gettext-base && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/dist /var/www/front-end
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-site.conf /etc/nginx/conf.d/default.conf.template

# Use envsubst to substitute VERSION in nginx config
CMD envsubst '${VERSION}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g "daemon off;"