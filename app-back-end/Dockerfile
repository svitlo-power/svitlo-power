FROM node:24-bookworm-slim AS deps
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY shared/typescript/package.json ./shared/typescript/
COPY app-back-end/package.json ./app-back-end/
RUN npm ci --ignore-scripts -w @svitlo-power/shared-typescript -w svitlo-power-app-back-end

FROM deps AS build
COPY shared/typescript/tsconfig.json shared/typescript/tsconfig.build.json ./shared/typescript/
COPY shared/typescript/src ./shared/typescript/src
COPY app-back-end/tsconfig.json app-back-end/tsconfig.build.json ./app-back-end/
COPY app-back-end/src ./app-back-end/src
# prebuild compiles the shared package first.
RUN npm run build -w svitlo-power-app-back-end

FROM build AS test
WORKDIR /workspace/app-back-end
COPY app-back-end/eslint.config.js ./
COPY app-back-end/test ./test
CMD ["sh", "-c", "npm run lint && npm run format:check && npm test"]

FROM node:24-bookworm-slim AS prod-deps
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY shared/typescript/package.json ./shared/typescript/
COPY app-back-end/package.json ./app-back-end/
RUN npm ci --omit=dev --ignore-scripts -w svitlo-power-app-back-end \
    && mkdir -p app-back-end/node_modules

FROM node:24-bookworm-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
ARG VERSION=0000.00.00
RUN echo "${VERSION}" > /app/VERSION
# Keep the workspace layout so node_modules/@svitlo-power/shared-typescript
# (a symlink to ../../shared/typescript) resolves.
COPY --from=prod-deps --chown=node:node /workspace/node_modules ./node_modules
COPY --from=prod-deps --chown=node:node /workspace/app-back-end/node_modules ./app-back-end/node_modules
COPY --from=build --chown=node:node /workspace/shared/typescript/package.json ./shared/typescript/package.json
COPY --from=build --chown=node:node /workspace/shared/typescript/dist ./shared/typescript/dist
COPY --from=build --chown=node:node /workspace/app-back-end/package.json ./app-back-end/package.json
COPY --from=build --chown=node:node /workspace/app-back-end/dist ./app-back-end/dist
WORKDIR /app/app-back-end
USER node
EXPOSE 8000 9097
CMD ["node", "dist/src/main.js"]
