# Internal App API v1

The Processing/back-end service owns this HTTP contract for the database-free NestJS app BFF. It does not change public mobile routes. The Redis snapshot remains an optional dashboard/outage read optimization; it is not a substitute for power logs or push operations.

## Access and deployment

All operations below use the prefix `/internal/v1/app` and require `Authorization: Bearer <service-token>`. Configure a long, randomly generated `INTERNAL_API_TOKEN` on back-end and provide the same secret to the consumer through a separate secret mechanism. An empty or missing token disables the API with `503`; incorrect or absent credentials return `401`. Do not reuse `APP_ACCESS_TOKEN`, the JWT secret, or an FCM device token. Rotate the secret on both sides together. Never include tokens in URLs or logs.

For Compose, back-end receives `INTERNAL_API_TOKEN` and optionally `INTERNAL_API_TIMEOUT_SECONDS` through its `.env` file. The consumer can reach `http://svitlo-power-back-end:5005/internal/v1/app` on `web_network`. The existing front-end nginx proxies `/api` only, and the back-end HTTP port is not published to the host by the supplied Compose file. This is network isolation from external clients, not isolation from other containers on `web_network`: restrict access using deployment networking and do not proxy `/internal` through a public gateway. Use TLS or mTLS when traffic leaves a trusted host/network.

For local development, set `INTERNAL_API_TOKEN` in the back-end environment or root `.env`, start back-end, and point a local consumer to `http://127.0.0.1:5005/internal/v1/app` when back-end listens there. Supply the token separately to the consumer. Use distinct secrets and Mongo credentials per environment.

The NestJS app-back-end receives only its required settings through Compose, including the internal API URL and service token; it must not receive Mongo credentials or use `env_file: .env`. The retained Python rollback implementation is isolated in `app-back-end-legacy` and still requires the legacy Mongo configuration and migration dependency. Local development may load the repository-root `.env`, but only the Nest service's explicitly named settings are consumed.

The older `/internal/v1/snapshots/refresh` is a separate API, currently protected by network segmentation rather than this bearer token. Existing snapshot clients are unchanged. Keep it private as well.

## Operations

IDs are opaque strings on the wire, currently validated as 24-character hexadecimal IDs for compatibility with existing clients. All JSON request and response fields use the camelCase names in the service's OpenAPI schema. `GET /openapi.json` on back-end provides the complete request and response schemas; access it only on a trusted network.

| Mobile operation | Method and internal path | Contract |
| --- | --- | --- |
| List buildings | `GET /dashboard/buildings` | Enabled buildings: `id`, localized `name`, `color`, `hasBoundStation`, `order`. |
| Building summaries | `POST /dashboard/buildings/summary` | Body `{"buildingIds":["<id>"]}`; returns summaries for matching buildings. |
| Buildings with summaries | `GET /dashboard/buildings-with-summary` | Combined building and summary fields. |
| Dashboard configuration | `GET /dashboard/config` | Localized `title` and nested `outagesSchedule` with `enable`, `regionId`, `dsoId`, `queue`. The BFF maps this to its legacy flat `enableOutagesSchedule` and `outagesScheduleQueue` fields. |
| Building power logs | `POST /dashboard/buildings/{building_id}/power-logs` | Body `{"startDate":"<ISO-8601>","endDate":"<ISO-8601>"}`; returns periods and duration totals. Naive times are UTC; start must precede end. No data returns `404`, matching the current mobile route. |
| Outage schedule | `GET /outages-schedule/{queue}` | Unwrapped schedule containing `days` and `updatedOn`; unknown queue returns `404`. |
| Register/refresh device | `POST /push/devices` | Body: nonempty `token`, `platform`, optional `language` and `appVersion`. Returns device state without the FCM token. |
| Get current device | `POST /push/devices/current` | Body `{"token":"<device-token>"}`; unknown device returns `404`. |
| Update subscriptions | `POST /push/devices/subscriptions` | Body: `token`, optional `enabled`, `disabledTopics`, `buildings`; unknown device returns `404`. |
| Unregister device | `POST /push/devices/unregister` | Body `{"token":"<device-token>"}`; returns `{"success":true}` even if already absent. |
| List push topics | `GET /push/topics` | Enabled topics with `key`, localized `name` and `description`. |
| API liveness | `GET /health` | Returns `{"status":"ok"}` after authentication; does not check dependencies. |
| API readiness | `GET /ready` | Checks MongoDB and Redis. `200` with `{"status":"ready","checks":{"mongodb":"healthy","redis":"healthy"}}`, otherwise `503` with `"status":"not_ready"`. Only per-dependency status is returned, never error messages. |

Summary and combined-building responses include the existing mobile fields such as `isGridAvailable`, `batteryPercent`, `consumptionPower` and `chargeSource`. The BFF retains current public route aliases, `X-App-Token` authentication, and response mapping. Snapshot reads may still be used by the BFF, but missing snapshots or unsupported operations use the appropriate domain operation instead of direct MongoDB access.

## Errors and timeouts

Errors use FastAPI's JSON `detail` field. Invalid date ranges or dates return `400`; invalid request shapes, identifiers, or platform values return `422`. Missing schedules, devices, or power logs return `404`. Missing/invalid service credentials return `401`; an unconfigured service token or a failed dependency returns `503`; a dependency timeout returns `504`. These dependency errors do not expose exception details.

`INTERNAL_API_TIMEOUT_SECONDS` limits each domain-service call and defaults to 10 seconds. The BFF client uses a bounded overall timeout slightly longer than the service limit, handles connection failures and `503`/`504`, and does not retry writes automatically. A timeout does not guarantee a write was rolled back; reconcile device state before retrying an uncertain mutation.

Use the authenticated `/internal/v1/app/health` for liveness and `/internal/v1/app/ready` for consumer readiness: the BFF should report itself not ready while back-end's `/ready` returns `503` or cannot be reached. `/ready` reuses back-end's registered MongoDB and Redis health checks and is bounded by `INTERNAL_API_TIMEOUT_SECONDS`. Prometheus on back-end port `9096` exposes `internal_app_dependency_calls_total` by fixed operation name and outcome (`success`, `error`, `timeout`) and `internal_app_dependency_duration_seconds`. A successful service call can still lead to an HTTP `404` when its result is absent. Failure logs include the operation and exception type, not request payloads or credentials.

## Verification

Run the back-end contract suite from `back-end`:

```bash
python -m pytest tests/app/routes/test_internal_app.py -q
```

The machine-readable contract is [`back-end/contracts/internal-app-api.v1.openapi.json`](../../back-end/contracts/internal-app-api.v1.openapi.json): the OpenAPI paths under `/internal/v1/app` and every schema they reference. Consumers can generate their TypeScript client from it. The suite fails when the generated schema drifts from this file, including through changes to shared API models. After an intentional, coordinated change, regenerate it:

```bash
UPDATE_INTERNAL_API_CONTRACT=1 python -m pytest tests/app/routes/test_internal_app.py -q
```

Breaking changes require a new version prefix rather than editing v1 in place.

The suite covers authentication for every domain route, readiness, successful contracts, validation, not-found, dependency failure and timeout, and registration with the real service container. It uses mocked domain dependencies; deployment/network isolation and end-to-end Mongo/Redis behavior still require an environment-level test. The BFF contract tests are in `app-back-end/test`; production cutover and rollback remain environment-level checks.