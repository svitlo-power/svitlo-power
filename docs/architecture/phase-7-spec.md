# Phase 7 Spec: Identity Boundary Migration

## Objective
Introduce a dedicated Identity Service (OIDC provider) while preserving existing login behavior, then migrate all clients (admin, public, mobile) to the new issuer. Run in parallel with dashboard/processing migration.

## Current State
- **Legacy auth**: Session-based (cookie) or JWT issued by back-end
- **User store**: MongoDB `users` collection (mixed identity + domain data)
- **Admin/public/mobile**: All use same auth mechanism

## Target State
- **Identity Service**: NestJS + standards-compliant OIDC library (e.g., `openid-client`, `oidc-provider`)
- **Identity store**: MongoDB (same deployment, separate collections, restricted credentials)
- **Domain users**: Owned by Processor (profiles, permissions, bindings)
- **BFFs**: Validate tokens with Identity Service, exchange for Processor-audience tokens

## Architecture

```
┌─────────────┐     OIDC / OAuth2      ┌──────────────────┐
│  Admin UI   │───────────────────────►│                  │
│  (browser)  │◄───────────────────────│  Identity        │
└─────────────┘   Authorization Code   │  Service         │
         │                             │  (NestJS +       │
         │                             │   OIDC lib)      │
┌─────────────┐                        │                  │
│  Public UI  │───────────────────────►│  - Credentials   │
│  (browser)  │◄───────────────────────│  - Login/MFA     │
└─────────────┘   Authorization Code   │  - Token issuance│
         │                             │  - Session mgmt  │
┌─────────────┐                        │  - Password reset│
│  Mobile App │───────────────────────►│                  │
│  (native)   │◄───────────────────────└────────┬─────────┘
└─────────────┘                                   │
                                                  │ Token Exchange
                                                  ▼
┌─────────────┐     Service-to-Service    ┌──────────────────┐
│  Admin BFF  │──────────────────────────►│                  │
│  App BFF    │◄──────────────────────────│  Processor       │
└─────────────┘   (mTLS + User Token)     │  (validates      │
                                          │   user token)    │
                                          └──────────────────┘
```

## Deliverables

### 1. Identity Service (NestJS)
**Stack**: NestJS + `@node-oidc/provider` (or `openid-client` + custom implementation)

**Features**:
- Authorization Code Flow + PKCE (public clients)
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
  audience: string[];             // ['processor', 'admin-bff', 'app-bff']
  isFirstParty: boolean;          // True for our UIs
}
```

### 2. Token Exchange Flow
**BFF → Identity Service**:
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
  siteAccess: string[];         // Site IDs user can access
  createdAt: Date;
  updatedAt: Date;
}
```
- **Identity Service**: Never writes here (read-only access if needed for admin UI)
- **Processor**: Sole writer; creates binding on first login or admin invitation

### 5. Client Migration Strategy

#### Phase 7a: Deploy Identity Service (Parallel)
- Deploy alongside legacy auth
- Create clients: `admin-ui`, `public-ui`, `mobile-app`, `admin-bff`, `app-bff`, `processor`
- Migrate **internal/admin users first** (lowest risk)
- Legacy auth remains for public/mobile

#### Phase 7b: Admin UI Migration
1. Admin UI → Identity Service (Authorization Code + PKCE)
2. Admin BFF validates token with Identity (introspection or JWKS)
3. Admin BFF exchanges token for Processor audience
4. Feature flag: `ADMIN_UI_OIDC_ENABLED`

#### Phase 7c: Public UI Migration
1. Public UI → Identity Service (Authorization Code + PKCE)
2. App BFF validates token, exchanges for Processor audience
3. Feature flag: `PUBLIC_UI_OIDC_ENABLED`
4. **Cookie domain**: Separate from admin (no shared session)

#### Phase 7d: Mobile App Migration
1. Mobile app → Identity Service (Authorization Code + PKCE, no secret)
2. App BFF validates token (same as public)
3. **App store release required** — coordinate timeline
4. Feature flag: `MOBILE_OIDC_ENABLED` (server-side, for token validation)

### 6. Legacy Auth Deprecation
- Legacy JWT/session validation remains in BFFs during migration
- BFFs accept both legacy and OIDC tokens (distinguish by `iss` claim)
- After 100% migration + 2-week observation: remove legacy validation

## Migration Steps (Detailed)

### Step 1: Identity Service Deploy (Week 1-2)
- [ ] NestJS project with OIDC provider
- [ ] MongoDB collections + restricted credentials
- [ ] Client registration (6 clients)
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

