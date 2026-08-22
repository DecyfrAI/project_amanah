# Security

## Secure Defaults

- You MUST deny access by default. Every resource and endpoint starts as protected; explicit grants open access, not the reverse.
- You MUST use HTTPS (TLS 1.2 minimum) for all traffic. HTTP endpoints MUST redirect to HTTPS and MUST NOT serve authenticated content.
- You MUST set `Strict-Transport-Security` with a `max-age` of at least 1 year and `includeSubDomains` on all responses.
- You MUST set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or `SAMEORIGIN` when framing is required), and `Referrer-Policy: strict-origin-when-cross-origin`.
- You MUST configure a Content Security Policy (CSP). Start with `default-src 'none'` and enumerate only what is required.
- You SHOULD enable HSTS preloading for public-facing domains.
- You SHOULD disable debug modes, stack traces, and verbose error messages in production environments.
- You MUST NOT expose internal paths, dependency versions, server software versions, or database error messages to clients.

**Example — minimum security headers (HTTP response):**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Secrets

- You MUST NOT hardcode secrets (API keys, passwords, tokens, certificates) in source code, config files, or comments.
- You MUST NOT commit secrets to version control. Use pre-commit hooks (e.g., `git-secrets`, `truffleHog`) to prevent this.
- You MUST store secrets in a dedicated secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager) rather than environment variable files checked into repos.
- You MUST apply least-privilege access to the secrets store. Applications SHOULD retrieve only the secrets they need.
- You MUST rotate secrets. Prefer dynamic, short-lived credentials (e.g., database credentials issued per session) over long-lived static ones.
- You SHOULD automate secret rotation. Manual rotation introduces human error and delays.
- You MUST revoke and rotate any secret that has been exposed or may have been exposed.
- You SHOULD minimize the time a secret lives in application memory and zero-out memory when done (where language/runtime allows).
- You MUST audit all access to secrets: who retrieved what, when.

**Example — retrieve secret at runtime, never at build time:**
```python
# Good
import boto3
secret = boto3.client("secretsmanager").get_secret_value(SecretId="prod/db/password")

# Bad
DB_PASSWORD = "hunter2"  # hardcoded in source
```

**Example — Kubernetes: inject via in-memory volume, not env vars baked into images:**
```yaml
volumes:
  - name: secrets-vol
    emptyDir:
      medium: Memory
containers:
  - name: app
    volumeMounts:
      - name: secrets-vol
        mountPath: /mnt/secrets
        readOnly: true
```

---

## Input Validation

- You MUST validate all input at the server side regardless of client-side checks. Client-side validation is UX only.
- You MUST use allowlist (whitelist) validation as the primary strategy. Define exactly what is permitted; reject everything else.
- You MUST NOT rely on denylist (blacklist) validation as the sole control. Attackers trivially bypass blacklists.
- You MUST validate at both syntactic level (correct format, type, length) and semantic level (value is within valid business range and context).
- You MUST validate all untrusted data sources: user input, API partners, webhooks, batch feeds, and internal service calls crossing trust boundaries.
- You MUST enforce maximum lengths on all string inputs to prevent denial-of-service from excessively large payloads.
- You SHOULD use framework-native validators before writing custom logic (e.g., Django Validators, Bean Validation, `express-validator`).
- You MUST use parameterized queries / prepared statements for all database interactions. String concatenation into SQL queries is forbidden.
- You MUST use an OS-command allowlist or avoid shell invocation entirely. Never interpolate user input into shell commands.
- You SHOULD validate structured formats (JSON, XML) against a schema (JSON Schema, XSD) before processing.
- You MUST use anchored regular expressions (`^...$`) that cover the full input string, not partial matches.
- You SHOULD be aware of ReDoS (Regular Expression Denial of Service) when writing complex regex patterns.

**Example — SQL: parameterized query:**
```python
# Good
cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))

# Bad
cursor.execute(f"SELECT * FROM users WHERE email = '{user_email}'")
```

**Example — allowlist validation for a US zip code:**
```python
import re
ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
if not ZIP_RE.match(user_zip):
    raise ValidationError("Invalid zip code")
```

---

## Output Encoding

- You MUST apply context-aware output encoding when rendering user-controlled data:
  - HTML body: HTML-entity encode (`&`, `<`, `>`, `"`, `'`).
  - HTML attribute: attribute-encode and quote all values.
  - JavaScript: JSON-encode or use a dedicated JS-string escaper; never use string concatenation.
  - URL: percent-encode all dynamic components.
  - CSS: CSS-hex-encode values inserted into style contexts.
