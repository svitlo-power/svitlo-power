# Phase 8 Spec: Separate Public & Admin Applications

## Objective
Split the combined front-end into two separate deployables with host-aware routing, and move public-facing API routes from the legacy back-end to the app back-end.

## Current State
- **Single front-end**: Serves both public pages and admin screens
- **Single back-end**: Serves both public APIs and admin APIs
- **Host**: `svitlo-power.pp.ua` (all traffic)

## Target State
| Host | UI | API |
|------|-----|-----|
| `svitlo-power.pp.ua` | Public front-end | App back-end |
| `admin.svitlo-power.pp.ua` | Admin front-end | Admin back-end |
| Mobile clients | — | App back-end (mobile API) |

## Deliverables

### 1. Front-End Split
**Repository structure** (monorepo or separate repos):
```
svitlo-power-ui/
├── packages/
│   ├── shared/           # Shared components, utilities, types
│   ├── public-app/       # Public front-end (Vite/Next.js)
│   │   ├── src/
│   │   │   ├── pages/    # Public routes only
│   │   │   ├── components/
│   │   │   └── main.tsx
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── admin-app/        # Admin front-end (Vite/Next.js)
│       ├── src/
│       │   ├── pages/    # Admin routes only
│       │   │   ├── dashboard/
│       │   │   ├── sites/
│       │   │   ├── users/
│       │   │   └── settings/
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
- `/` — Landing page
- `/sites/:id` — Public site dashboard
- `/outages` — Public outage schedule
- `/about`, `/contact`, etc.

**Admin routes** (move to admin-app):
- `/admin/*` — All admin screens
- `/admin/dashboard`
- `/admin/sites`
- `/admin/users`
- `/admin/settings`

**Shared components** (in `packages/shared`):
- UI primitives (Button, Card, Table, Chart)
- Auth hooks (useAuth, useUser)
- API client (configured per app)
- Types (DashboardSnapshot, Site, etc.)

### 3. API Route Migration (Legacy Back-end → App Back-end)
**Current public APIs on legacy back-end** (to move):
| Endpoint | Current Host | Target Host |
|----------|--------------|-------------|
| `GET /api/v1/dashboard` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/v1/sites/:id` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/v1/outages/:siteId` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |
| `GET /api/v1/public/*` | `svitlo-power.pp.ua` | `svitlo-power.pp.ua` (app-back-end) |

**Migration steps**:
1. **Duplicate routes** in app-back-end (proxy to Redis snapshot, same as mobile API)
2. **Feature flag**: `PUBLIC_API_VIA_APP_BACKEND` (default: false)
3. **Edge proxy**: Route public host API traffic to app-back-end when flag enabled
4. **Verify**: Contract tests, parity with legacy responses
5. **Cutover**: Enable flag, monitor, remove from legacy back-end

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
        proxy_pass http://app-back-end;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /dashboard/stream {
        # SSE (app back-end)
        proxy_pass http://app-back-end;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_cache off;
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
        # Admin back-end
        proxy_pass http://admin-back-end;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /api/v1/admin/dashboard/stream {
        # SSE (admin back-end)
        proxy_pass http://admin-back-end;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_cache off;
    }
}
```

**Feature flag at edge** (for gradual cutover):
- `X-Public-API-Target: legacy|app-backend` header
- Controlled via edge config (Cloudflare Workers, NGINX map, etc.)

### 5. Authentication Boundaries
**Cookie/Session Separation**:
| App | Cookie Domain | Cookie Name | SameSite |
|-----|---------------|-------------|----------|
| Public | `.svitlo-power.pp.ua` | `public_session` | Lax |
| Admin | `.admin.svitlo-power.pp.ua` | `admin_session` | Lax |
| Mobile | N/A | Bearer token | N/A |

**CORS**:
- Public UI → App back-end: `Origin: https://svitlo-power.pp.ua`
- Admin UI → Admin back-end: `Origin: https://admin.svitlo-power.pp.ua`
- Mobile → App back-end: No CORS (native app)

**OIDC Redirect URIs**:
- Public UI: `https://svitlo-power.pp.ua/callback`
- Admin UI: `https://admin.svitlo-power.pp.ua/callback`
- Mobile: `com.svitlo.power://callback` (custom scheme)

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
- [ ] Remove public routes from legacy back-end

### Step 3: Host Deployment (Week 3-4)
- [ ] Deploy public-app to `svitlo-power.pp.ua`
- [ ] Deploy admin-app to `admin.svitlo-power.pp.ua`
- [ ] Configure edge proxy rules
- [ ] SSL certificates (wildcard or separate)
- [ ] DNS: `admin.svitlo-power.pp.ua` → edge proxy

### Step 4: Authentication Separation (Week 4)
- [ ] Configure separate cookie domains
- [ ] Update OIDC clients with new redirect URIs
- [ ] Test login flows on both hosts
- [ ] Verify no cookie leakage between hosts

### Step 5: Legacy Back-end Restriction (Week 5)
- [ ] Legacy back-end: Remove public routes (already migrated)
- [ ] Legacy back-end: Restrict to admin host only (via edge proxy)
- [ ] Rename: "Legacy back-end" → "Admin back-end" (already done conceptually)
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
| Public login works, cookie scoped | Verified |
| Admin login works, cookie scoped | Verified |
| No shared session between hosts | Verified |
| Mobile login unaffected | Verified |

## Rollback Procedures

### Front-End Rollback
1. Edge proxy: Route both hosts to legacy front-end build
2. Legacy front-end: Still contains both public + admin routes
3. Feature flag: `FRONTEND_SPLIT_ENABLED=false`

### API Rollback
1. Edge proxy: Route public host API to legacy back-end
2. Feature flag: `PUBLIC_API_VIA_APP_BACKEND=false`
3. Legacy back-end: Public routes still exist (not removed until verified)

### Host Rollback
1. DNS: Point `admin.svitlo-power.pp.ua` back to legacy (or disable subdomain)
2. Single host serves both apps (legacy front-end)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Shared component drift | Single package, versioned; CI tests both apps |
| SEO impact (public host) | Same URLs, same content; 301 redirects if any URL changes |
| Mobile app breakage | Mobile API untouched; contract tests in CI |
| Cookie leakage | Separate domains, `SameSite=Lax`, `Secure`, `HttpOnly` |
| Edge proxy misconfiguration | Staging mirror of production edge config; automated tests |

## Test Checklist

- [ ] Unit: Shared components work in both apps
- [ ] Integration: Public app → App back-end API (all endpoints)
- [ ] Integration: Admin app → Admin back-end API (all endpoints)
- [ ] Integration: Mobile app → App back-end API (all endpoints)
- [ ] Contract: Mobile API test suite passes
- [ ] E2E: Public user journey (landing → site dashboard → outage schedule)
- [ ] E2E: Admin user journey (login → dashboard → site management → user management)
- [ ] E2E: Cross-host navigation (public → admin link, admin → public link)
- [ ] Auth: Cookie isolation (login public, open admin → not logged in)
- [ ] Auth: OIDC redirects work on both hosts
- [ ] Load: Public host 10k req/s, Admin host 1k req/s
- [ ] Chaos: App back-end down → public host 503, admin host unaffected
- [ ] Chaos: Admin back-end down → admin host 503, public host unaffected
- [ ] Rollback: Each rollback procedure tested in staging