# Security Review Checklist

Source: [Security Review Standards Research](../../docs/research/security-review-standards.md)

16-item checklist based on OWASP Top 10, ASVS 4.0, and CWE. Apply against every diff during PR security review.

---

## Critical

### 1. Injection

| Field | Value |
|-------|-------|
| **CWE** | CWE-79 (XSS), CWE-89 (SQLi), CWE-78 (OS Command Injection) |
| **Severity** | Critical |
| **ASVS** | V5.3 (Output Encoding), V5.2 (Sanitization) |

**Detection guidance:**
- String concatenation or template literals building SQL queries, shell commands, or HTML
- User input passed to `eval()`, `exec()`, `child_process`, `subprocess`, `os.system`
- ORM `.raw()` or `.execute()` with interpolated variables
- Rendering user content without escaping (`dangerouslySetInnerHTML`, `| safe`, `{!! !!}`)
- Template injection via user-controlled template strings

### 2. Missing Authorization

| Field | Value |
|-------|-------|
| **CWE** | CWE-862 |
| **Severity** | Critical |
| **ASVS** | V4.1 (General Access Control), V4.2 (Operation Level Access Control) |

**Detection guidance:**
- New endpoint/route without middleware or decorator enforcing permissions
- Database queries without tenant/user scoping (missing `WHERE user_id = ?`)
- Missing or disabled Row-Level Security (RLS) policies on new tables
- Admin-only operations accessible without role check
- API handler that reads `user_id` from request body instead of auth token

### 3. Broken Authentication

| Field | Value |
|-------|-------|
| **CWE** | CWE-287 |
| **Severity** | Critical |
| **ASVS** | V2.1 (Password Security), V3.5 (Token-based Session Management) |

**Detection guidance:**
- JWT verified without checking signature (`alg: none` accepted, missing `verify()`)
- Token expiry (`exp`) not checked or set far in the future
- Auth middleware bypassed for specific routes without justification
- Password comparison using `==` instead of constant-time compare
- Missing MFA enforcement on sensitive operations

### 4. Hardcoded Secrets

| Field | Value |
|-------|-------|
| **CWE** | CWE-798 |
| **Severity** | Critical |
| **ASVS** | V2.10 (Service Authentication) |

**Detection guidance:**
- API keys, passwords, tokens as string literals in source
- Private keys or certificates committed to repo
- `.env` files or secrets in non-ignored paths
- Default credentials in production config
- Grep for: `password\s*=\s*["']`, `api_key`, `secret`, `token`, `Bearer `, base64 blobs

---

## High

### 5. Cross-Site Request Forgery (CSRF)

| Field | Value |
|-------|-------|
| **CWE** | CWE-352 |
| **Severity** | High |
| **ASVS** | V4.2.2 |

**Detection guidance:**
- State-changing endpoints (POST/PUT/DELETE) without CSRF token validation
- Cookie-based auth without `SameSite=Strict` or `SameSite=Lax`
- CSRF middleware disabled or excluded for routes that mutate state
- Form submissions without hidden CSRF token field
- API endpoints that accept both cookie and token auth without CSRF protection on cookie path

### 6. Path Traversal

| Field | Value |
|-------|-------|
| **CWE** | CWE-22 |
| **Severity** | High |
| **ASVS** | V12.3 (File Execution) |

**Detection guidance:**
- User input concatenated into `fs.readFile`, `open()`, `Path.join()` without sanitization
- Missing check for `..`, `%2e%2e`, or null bytes in file path parameters
- Serving static files from user-specified directory without path normalization
- Download endpoints that accept arbitrary filenames
- Archive extraction without validating entry paths (zip slip)

### 7. Unrestricted File Upload

| Field | Value |
|-------|-------|
| **CWE** | CWE-434 |
| **Severity** | High |
| **ASVS** | V12.1 (File Upload) |

**Detection guidance:**
- Upload handler without server-side MIME type validation (trusting `Content-Type` header)
- No file size limit or limit set excessively high
- Uploaded files stored with original user-provided filename
- Missing virus/malware scanning on uploaded content
- Uploaded files served from same origin without `Content-Disposition: attachment`

### 8. Insecure Deserialization

| Field | Value |
|-------|-------|
| **CWE** | CWE-502 |
| **Severity** | High |
| **ASVS** | V5.5 (Deserialization Prevention) |

**Detection guidance:**
- `pickle.loads()`, `yaml.load()` (without SafeLoader), `unserialize()` on untrusted input
- `JSON.parse()` followed by direct object usage without schema validation
- Java `ObjectInputStream` on user-controlled data
- GraphQL or REST accepting polymorphic type fields without validation
- Message queue consumers deserializing without type allowlists

