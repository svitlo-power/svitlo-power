FROM node:22-bookworm-slim AS build

WORKDIR /workspace/app-back-end
COPY app-back-end/package*.json ./
RUN npm ci
COPY app-back-end/tsconfig.json ./
COPY app-back-end/tsconfig.build.json ./
COPY app-back-end/src ./src
COPY app-back-end/test ./test
COPY shared/typescript/package.json /workspace/shared/typescript/package.json
COPY shared/typescript/src /workspace/shared/typescript/src
RUN npm run build
RUN npm prune --omit=dev

FROM node:22-bookworm-slim AS test
WORKDIR /workspace/app-back-end
COPY app-back-end/package*.json ./
RUN npm ci
COPY app-back-end/tsconfig.json ./
COPY app-back-end/eslint.config.js ./
COPY app-back-end/src ./src
COPY app-back-end/test ./test
COPY shared/typescript /workspace/shared/typescript
RUN npm ci --prefix /workspace/shared/typescript
CMD ["sh", "-c", "npm --prefix /workspace/shared/typescript test && npm run lint && npm run format:check && npm test"]

FROM node:22-bookworm-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build --chown=node:node /workspace/app-back-end/node_modules ./node_modules
COPY --from=build --chown=node:node /workspace/app-back-end/dist ./dist
COPY --from=build --chown=node:node /workspace/app-back-end/package.json ./package.json
USER node
EXPOSE 8000 9097
CMD ["node", "dist/app-back-end/src/main.js"]