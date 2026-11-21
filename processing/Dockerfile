FROM node:24-bookworm-slim AS deps
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY shared/typescript/package.json ./shared/typescript/
COPY processing/package.json ./processing/
RUN npm ci --ignore-scripts -w @svitlo-power/shared-typescript -w svitlo-power-processing

FROM deps AS build
COPY shared/typescript/tsconfig.json shared/typescript/tsconfig.build.json ./shared/typescript/
COPY shared/typescript/src ./shared/typescript/src
COPY processing/tsconfig.json processing/tsconfig.build.json ./processing/
COPY processing/src ./processing/src
# prebuild compiles the shared package first.
RUN npm run build -w svitlo-power-processing

FROM build AS test
WORKDIR /workspace/processing
COPY processing/eslint.config.js ./
COPY processing/test ./test
CMD ["sh", "-c", "npm run lint && npm run format:check && npm test"]

FROM node:24-bookworm-slim AS prod-deps
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY shared/typescript/package.json ./shared/typescript/
COPY processing/package.json ./processing/
RUN npm ci --omit=dev --ignore-scripts -w svitlo-power-processing \
    && mkdir -p processing/node_modules

FROM node:24-bookworm-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
ARG VERSION=0000.00.00
RUN echo "${VERSION}" > /app/VERSION
# Keep the workspace layout so node_modules/@svitlo-power/shared-typescript
# (a symlink to ../../shared/typescript) resolves.
COPY --from=prod-deps --chown=node:node /workspace/node_modules ./node_modules
COPY --from=prod-deps --chown=node:node /workspace/processing/node_modules ./processing/node_modules
COPY --from=build --chown=node:node /workspace/shared/typescript/package.json ./shared/typescript/package.json
COPY --from=build --chown=node:node /workspace/shared/typescript/dist ./shared/typescript/dist
COPY --from=build --chown=node:node /workspace/processing/package.json ./processing/package.json
COPY --from=build --chown=node:node /workspace/processing/dist ./processing/dist
WORKDIR /app/processing
USER node
EXPOSE 8100 9099
CMD ["node", "dist/src/main.js"]