- You MUST use the templating engine's auto-escaping feature (e.g., Jinja2 with `autoescape=True`, React JSX). Explicit opt-out of auto-escaping (e.g., `dangerouslySetInnerHTML`, `|safe` filter) MUST be code-reviewed and justified.
- You MUST NOT rely on input validation alone to prevent XSS. Encoding at output is the primary defense.
- You SHOULD use `Content-Type: text/plain` for responses that are known to contain only plain text.
- You MUST sanitize rich user content (HTML WYSIWYG output) with a maintained allowlist-based library (e.g., DOMPurify, bleach).

**Example — Jinja2 with auto-escape enabled:**
```python
# Good
from jinja2 import Environment
env = Environment(autoescape=True)  # default-safe

# Bad
env = Environment(autoescape=False)
template.render(username=user_input)  # XSS if input contains <script>
```

---

## Authentication

- You MUST transmit passwords and session tokens only over TLS. The login page itself MUST be served over TLS.
- You MUST enforce a minimum password length of 8 characters when MFA is enabled, 15 characters when it is not (NIST SP 800-63B).
- You MUST allow passwords up to at least 64 characters to support passphrases.
- You MUST NOT impose arbitrary character-composition rules (e.g., "must contain a number"). Allow all Unicode characters including spaces.
- You MUST NOT silently truncate passwords.
- You SHOULD check new passwords against known-breached password lists (e.g., HaveIBeenPwned API) at registration and change time.
- You SHOULD surface a password-strength meter (e.g., `zxcvbn`) to users rather than rejecting passwords based on composition rules.
- You MUST NOT require periodic password changes absent evidence of compromise. Encourage strong passwords and MFA instead (NIST SP 800-63B).
- You MUST implement Multi-Factor Authentication (MFA) for all privileged accounts and SHOULD offer it to all users. Prefer passkeys or hardware security keys (FIDO2/WebAuthn) over TOTP, and TOTP over SMS. SMS SHOULD be a last resort due to SIM-swap risk.
- You MUST return a generic, constant-time error message for failed login, password reset, and account creation flows to prevent user enumeration.
- You MUST verify the current password before allowing a password change.
- You MUST require re-authentication before sensitive operations (password change, email change, payment method update, adding a new trusted device).
- You MUST implement login throttling or exponential backoff after repeated failures. Track failures by account, not by source IP alone.
- You SHOULD implement account lockout with a sensible threshold, observation window, and lockout duration. Ensure lockout cannot be weaponized for denial-of-service; allow password-reset flow to bypass lockout.
- You SHOULD use OIDC or SAML for SSO rather than building a bespoke identity protocol.
- You MUST log all authentication events: successes, failures, lockouts, and password changes, including timestamp and source IP.

**Example — generic error message (pseudo-code):**
```
# Good: processes the same path regardless of whether user exists
password_hash = HASH(password)
is_valid = LOOKUP_CREDENTIALS(username, password_hash)
if not is_valid:
    return Error("Invalid username or password.")

# Bad: reveals whether the username exists via timing
if USER_EXISTS(username):
    ...
else:
    return Error("Invalid username or password.")  # returns faster -> enumerable
```

---

## Authorization

- You MUST enforce authorization checks on every request, including AJAX and API calls. Server-side only; never trust client-side checks.
- You MUST apply least privilege. Grant users only the permissions required to perform their specific function, both horizontally (across peers) and vertically (across privilege levels).
- You MUST deny access by default. Be able to explicitly justify every granted permission.
- You MUST validate permissions against the specific resource being accessed on each request, not just at login or once per session.
- You MUST NOT expose sequential or guessable resource identifiers to users without accompanying per-request authorization checks. Prefer indirect references or UUIDs, and always verify ownership server-side.
- You MUST enforce authorization on static resources (files, images, documents in cloud storage) the same way as dynamic endpoints.
- You SHOULD prefer Attribute-Based Access Control (ABAC) or Relationship-Based Access Control (ReBAC) over simple RBAC for complex permission models. ABAC can incorporate time-of-day, device type, location, and other attributes.
- You MUST fail safely when an authorization check fails: return HTTP 403 (or redirect to login for unauthenticated), log the event, and never expose sensitive context in the error response.
- You MUST write automated unit and integration tests that cover authorization boundaries, including negative cases (access denied).
- You MUST NOT rely on security-through-obscurity (hidden fields, non-obvious URLs) as an authorization control.

**Example — per-request ownership check:**
```python
# Good
def get_invoice(request, invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    if invoice.owner != request.user:
        raise PermissionDenied
    return invoice

# Bad — fetches by ID with no ownership check
def get_invoice(request, invoice_id):
    return Invoice.objects.get(pk=invoice_id)
```

