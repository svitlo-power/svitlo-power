# Phase 7 Spec: Identity Boundary Migration

## Objective
Introduce a dedicated Identity Service (OIDC provider) while preserving existing login behavior, then migrate **admin** clients to the new issuer. **Public web and mobile remain anonymous** — no login migration needed for them. Run in parallel with dashboard/processing migration.

## Current State
- **Admin auth**: JWT access/refresh tokens issued by `back-end` (`/api/auth/login`)
- **Public web**: Anonymous (no login)
- **Mobile (Android)**: Anonymous, uses static `X-App-Token` header
- **User store**: MongoDB `users` collection (mixed identity + domain data)
- **Admin UI**: Uses JWT tokens from `back-end`

## Target State
- **Identity Service**: NestJS + `oidc-provider` (panva) — standards-compliant OIDC provider
- **Identity store**: MongoDB (same deployment, separate collections, restricted credentials)
- **Domain users**: Owned by Processor (profiles, permissions, bindings)
- **Admin BFF**: Validates tokens with Identity Service, exchanges for Processor-audience tokens
- **Public/Mobile**: Unchanged (anonymous, `X-App-Token`)

## Architecture

```
┌─────────────┐     OIDC / OAuth2      ┌──────────────────┐
│  Admin UI   │───────────────────────►│                  │
│  (browser)  │◄───────────────────────│  Identity        │
└─────────────┘   Authorization Code   │  Service         │
         │                              │  (NestJS +       │
         │                              │   oidc-provider) │
         │                              │                  │
         │                              │  - Credentials   │
         │                              │  - Login/MFA     │
         │                              │  - Token issuance│
         │                              │  - Session mgmt  │
         │                              │  - Password reset│
         │                              └────────┬─────────┘
         │                                       │ Token Exchange
         ▼                                       ▼
┌─────────────┐     Service-to-Service    ┌──────────────────┐
│  Admin BFF  │──────────────────────────►│                  │
│  (back-end) │◄──────────────────────────│  Processor       │
└─────────────┘   (mTLS + User Token)     │  (validates      │
                                          │   user token)    │
                                          └──────────────────┘
```

**Public/Mobile**: No change — continue using `X-App-Token` / anonymous access.

## Deliverables

