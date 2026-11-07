# NestJS app-back-end

The mobile BFF is a NestJS service. It has no MongoDB client or database
credentials; dashboard, power-log, outage-schedule, and push operations use the
private `INTERNAL_API_URL` with `INTERNAL_API_TOKEN`. Redis is used only for the
optional dashboard snapshot cache and shared event subscription client.
HTTP logs are structured JSON with request IDs; app/service credentials and
push-device tokens are redacted. Helmet headers and Redis-backed route limits
are enabled by default.

## Structure

- `src/config`: validated, typed environment configuration.
- `src/infrastructure/internal-api`: private domain API client provider.
- `src/infrastructure/redis` and `src/snapshots`: Redis connections and snapshot lifecycle.
- `src/dashboard`, `src/outages-schedule`, `src/push`, and `src/health`: feature controllers, services, DTOs, and modules.
- `src/http`: cross-cutting authentication, exception mapping, and validation.
- `shared/typescript`: framework-independent API contracts and Redis clients.

## Local development

Use the repository-root `.env` and run the service from this directory:

```bash
npm ci
npm run start:dev
```

Set `INTERNAL_API_URL=http://127.0.0.1:5005/internal/v1/app` when the Processing
service is running on the host. Keep `INTERNAL_API_TOKEN` identical to the
Processing service's token. `APP_ACCESS_TOKEN` remains the mobile client's
`X-App-Token`. Redis should be available at `REDIS_URI`; snapshot reads remain
disabled unless the existing publisher and consumer feature flags are enabled.

Run the app tests with `npm test`. Run shared-client tests from the repository root
with `cd shared/typescript && npm ci && npm test`.
Use `npm run lint` and `npm run format:check` before submitting changes. Set
`API_DOCS_ENABLED=true` for a non-production environment to expose Swagger UI at
`/docs` and its OpenAPI document at `/docs/openapi.json`; docs are disabled in
production.

## Rollback

The previous Python implementation and Dockerfile remain in
`app-back-end-legacy`. Build its image with:

```bash
docker build -f app-back-end-legacy/Dockerfile -t svitlo-power-app-back-end-legacy .
```

For a Compose rollback, start the same service name with the legacy override:

```bash
docker compose -f docker-compose.yml -f docker-compose.app-back-end-legacy.yml up -d --build svitlo-power-app-back-end
```

Keep the previous production image and route available until Nest passes
contract, staging, readiness, and cutover checks. The legacy service requires
the existing Mongo configuration and migration service; do not pass those
settings to the Nest service.