### Step 3: Public UI Migration (Week 4-5)
- [ ] Public UI: OIDC login page (separate from admin)
- [ ] App BFF: Accept OIDC tokens
- [ ] Cookie/session: Separate domain (`svitlo-power.pp.ua` vs `admin.svitlo-power.pp.ua`)
- [ ] Shadow: Both paths, compare
- [ ] Cutover: Public UI defaults to OIDC

### Step 4: Mobile App Migration (Week 6-8)
- [ ] Mobile app: Implement Authorization Code + PKCE
- [ ] App store review cycle (2 weeks)
- [ ] App BFF: Accept mobile OIDC tokens
- [ ] Staged rollout: TestFlight/TestTrack → 10% → 100%
- [ ] Legacy mobile token validation remains until 100% migrated

### Step 5: Legacy Removal (Week 9+)
- [ ] 2-week observation at 100% OIDC
- [ ] Remove legacy token validation from BFFs
- [ ] Remove legacy login endpoints from back-end
- [ ] Remove legacy user session code

## Exit Gates

### Phase 7a (Identity Service Deployed)
| Criterion | Threshold |
|-----------|-----------|
| OIDC discovery + JWKS accessible | 100% |
| Token issuance (all flows) | Works in staging |
| Token exchange (BFF → Processor) | Works in staging |
| MFA enrollment + challenge | Works |
| Password reset flow | Works |
| Admin API (user CRUD) | Works |
| Load test: 1000 auth req/s | p99 < 200ms |

### Phase 7b (Admin Migrated)
| Criterion | Threshold |
|-----------|-----------|
| Admin login success rate | ≥ 99.9% |
| Token exchange success rate | 100% |
| Processor validates user tokens | 100% |
| Admin UI flows (all) | Work end-to-end |
| Rollback tested | < 2 min |

### Phase 7c (Public Migrated)
| Criterion | Threshold |
|-----------|-----------|
| Public login success rate | ≥ 99.9% |
| No shared cookies with admin | Verified |
| Mobile API (public endpoints) | Unaffected |

### Phase 7d (Mobile Migrated)
| Criterion | Threshold |
|-----------|-----------|
| Mobile login success rate | ≥ 99.9% |
| App store version > 50% adoption | Before legacy removal |
| Token refresh works (offline_access) | Verified |

### Phase 7e (Legacy Removed)
| Criterion | Threshold |
|-----------|-----------|
| 0 legacy token validations in logs | 14 days |
| All clients on OIDC | 100% |
| Identity Service HA | 2+ replicas, multi-AZ |

## Rollback Procedures

### Per-Client Rollback
1. Feature flag: `{CLIENT}_OIDC_ENABLED=false`
2. UI reverts to legacy login form
3. BFF accepts legacy tokens
4. Identity Service remains running (other clients unaffected)

### Full Rollback (Emergency)
1. All client flags `false`
2. Legacy auth fully active
3. Identity Service scaled to 0 (optional)
4. **Account mappings preserved** — `IdentityBinding` links `sub` to domain user
5. Re-migrate later with same `sub` values

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OIDC library vulnerabilities | Use maintained library (`@node-oidc/provider`); Dependabot; security scanning |
| Token exchange complexity | Start with simpler: BFF validates user token directly (JWKS), adds `X-User-Sub` header to Processor calls; migrate to token exchange later |
| Mobile app store delay | Begin mobile work early; use feature flag for server-side validation |
| Sub mismatch (legacy vs OIDC) | Migration script: legacy `userId` → OIDC `sub` mapping stored; Processor uses `sub` consistently |
| Session fixation | PKCE for all public clients; short access tokens (5 min); refresh token rotation |
| Identity Service downtime | 2+ replicas; health checks; BFFs cache JWKS (5 min TTL); graceful degradation |

## Test Checklist

- [ ] Unit: Identity Service issues valid tokens (all flows)
- [ ] Unit: Token exchange returns Processor-audience token
- [ ] Unit: Processor validates token, maps `sub` to domain user
- [ ] Integration: Admin UI → Identity → Admin BFF → Processor
- [ ] Integration: Public UI → Identity → App BFF → Processor
- [ ] Integration: Mobile → Identity → App BFF → Processor
- [ ] Contract: OpenID Connect certification tests (if applicable)
- [ ] Load: 1000 concurrent auth flows, p99 < 200ms
- [ ] Chaos: Identity Service down → BFFs use cached JWKS, return 503 for new logins
- [ ] Security: Penetration test on auth flows
- [ ] Migration: Legacy user → OIDC user mapping verified
- [ ] Rollback: Each client flag tested, legacy path works