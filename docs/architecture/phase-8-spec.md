# Phase 8 Spec: Separate Public & Admin Applications

## Objective
Split the combined front-end into two separate deployables with host-aware routing, and move public-facing API routes from the `back-end` to the `app-back-end`.

## Current State
- **Single front-end**: Serves both public pages (`/`, `/app`, `/privacy-policy`) and admin screens (`/stations`, `/buildings`, `/users`, etc.)
- **Single back-end**: `back-end` serves both public APIs (buildings, outages) and admin APIs
- **Host**: `svitlo-power.pp.ua` (all traffic)

## Target State
| Host | UI | API |
|------|-----|-----|
| `svitlo-power.pp.ua` | Public front-end | App back-end |
| `admin.svitlo-power.pp.ua` | Admin front-end | Back-end (renamed to admin-back-end) |
| Mobile clients | — | App back-end (mobile API) |

## Deliverables

### 1. Front-End Split
**Repository structure** (monorepo):
```
svitlo-power-ui/
├── packages/
│   ├── shared/           # Shared components, utilities, types
│   ├── public-app/       # Public front-end (Vite/React)
│   │   ├── src/
│   │   │   ├── pages/    # Public routes only: /, /app, /privacy-policy
│   │   │   ├── components/
│   │   │   └── main.tsx
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── admin-app/        # Admin front-end (Vite/React)
│       ├── src/
│       │   ├── pages/    # Admin routes only: /stations, /buildings, /users, /messages, /chats, /ext-data, /ext-devices, /push, /settings
│       │   ├── components/
│       │   └── main.tsx
│       ├── package.json
│       └── vite.config.ts
├── package.json          # Workspace root
└── turbo.json            # Turborepo config (if used)
```

**Build outputs**:
- `public-app/dist/` → deployed to `svitlo-power.pp.ua`
- `admin-app/dist/` → deployed to `admin.svitlo-power.pp.ua`

### 2. Route Separation
**Public routes** (move to public-app):
- `/` — Landing page (shows `BuildingsPage` for anonymous users)
- `/app` — App landing page
- `/privacy-policy` — Privacy policy

**Admin routes** (move to admin-app):
- `/stations` — Stations page
- `/stations/details/:stationId` — Station details
- `/bots` — Bots page
- `/chats` — Chats page
- `/messages` — Messages page
- `/messages/edit/:messageId` — Message edit
- `/messages/create` — Message create
- `/ext-data` — External data page
- `/users` — Users page
- `/buildings` — Buildings page
- `/ext-devices` — External devices page
- `/push` — Push notifications page
- `/settings` — System settings page
- `/changePassword` — Change password (anonymous layout)
- `/login` — Login (anonymous layout)

**Shared components** (in `packages/shared`):
- UI primitives (Button, Card, Table, Chart)
- Auth hooks (useAuth, useUser)
- API client (configured per app)
- Types (DashboardSnapshot, Building, etc.)