---

## Sessions

- You MUST generate session identifiers server-side using a cryptographically secure random number generator with sufficient entropy (≥128 bits).
- You MUST issue a new session identifier after a successful login (session fixation prevention).
- You MUST invalidate the session identifier on logout. Server-side session state MUST also be destroyed, not just the client-side cookie.
- You MUST set session cookies with `HttpOnly`, `Secure`, and `SameSite=Lax` (or `Strict`) attributes.
- You MUST NOT expose session identifiers in URLs, log files, or HTTP Referer headers.
- You MUST implement idle session timeouts (e.g., 15–30 minutes for sensitive applications) and absolute session expiry.
- You SHOULD implement re-authentication for sensitive operations even within an active session.
- You MUST rotate session tokens after privilege escalation or any change in authentication state.
- You MUST protect against CSRF: use `SameSite` cookies as the primary defense; add a synchronizer token or Double-Submit Cookie pattern for cross-origin use cases.

**Example — secure session cookie (Set-Cookie header):**
```
Set-Cookie: sessionid=<random>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=1800
```

---

## Encryption

- You MUST encrypt sensitive data at rest using AES-256 (or equivalent). Store decryption keys in a separate key management service (KMS), not alongside the data.
- You MUST use TLS 1.2 or higher for all data in transit. Disable TLS 1.0, TLS 1.1, and SSLv3. Disable weak cipher suites (RC4, DES, 3DES, export ciphers).
- You SHOULD use TLS 1.3 where supported.
- You MUST use mTLS for server-to-server communication in internal networks.
- You MUST NOT store passwords in reversible form. Use a memory-hard password hashing algorithm:
  - **Argon2id** is preferred (minimum: `m=19456` KB, `t=2`, `p=1`).
  - **scrypt** (`N=32768`, `r=8`, `p=1`) is acceptable.
  - **bcrypt** (work factor ≥ 10) is acceptable for legacy systems; note its 72-byte password limit.
  - **PBKDF2-HMAC-SHA256** (≥600,000 iterations) is acceptable for FIPS environments.
  - MD5, SHA-1, SHA-256, and unsalted hashes are forbidden for password storage.
- You MUST use a unique, cryptographically random salt per password (handled automatically by the above algorithms).
- You SHOULD use a server-side pepper (a secret combined with the password before hashing) stored separately from the database, as an additional layer.
- You MUST use constant-time comparison when verifying password hashes to prevent timing attacks.
- You MUST use authenticated encryption (AES-GCM, ChaCha20-Poly1305) rather than unauthenticated modes (AES-CBC without MAC).
- You MUST NOT generate cryptographic keys, nonces, or IVs with non-cryptographic random number generators (`Math.random()`, `rand()`).
- You SHOULD verify TLS configuration using a tool such as SSL Labs Server Test.

**Example — Argon2id in Python:**
```python
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
hash = ph.hash(password)          # store this
ph.verify(hash, password)         # returns True or raises exception
```

---

## Logging

- You MUST log the following security events with timestamp, user/session identifier, source IP, and outcome:
  - Authentication: successes, failures, lockouts, MFA events
  - Authorization: access denied events
  - Session: creation, termination, timeout
  - Account changes: password change, email change, MFA enrollment/removal
  - Privilege changes: role grants and revocations
  - Suspicious activity: impossible logins (new device, new geography), repeated failures
- You MUST NOT log the following sensitive data: plaintext passwords, secrets or API keys, full payment card numbers, session tokens, or other credentials.
- You MUST sanitize log messages to prevent log injection (newlines, CRLF sequences in user-controlled values).
- You SHOULD ship logs to a centralized, tamper-evident log store or SIEM separate from the application host.
- You MUST ensure log timestamps are synchronized (NTP) across all systems to support accurate incident correlation.
- You SHOULD define and enforce a log retention policy. Keep security-relevant logs for at least 90 days online and 1 year in cold storage.
- You MUST monitor logs and alert on anomalies in near-real-time. Unmonitored logs provide no security value.
- You MUST protect log integrity. Logs SHOULD be append-only and SHOULD require separate credentials to delete.

**Example — structured security log entry (JSON):**
```json
{
  "timestamp": "2026-06-12T14:32:01Z",
  "event": "auth.login.failure",
  "user_id": "usr_9x2k",
  "source_ip": "203.0.113.42",
  "user_agent": "Mozilla/5.0 ...",
  "reason": "invalid_password",
  "attempt_count": 3
}
```

---

## Dependencies

