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
ENV VERSION=${VERSION}
RUN mkdir -p /var/www/front-end && echo "${VERSION}" > /var/www/front-end/VERSION

# Install gettext for envsubst
RUN apt-get update && apt-get install -y gettext-base && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/dist /var/www/front-end
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-site.conf.template /etc/nginx/conf.d/default.conf.template
COPY docker-entrypoint/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-runtime-config.sh \
    && chmod +x /docker-entrypoint.d/40-runtime-config.sh

CMD ["nginx", "-g", "daemon off;"]