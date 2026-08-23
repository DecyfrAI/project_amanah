# 0002. Verify Supabase access tokens with the shared JWT secret

* **Status**: accepted
* **Date**: 2026-08-22
* **Deciders**: Project Amanah team

## Context and Problem Statement

[ADR 0001](./0001-require-authentication-for-application-access.md) makes every
`/v1` endpoint require a server-verified session. The backend therefore has to
verify Supabase access tokens itself. Supabase can issue tokens under two
schemes: symmetric `HS256` signed with the project's shared JWT secret, or
asymmetric keys published at `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`.

`spec.md` section 22.1 lists `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and
`DATABASE_URL` as server variables but names no verification key, so the choice
also decides whether a new required variable is introduced.

## Decision Drivers

* Verification must be server-side and must not depend on a provider being
  reachable during a request.
* The 48-hour build cannot absorb a key-rotation and cache-invalidation surface.
* Negative authorization tests must be deterministic and offline.
* Startup must fail on weak or missing configuration rather than at first
  request.

## Considered Options

* Symmetric `HS256` verification with the project JWT secret.
* Asymmetric verification against the Supabase JWKS endpoint.

## Decision Outcome

**Chosen option**: symmetric `HS256` verification with the project JWT secret,
supplied as a new required variable `SUPABASE_JWT_SECRET`.

`amanah.auth.tokens.verify_access_token` checks the signature, the `authenticated`
audience, the issuer derived from `SUPABASE_URL`, and the presence of `exp`,
`iat`, `sub`, `aud`, and `iss`. The subject must parse as a UUID.

The product role is read from `app_metadata.role`, which only the service-role
key can write. Supabase's top-level `role` claim is its Postgres role and is
ignored; treating it as a product role would grant every signed-in user the same
privileges. An unrecognized role value falls back to `registered_user`, so an
unexpected claim can only reduce privilege.

The secret must be at least 32 characters, enforced at startup, because a shorter
HMAC key weakens every token the service accepts (RFC 7518 section 3.2).

### Positive Consequences

* Verification needs no network call, so an authentication check cannot fail
  because a provider endpoint is slow or unreachable.
* Tests sign their own throwaway tokens and cover expiry, wrong issuer, wrong
  audience, wrong secret, missing claims, and forged roles without any mock.
* A weak or missing secret stops the deployment at startup.

### Negative Consequences / Trade-offs

* One more secret has to be provisioned and rotated, and it is shared rather than
  public-key material, so exposure is more damaging than a leaked public key.
* Rotating the secret invalidates live sessions; there is no overlap window.
* Migrating to Supabase's asymmetric keys later means changing the verification
  path and the configuration contract together.

## Pros and Cons of the Options

### Symmetric `HS256` with the shared secret

* Good: offline, deterministic verification; trivial to test.
* Good: no cache, no key-rotation state machine, no provider dependency.
* Bad: introduces a shared secret with no rotation overlap.

### Asymmetric verification against JWKS

* Good: no shared secret; supports key rotation without invalidating sessions.
* Bad: adds a network dependency, a key cache, and its invalidation rules to the
  authentication path.
* Bad: needs HTTP mocking in every authorization test.

## Links

* Governing requirements: [`../spec.md`](../spec.md) sections 16 and 22.1
* Access boundary: [`0001-require-authentication-for-application-access.md`](./0001-require-authentication-for-application-access.md)
* Implementation: `backend/src/amanah/auth/tokens.py`, `backend/src/amanah/settings.py`