### 3. API Route Migration (Back-end → App-back-end)
**Current public APIs on `back-end`** (to move for public host):
| Endpoint | Current Host | Target Host |
|----------|--------------|-------------|
| `GET /api/dashboard/buildings` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `POST /api/dashboard/buildings/summary` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/buildings/buildings` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/dashboard/config` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/buildings/dashboardConfig` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `POST /api/dashboard/buildings/{building_id}/power-logs` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `POST /api/buildings/{building_id}/power-logs` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/outagesSchedule/outagesSchedule/{queue}` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/events` (SSE) | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |

**Important**: The admin Buildings page calls `GET /api/dashboard/buildings` and `POST /api/dashboard/buildings/summary` on the **admin host**. These endpoints **stay on `back-end`** for the admin host. Only public-host traffic is routed to `app-back-end`.

**Migration steps**:
1. **Duplicate routes** in `app-back-end` (read from Redis snapshot, same as mobile API)
2. **Feature flag**: `PUBLIC_API_VIA_APP_BACKEND` (default: false)
3. **Edge proxy**: Route **public host** API traffic to `app-back-end` when flag enabled
4. **Verify**: Contract tests, parity with legacy responses
5. **Cutover**: Enable flag, monitor, **stop routing public-host traffic to `back-end`** (do not remove routes from `back-end` — they remain for admin host)

### 4. Edge Proxy Configuration
**NGINX / Cloudflare / AWS ALB** rules:
```nginx
# Public host
server {
    server_name svitlo-power.pp.ua;
    
    location / {
        # Static files (public-app)
        root /var/www/public-app;
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        # App back-end
        proxy_pass http://svitlo-power-app-back-end:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
    
    location /api/events {
        # SSE (app back-end)
        proxy_pass http://svitlo-power-app-back-end:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_cache off;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}

# Admin host
server {
    server_name admin.svitlo-power.pp.ua;
    
    location / {
        # Static files (admin-app)
        root /var/www/admin-app;
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        # Admin back-end (back-end service)
        proxy_pass http://svitlo-power-back-end:5005;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
    
    location /api/events {
        # SSE (admin back-end)
        proxy_pass http://svitlo-power-back-end:5005;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_cache off;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

> **Note**: Upstream names match `docker-compose.yml` service names (`svitlo-power-app-back-end`, `svitlo-power-back-end`). Ports: app-back-end=8000, back-end=5005.

**Feature flag at edge** (for gradual cutover):
- `X-Public-API-Target: legacy|app-backend` header
- Controlled via edge config (Cloudflare Workers, NGINX map, etc.)

### 5. Authentication Boundaries
**Current Auth**:
- Admin: JWT access/refresh tokens from `back-end` `/api/auth/login`
- Public: Anonymous (no auth)
- Mobile: Static `X-App-Token` header

**Phase 8 Changes**:
- **Admin host**: Uses Identity Service (OIDC) after Phase 7 — cookies/tokens scoped to `admin.svitlo-power.pp.ua`
- **Public host**: Remains anonymous — no cookies, no auth
- **Mobile**: Unchanged — `X-App-Token` header to `app-back-end`

**Cookie/Session Separation** (after Phase 7):
| App | Cookie Domain | Cookie Name | SameSite |
|-----|---------------|-------------|----------|
| Admin | `admin.svitlo-power.pp.ua` (host-only, no Domain attr) | `admin_session` | Lax |
| Public | None (anonymous) | N/A | N/A |
| Mobile | N/A | Bearer token | N/A |

**CORS**:
- Public UI → App back-end: `Origin: https://svitlo-power.pp.ua`
- Admin UI → Admin back-end: `Origin: https://admin.svitlo-power.pp.ua`
- Mobile → App back-end: No CORS (native app)

**OIDC Redirect URIs** (after Phase 7):
- Admin UI: `https://admin.svitlo-power.pp.ua/callback`
- Public UI: N/A (anonymous)
- Mobile: N/A (uses `X-App-Token`)

### 6. Mobile API Contract Preservation
- **No changes** to mobile API endpoints, request/response shapes
- App back-end continues serving mobile API at same paths
- Versioning: `Accept: application/vnd.svitlo.v1+json` header (if needed)

## Migration Steps

### Step 1: Front-End Split (Week 1-2)
- [ ] Create monorepo structure with shared package
- [ ] Move public pages to public-app, admin pages to admin-app
- [ ] Configure builds, verify both apps work locally
- [ ] Shared components extracted, tested
- [ ] CI/CD: Separate build + deploy pipelines

### Step 2: API Route Migration (Week 2-3)
- [ ] Implement public API routes in app-back-end (read from Redis)
- [ ] Contract tests: app-back-end responses match legacy
- [ ] Feature flag + edge proxy routing
- [ ] Shadow: Dual serve, compare responses
- [ ] Cutover: Enable flag, monitor 24h
- [ ] Remove public routes from back-end

### Step 3: Host Deployment (Week 3-4)
- [ ] Deploy public-app to `svitlo-power.pp.ua`
- [ ] Deploy admin-app to `admin.svitlo-power.pp.ua`
- [ ] Configure edge proxy rules
- [ ] SSL certificates (wildcard or separate)
- [ ] DNS: `admin.svitlo-power.pp.ua` → edge proxy

### Step 4: Authentication Separation (Week 4, after Phase 7)
- [ ] Configure admin cookie domain (host-only, no parent domain)
- [ ] Update OIDC clients with new redirect URIs
- [ ] Test admin login on admin host
- [ ] Verify public host remains anonymous

### Step 5: Back-end Restriction (Week 5)
- [ ] Back-end: Remove public routes (already migrated)
- [ ] Back-end: Restrict to admin host only (via edge proxy)
- [ ] Rename: "Back-end" → "Admin back-end" (conceptually)
- [ ] Verify: No public traffic reaches admin back-end

## Exit Gates

### Front-End Split
| Criterion | Threshold |
|-----------|-----------|
| Public app builds, all pages render | 100% |
| Admin app builds, all screens render | 100% |
| Shared components: 0 breaking changes | Verified |
| Bundle size: Public < 500KB, Admin < 1MB | gzipped |

### API Migration
| Criterion | Threshold |
|-----------|-----------|
| Contract test parity (app-back-end vs legacy) | 100% |
| Shadow parity (production, 24h) | ≥ 99.99% |
| Mobile API unchanged | Contract tests pass |
| Legacy public routes removed | 0 traffic |

### Host Deployment
| Criterion | Threshold |
|-----------|-----------|
| Public host serves public app | 100% |
| Admin host serves admin app | 100% |
| No cross-host route leakage | Verified |
| SSE works on both hosts | Verified |

### Auth Separation
| Criterion | Threshold |
|-----------|-----------|
| Admin login works, cookie scoped to admin host | Verified |
| Public host remains anonymous | Verified |
| Mobile login unaffected (X-App-Token) | Verified |
| No shared session between hosts | Verified |

## Rollback Procedures

### Front-End Rollback
1. Edge proxy: Route both hosts to legacy front-end build
2. Legacy front-end: Still contains both public + admin routes
3. Feature flag: `FRONTEND_SPLIT_ENABLED=false`

### API Rollback
1. Edge proxy: Route public host API to back-end
2. Feature flag: `PUBLIC_API_VIA_APP_BACKEND=false`
3. Back-end: Public routes still exist (not removed until verified)

### Host Rollback
1. DNS: Point `admin.svitlo-power.pp.ua` back to legacy (or disable subdomain)
2. Single host serves both apps (legacy front-end)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Shared component drift | Single package, versioned; CI tests both apps |
| SEO impact (public host) | Same URLs, same content; 301 redirects if any URL changes |
| Mobile app breakage | Mobile API untouched; contract tests in CI |
| Cookie leakage | Admin cookie host-only (no Domain attr), `SameSite=Lax`, `Secure`, `HttpOnly` |
| Edge proxy misconfiguration | Staging mirror of production edge config; automated tests |

## Test Checklist

- [ ] Unit: Shared components work in both apps
- [ ] Integration: Public app → App back-end API (all endpoints)
- [ ] Integration: Admin app → Admin back-end API (all endpoints)
- [ ] Integration: Mobile app → App back-end API (all endpoints)
- [ ] Contract: Mobile API test suite passes
- [ ] E2E: Public user journey (landing → buildings → outage schedule)
- [ ] E2E: Admin user journey (login → dashboard → stations → buildings → users)
- [ ] E2E: Cross-host navigation (public → admin link, admin → public link)
- [ ] Auth: Admin cookie isolation (login admin, open public → not logged in)
- [ ] Auth: OIDC redirects work on admin host
- [ ] Load: Public host 10k req/s, Admin host 1k req/s
- [ ] Chaos: App back-end down → public host 503, admin host unaffected
- [ ] Chaos: Admin back-end down → admin host 503, public host unaffected
- [ ] Rollback: Each rollback procedure tested in staging