- You MUST track all third-party dependencies and their versions in a manifest (e.g., `package-lock.json`, `Pipfile.lock`, `go.sum`).
- You MUST scan dependencies for known vulnerabilities as part of CI/CD (e.g., `npm audit`, `pip-audit`, Dependabot, Snyk, OWASP Dependency-Check).
- You MUST act on critical and high-severity CVEs within a defined SLA (e.g., critical ≤7 days, high ≤30 days).
- You SHOULD pin dependencies to specific versions and review changes in automated update PRs before merging.
- You MUST NOT use dependencies that have reached end-of-life without a documented exception and compensating controls.
- You SHOULD generate and maintain a Software Bill of Materials (SBOM) to support supply-chain audits.
- You MUST verify package integrity using checksums or signatures when available (e.g., `npm ci`, lock file verification, PyPI hash checking).
- You SHOULD prefer dependencies with active maintenance, a security disclosure policy, and a responsive CVE history.

---

## File Uploads

- You MUST validate file type server-side by inspecting magic bytes (file signature), not only by MIME type or file extension supplied by the client.
- You MUST enforce maximum file size limits before processing.
- You MUST store uploaded files outside the web root or in a separate, isolated storage service (e.g., S3 bucket). Never store uploads directly in the application's document root.
- You MUST serve uploaded files with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff` to prevent execution in the browser.
- You MUST rename uploaded files to a server-generated name. Do not trust client-supplied file names.
- You MUST NOT allow uploaded files to be executed (disable PHP/CGI execution in the upload directory).
- You SHOULD scan uploads with antivirus or content inspection before making them available to other users.
- You SHOULD limit accepted file extensions to an explicit allowlist (e.g., only `.jpg`, `.png`, `.pdf`).
- For image uploads, you SHOULD re-encode the image through a known-safe library to strip embedded payloads (e.g., malicious EXIF data, polyglot files).

**Example — restrict accepted types and re-stream:**
```python
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}

def handle_upload(file):
    if file.content_type not in ALLOWED_TYPES:
        raise ValidationError("File type not permitted")
    if file.size > 10 * 1024 * 1024:  # 10 MB
        raise ValidationError("File too large")
    safe_name = f"{uuid.uuid4()}.{EXTENSION_MAP[file.content_type]}"
    storage.save(safe_name, file)
```

---

## Rate Limiting

- You MUST apply rate limiting to all authentication endpoints (login, password reset, MFA verification, registration) to mitigate brute-force and credential-stuffing attacks.
- You MUST apply rate limiting to all public-facing API endpoints.
- You SHOULD rate-limit by user/account identity in addition to source IP, since attackers frequently distribute requests across IPs.
- You SHOULD implement exponential backoff for repeat offenders rather than a flat window.
- You MUST return HTTP 429 (Too Many Requests) with a `Retry-After` header when a limit is exceeded.
- You SHOULD log rate-limit events to detect and investigate volumetric attacks.
- You MAY use a distributed cache (Redis, Memcached) for rate-limit counters to ensure consistency across multiple application instances.
- You SHOULD set resource quotas (e.g., token/request budgets per API key) and alert when nearing limits, not only when exceeded.

**Example — token bucket per account (pseudo-code):**
```python
KEY = f"rate:{user_id}:login"
count = redis.incr(KEY)
if count == 1:
    redis.expire(KEY, 60)  # 60-second window
if count > 5:
    raise RateLimitError("Too many login attempts. Retry after 60 seconds.")
```

---

## Security Reviews

- You MUST perform threat modeling at the design phase for any feature that touches authentication, authorization, payments, PII, or inter-service trust boundaries. Identify trust boundaries, data flows, and abuse cases before writing code.
- You MUST conduct a security-focused code review for all changes to authentication, authorization, cryptography, session management, and secrets handling. Automated CI gates do not replace human review for these areas.
- You SHOULD run automated static analysis (SAST) on every pull request and block merges on high-confidence findings.
- You SHOULD run dynamic analysis (DAST) and fuzzing against staging environments on a regular cadence.
- You MUST triage and remediate findings from security scans within the defined SLA for their severity.
- You SHOULD run penetration tests on a defined schedule (at minimum annually) and after major architectural changes.
- You MUST maintain a vulnerability disclosure program (bug bounty or responsible disclosure policy) with a clear process for receiving, triaging, and rewarding external reports.
- You MUST ensure that all code changes to security-sensitive paths pass through multiparty review (at least two reviewers).
- You SHOULD record security decisions, accepted risks, and compensating controls in Architecture Decision Records (ADRs) for future reference.
- You MUST train all engineers on secure coding practices. Security awareness is everyone's responsibility, not only the security team's.