### 1. Identity Service (NestJS)
**Stack**: NestJS + `oidc-provider` (panva) — **not** `openid-client` (that's a relying-party library)

**Features**:
- Authorization Code Flow + PKCE (for admin UI)
- Client Credentials Flow (service-to-service)
- Token Exchange (RFC 8693) — BFF exchanges user token for Processor-audience token
- MFA (TOTP, WebAuthn)
- Password reset (email)
- Session management (refresh tokens, revocation)
- Admin API for user management (scoped to identity data only)

**Data Model** (MongoDB, separate collections):
```typescript
// Identity-owned collections (credentials restricted)
interface IdentityUser {
  _id: ObjectId;
  sub: string;                    // Stable, immutable (UUID)
  email: string;                  // Unique, verified
  emailVerified: boolean;
  passwordHash: string;           // Argon2id
  mfa: { totp?: string; webauthn?: WebAuthnCredential[] };
  createdAt: Date;
  updatedAt: Date;
  lastLoginAt?: Date;
}

interface Client {
  _id: ObjectId;
  clientId: string;
  clientSecretHash: string;       // For confidential clients
  redirectUris: string[];
  grantTypes: string[];           // ['authorization_code', 'client_credentials', 'urn:ietf:params:oauth:grant-type:token-exchange']
  responseTypes: string[];        // ['code']
  scope: string;                  // 'openid profile email offline_access'
  audience: string[];             // ['processor', 'admin-bff']
  isFirstParty: boolean;          // True for our UIs
}
```

### 2. Token Exchange Flow
**Admin BFF → Identity Service**:
```
POST /token
Authorization: Basic <bff-client-id:secret>
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&subject_token=<user-access-token>
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&requested_token_type=urn:ietf:params:oauth:token-type:access_token
&audience=processor
&scope=domain:read domain:write
```

**Response**:
```json
{
  "access_token": "eyJ...",  // JWT, audience=processor, sub=user-sub
  "token_type": "Bearer",
  "expires_in": 300
}
```

### 3. Processor Token Validation
- Validates JWT: signature (JWKS from Identity), `aud=processor`, `exp`, `iss`
- Extracts `sub` → maps to domain user via `IdentityBinding` collection
- Checks domain permissions for requested operation

### 4. Identity Binding (Processor-Owned)
```typescript
interface IdentityBinding {
  _id: ObjectId;
  identitySub: string;          // Links to Identity Service user
  domainUserId: string;         // Processor's domain user ID
  roles: string[];              // ['admin', 'reporter', 'viewer']
  buildingAccess: string[];     // Building IDs user can access
  createdAt: Date;
  updatedAt: Date;
}
```
- **Identity Service**: Never writes here (read-only access if needed for admin UI)
- **Processor**: Sole writer; creates binding on first admin login or admin invitation

### 5. Client Migration Strategy (Admin Only)

#### Phase 7a: Deploy Identity Service (Parallel)
- Deploy alongside legacy auth
- Create clients: `admin-ui`, `admin-bff`, `processor`
- **No public/mobile clients** — they stay anonymous
- Migrate **internal/admin users first** (lowest risk)
- Legacy auth remains for admin UI during transition

#### Phase 7b: Admin UI Migration
1. Admin UI → Identity Service (Authorization Code + PKCE)
2. Admin BFF validates token with Identity (introspection or JWKS)
3. Admin BFF exchanges token for Processor audience
4. Feature flag: `ADMIN_UI_OIDC_ENABLED`

#### Phase 7c: Legacy Admin Auth Deprecation
- Legacy JWT/session validation remains in BFF during migration
- BFFs accept both legacy and OIDC tokens (distinguish by `iss` claim)
- After 100% admin migration + 2-week observation: remove legacy validation

## Migration Steps (Detailed)

### Step 1: Identity Service Deploy (Week 1-2)
- [ ] NestJS project with `oidc-provider`
- [ ] MongoDB collections + restricted credentials
- [ ] Client registration (3 clients: admin-ui, admin-bff, processor)
- [ ] JWKS endpoint (`/.well-known/jwks.json`)
- [ ] Discovery endpoint (`/.well-known/openid-configuration`)
- [ ] Health checks, metrics, logging
- [ ] Staging deploy, smoke tests

### Step 2: Admin User Migration (Week 3)
- [ ] Create Identity users for existing admins (script: `email` → `sub`, temp password)
- [ ] Admin UI: Add "Login with OIDC" button (alongside legacy)
- [ ] Admin BFF: Accept OIDC tokens, exchange for Processor
- [ ] Shadow: Both auth paths work, compare user resolution
- [ ] Cutover: Admin UI defaults to OIDC, legacy hidden
- [ ] Rollback: Legacy login re-enabled

### Step 3: Legacy Removal (Week 4+)
- [ ] 2-week observation at 100% OIDC for admin
- [ ] Remove legacy token validation from Admin BFF
- [ ] Remove legacy login endpoints from back-end
- [ ] Remove legacy user session code

## Exit Gates

### Phase 7a (Identity Service Deployed)
| Criterion | Threshold |
|-----------|-----------|
| OIDC discovery + JWKS accessible | 100% |
| Token issuance (all flows) | Works in staging |
| Token exchange (Admin BFF → Processor) | Works in staging |
| MFA enrollment + challenge | Works |
| Password reset flow | Works |
| Admin API (user CRUD) | Works |
| Load test: 100 auth req/s | p99 < 200ms |

### Phase 7b (Admin Migrated)
| Criterion | Threshold |
|-----------|-----------|
| Admin login success rate | ≥ 99.9% |
| Token exchange success rate | 100% |
| Processor validates user tokens | 100% |
| Admin UI flows (all) | Work end-to-end |
| Rollback tested | < 2 min |

### Phase 7c (Legacy Removed)
| Criterion | Threshold |
|-----------|-----------|
| 0 legacy token validations in logs | 14 days |
| All admin clients on OIDC | 100% |
| Identity Service HA | 2+ replicas, multi-AZ |

## Rollback Procedures

### Admin Rollback
1. Feature flag: `ADMIN_UI_OIDC_ENABLED=false`
2. UI reverts to legacy login form
3. BFF accepts legacy tokens
4. Identity Service remains running

### Full Rollback (Emergency)
1. Admin flag `false`
2. Legacy auth fully active
3. Identity Service scaled to 0 (optional)
4. **Account mappings preserved** — `IdentityBinding` links `sub` to domain user
5. Re-migrate later with same `sub` values

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OIDC library vulnerabilities | Use maintained library (`oidc-provider`); Dependabot; security scanning |
| Token exchange complexity | Start with simpler: Admin BFF validates user token directly (JWKS), adds `X-User-Sub` header to Processor calls; migrate to token exchange later |
| Sub mismatch (legacy vs OIDC) | Migration script: legacy `userId` → OIDC `sub` mapping stored; Processor uses `sub` consistently |
| Session fixation | PKCE for admin client; short access tokens (5 min); refresh token rotation |
| Identity Service downtime | 2+ replicas; health checks; BFFs cache JWKS (5 min TTL); graceful degradation |
| Public/mobile auth | **No change** — they remain anonymous with `X-App-Token` |

## Test Checklist

- [ ] Unit: Identity Service issues valid tokens (all flows)
- [ ] Unit: Token exchange returns Processor-audience token
- [ ] Unit: Processor validates token, maps `sub` to domain user
- [ ] Integration: Admin UI → Identity → Admin BFF → Processor
- [ ] Contract: OpenID Connect certification tests (if applicable)
- [ ] Load: 100 concurrent auth flows, p99 < 200ms
- [ ] Chaos: Identity Service down → BFFs use cached JWKS, return 503 for new logins
- [ ] Security: Penetration test on auth flows
- [ ] Migration: Legacy admin user → OIDC user mapping verified
- [ ] Rollback: Admin flag tested, legacy path works
- [ ] Verify: Public/mobile unchanged (anonymous, X-App-Token)