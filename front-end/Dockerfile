FROM node:latest AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . ./
COPY --from=shared i18n /shared/i18n

RUN npm run build

FROM nginx:latest

COPY --from=build /app/dist /var/www/front-end
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-site.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