### 9. Server-Side Request Forgery (SSRF)

| Field | Value |
|-------|-------|
| **CWE** | CWE-918 |
| **Severity** | High |
| **ASVS** | V12.6 (SSRF Prevention) |

**Detection guidance:**
- User-controlled URL passed to `fetch()`, `axios()`, `requests.get()`, `http.get()` server-side
- Missing URL allowlist or blocklist for internal IP ranges (169.254.x.x, 10.x.x.x, 127.0.0.1)
- Webhook/callback URL registration without validation
- Image/PDF renderers fetching user-provided URLs
- DNS rebinding not mitigated (resolve then fetch pattern missing)

---

## Medium

### 10. Sensitive Data Exposure

| Field | Value |
|-------|-------|
| **CWE** | CWE-200, CWE-532 |
| **Severity** | Medium |
| **ASVS** | V8.1 (General Data Protection) |

**Detection guidance:**
- PII, tokens, or passwords in log statements (`console.log`, `logger.info`)
- Stack traces or internal paths returned in API error responses
- Sensitive fields included in API responses without explicit allowlisting
- Missing encryption at rest for PII columns
- Verbose error messages in production config (`DEBUG=true`, `RAILS_ENV=development`)

### 11. Weak Cryptography

| Field | Value |
|-------|-------|
| **CWE** | CWE-327, CWE-328 |
| **Severity** | Medium |
| **ASVS** | V6.2 (Algorithms) |

**Detection guidance:**
- MD5 or SHA-1 used for password hashing, token generation, or integrity checks
- Hardcoded IVs or nonces in encryption routines
- ECB mode usage (`AES-ECB`)
- Missing key rotation mechanism for long-lived secrets
- Custom crypto implementations instead of vetted libraries
- `Math.random()` / `random.random()` for security-sensitive values

### 12. Session Mismanagement

| Field | Value |
|-------|-------|
| **CWE** | CWE-614, CWE-384 |
| **Severity** | Medium |
| **ASVS** | V3.4 (Cookie-based Session Management) |

**Detection guidance:**
- Session cookies missing `HttpOnly`, `Secure`, or `SameSite` flags
- No session expiry or excessively long TTL (>24h without refresh)
- Session ID not rotated after authentication (session fixation)
- Refresh tokens without rotation or family tracking
- Logout not invalidating server-side session/token

### 13. Overly Permissive CORS

| Field | Value |
|-------|-------|
| **CWE** | CWE-942 |
| **Severity** | Medium |
| **ASVS** | V14.5 (HTTP Request Header Validation) |

**Detection guidance:**
- `Access-Control-Allow-Origin: *` on endpoints requiring authentication
- Origin reflected back without validation (`res.setHeader('ACAO', req.headers.origin)`)
- `Access-Control-Allow-Credentials: true` with wildcard or overly broad origin
- CORS configuration allowing `null` origin
- Missing CORS configuration review when auth strategy changes

### 14. Missing Rate Limiting

| Field | Value |
|-------|-------|
| **CWE** | CWE-770 |
| **Severity** | Medium |
| **ASVS** | V11.1 (Business Logic Security) |

**Detection guidance:**
- Login/registration/password-reset endpoints without rate limiter middleware
- API endpoints performing expensive operations (reports, exports, AI calls) without throttling
- Missing per-user or per-IP rate limiting on public endpoints
- Rate limiter configured but easily bypassed (e.g., keyed only on IP behind shared proxy)
- Webhook/callback endpoints without deduplication or throttling

---

## Low

### 15. Debug/Dead Code

| Field | Value |
|-------|-------|
| **CWE** | CWE-489, CWE-615 |
| **Severity** | Low |
| **ASVS** | V14.2 (Dependency) |

**Detection guidance:**
- `console.log` / `print` statements exposing sensitive variables
- Commented-out authentication or authorization checks
- `TODO` / `FIXME` / `HACK` comments referencing security concerns
- Debug routes or test endpoints left in production code
- Feature flags permanently enabled that bypass security controls

### 16. Dependency Risk

| Field | Value |
|-------|-------|
| **CWE** | CWE-1104 |
| **Severity** | Low |
| **ASVS** | V14.2 (Dependency) |

**Detection guidance:**
- Unpinned dependency versions (`^`, `~`, `*`, `>=` in package.json/requirements.txt)
- Direct dependencies with known CVEs (check against advisory databases)
- New dependencies with low download counts or no maintenance activity
- Typosquatting risk: package names similar to popular packages
- Unused dependencies increasing attack surface
