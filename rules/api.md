# API Design Rules

> **Scope:** These rules apply to all HTTP/REST APIs intended for external or long-lived internal consumers. Rules use RFC 2119 keywords: **MUST**, **SHOULD**, **MAY**.

---

## Table of Contents

1. [General Principles](#1-general-principles)
2. [Resource Design](#2-resource-design)
3. [Naming](#3-naming)
4. [HTTP Methods](#4-http-methods)
5. [Status Codes](#5-status-codes)
6. [Request Bodies](#6-request-bodies)
7. [Pagination](#7-pagination)
8. [Filtering](#8-filtering)
9. [Sorting](#9-sorting)
10. [Versioning](#10-versioning)
11. [Error Responses](#11-error-responses)
12. [Idempotency](#12-idempotency)
13. [Backward Compatibility](#13-backward-compatibility)
14. [Rate Limiting](#14-rate-limiting)

---

## 1. General Principles

### 1.1 Contract-First Design

APIs **MUST** be designed before implementation. The OpenAPI specification is the single source of truth and **MUST** be committed to version control before any server code is written.

**Why:** A spec-first discipline forces clarity about the domain model, prevents leaking implementation details into the API surface, and enables parallel client/server development. APIs that are reverse-engineered from implementations tend to be brittle, tightly coupled to their first implementation, and hard to version.

Define the API contract in OpenAPI 3.x:

```yaml
openapi: "3.1.0"
info:
  title: Orders API
  version: "2024-06-01"
paths:
  /orders:
    get:
      summary: List orders
      ...
```

Early review feedback **MUST** be solicited from client teams before the API reaches production. Incompatible changes discovered post-launch cost significantly more to fix.

### 1.2 API as a Product

API designers **MUST** treat their API as a product with real consumers. Design decisions **SHOULD** prioritize the developer experience of callers over implementation convenience of the provider.

- Minimize required fields and query parameters in every operation.
- Prefer generalized resource endpoints over use-case-specific ones.
- Document every breaking change with a migration guide and deprecation timeline.

### 1.3 Robustness

APIs **MUST** be conservative in what they send and **SHOULD** be documented to guide consumers on what to accept. Servers **MUST** reject unknown input fields in `PUT`, `POST`, and `PATCH` requests with `400 Bad Request` — silent acceptance of unknown fields hides typos and prevents safe future extension of the schema.

Clients **MUST** be prepared to:
- Ignore unknown fields in responses (tolerate server-side additions).
- Handle unknown enum values gracefully (treat as a default/unknown case).
- Handle HTTP status codes not explicitly listed in the spec by applying the `x00` class semantics (e.g., treat an unknown `4xx` as `400`).

### 1.4 Long-Lived APIs

APIs **MUST** be designed under the assumption that they will outlive their first implementation. Choices made on day one — resource names, field names, versioning strategy — are extremely expensive to change later.

- Prefer additive evolution over versioned rewrites.
- Never add mandatory fields to an existing operation without a new version.
- Enumerate all known breaking-change categories before releasing GA (see §13).

---

## 2. Resource Design

### 2.1 Resources Are Nouns

URLs **MUST** identify resources (things), not actions (verbs). Model the domain as a set of entities and collections.

```
# Good
GET  /orders
GET  /orders/{orderId}
POST /orders

# Bad — verb in path
POST /createOrder
GET  /getOrderById?id=123
```

### 2.2 Hierarchy

Resource paths **SHOULD** reflect ownership or containment relationships, but nesting **SHOULD NOT** exceed three levels to avoid brittle URLs.

```
/customers/{customerId}/subscriptions/{subscriptionId}   # acceptable
/customers/{id}/orders/{id}/items/{id}/details/{id}      # too deep — flatten
```

Top-level resources that are only meaningful in context of a parent **MAY** be exposed at the top level with a parent filter parameter when deep nesting would make independent access impractical.

### 2.3 Flat Schemas

Resource schemas **SHOULD** be shallow (one or two levels of nesting). Deep nesting complicates partial updates (PATCH), serialization, and readability.

```json
// Good
{
  "id": "ord_123",
  "customerId": "cust_456",
  "status": "pending",
  "totalAmount": 9999,
  "currency": "usd"
}

// Avoid when fields are simple
{
  "id": "ord_123",
  "customer": { "id": "cust_456", "details": { "address": { ... } } }
}
```

### 2.4 Consistent Schema Across Operations

The same JSON schema **MUST** be used for `PUT` request/response, `PATCH` response, `GET` response, and `POST` request/response on a given URL path. The `PATCH` request schema **MUST** have all fields optional.

This allows a single SDK type to serve as both input and output, and enables the GET response to be fed directly into a PATCH or PUT request.

### 2.5 Actions on Resources

When an operation cannot be expressed as CRUD, use a POST action appended to the resource URL with a colon separator:

```
POST /orders/{orderId}:cancel
POST /accounts/{accountId}:suspend
POST /invoices:bulkSend
```

Actions **MUST** use `POST`. Action names **SHOULD** be verbs. Actions **MUST NOT** be used when standard CRUD semantics would suffice.

---

## 3. Naming

### 3.1 URL Path Segments

URL path segments **MUST** use **kebab-case**. Collection names **MUST** be plural nouns.

```
/payment-methods       ✓
/paymentMethods        ✗
/payment_methods       ✗
/paymentmethod         ✗ (singular)
```

Resource identifiers **MUST** be raw values (no wrapping quotes or braces) and **MUST** be properly percent-encoded.

### 3.2 Query Parameters

Query parameter names **MUST** use **camelCase**.

```
GET /orders?pageSize=20&createdAfter=2024-01-01    ✓
GET /orders?page_size=20                            ✗
```

### 3.3 JSON Field Names

JSON field names **MUST** use **camelCase**. Acronyms **MUST NOT** be fully uppercased.

```json
{ "customerId": "...", "createdAt": "...", "totalVatAmount": 100 }   ✓
{ "CustomerID": "...", "created_at": "...", "totalVATAmount": 100 }  ✗
```

### 3.4 Date and Time

Date/time values **MUST** use [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339) format in JSON bodies: `YYYY-MM-DDTHH:mm:ssZ`. Date/time values in HTTP headers **MUST** use IMF-fixdate format per RFC 7231: `Sun, 06 Nov 1994 08:49:37 GMT`.

```json
{ "createdAt": "2024-06-01T14:30:00Z" }
```

Duration fields **MUST** include the unit in the field name:

```json
{ "ttlSeconds": 3600, "retryDelayMilliseconds": 500 }
```

### 3.5 Enumerations

Enum values **SHOULD** use `SCREAMING_SNAKE_CASE` for consistency and readability.

Enums that may grow over time **MUST** be documented as extensible. Clients **MUST** implement a default/fallback case for unrecognized enum values.

```yaml
status:
  type: string
  examples:
    - PENDING
    - PROCESSING
    - COMPLETED
    - FAILED
  description: "[Extensible enum] Current status of the order."
```

**MUST NOT** remove enum values from a published API — this is a breaking change.

### 3.6 Boolean Fields

Boolean field names **SHOULD** use affirmative phrasing to avoid double negatives.

```json
{ "isActive": true }     ✓
{ "notDisabled": true }  ✗
```

---

## 4. HTTP Methods

### 4.1 Method Semantics

**MUST** use HTTP methods according to their standardized semantics:

| Method   | Semantics                                      | Safe | Idempotent |
|----------|------------------------------------------------|------|------------|
| `GET`    | Read a resource or collection                  | Yes  | Yes        |
| `HEAD`   | Read headers only (no body)                    | Yes  | Yes        |
| `POST`   | Create a resource; invoke an action            | No   | No*        |
| `PUT`    | Replace a resource entirely                    | No   | Yes        |
| `PATCH`  | Partially update a resource                    | No   | No*        |
| `DELETE` | Remove a resource                              | No   | Yes        |
| `OPTIONS`| Describe available operations                  | Yes  | Yes        |

\* `POST` and `PATCH` **SHOULD** be made idempotent via idempotency keys or secondary keys (see §12).

### 4.2 GET

`GET` requests **MUST NOT** have a request body. `GET` requests **MUST NOT** cause side effects. Results **SHOULD** be cacheable unless the response contains user-specific or time-sensitive data.

For queries with complex filter payloads that exceed URL length limits, a `POST` to a search endpoint **MAY** be used with explicit documentation.

### 4.3 POST

`POST` on a collection **MUST** return `201 Created` with the created resource in the body and the resource URL in the `Location` header.

`POST` on an action **MUST** return `200 OK`.

```http
POST /orders HTTP/1.1
Content-Type: application/json

{ "customerId": "cust_123", "items": [...] }

---

HTTP/1.1 201 Created
Location: /orders/ord_456
Content-Type: application/json

{ "id": "ord_456", "status": "PENDING", ... }
```

### 4.4 PUT

`PUT` **MUST** replace the entire resource. Clients sending a `PUT` **MUST** provide all fields, as omitted fields will be reset to defaults. `PUT` **SHOULD** be idempotent by design — calling it twice with the same payload **MUST** produce the same result.

### 4.5 PATCH

`PATCH` **MUST** use [JSON Merge Patch (RFC 7396)](https://datatracker.ietf.org/doc/html/rfc7396) with `Content-Type: application/merge-patch+json` unless there is a strong justification for JSON Patch (RFC 6902).

To remove a field using Merge Patch, set it to `null`. Fields omitted from the patch payload **MUST NOT** be modified.

```http
PATCH /orders/ord_456 HTTP/1.1
Content-Type: application/merge-patch+json

{ "status": "CANCELLED" }
```

### 4.6 DELETE

`DELETE` **MUST** return `204 No Content` on success, even if the resource was already absent. **MUST NOT** return `404` for a previously-deleted resource.

---

## 5. Status Codes

### 5.1 Success Codes

| Code  | When to use                                                             |
|-------|-------------------------------------------------------------------------|
| `200` | Successful `GET`, `PUT`, `PATCH`, or `POST` action                      |
| `201` | Resource created by `POST` or `PUT`; return `Location` header           |
| `202` | Request accepted for async processing                                   |
| `204` | Successful `DELETE` or `PATCH`/`PUT` with no response body              |
| `207` | Batch/bulk request with per-item status (always inspect items array)    |

### 5.2 Client Error Codes

| Code  | When to use                                                             |
|-------|-------------------------------------------------------------------------|
| `400` | Malformed request, invalid parameter values, failed validation          |
| `401` | Missing or invalid credentials (authentication required)                |
| `403` | Authenticated but not authorized; use `404` if existence must be hidden |
| `404` | Resource not found; also used to hide existence for security reasons    |
| `405` | HTTP method not supported for this resource                             |
| `409` | State conflict (e.g., resource already exists, optimistic lock failure) |
| `410` | Resource permanently deleted and will not return                        |
| `412` | Conditional request failed (`If-Match`, `If-Unmodified-Since`)          |
| `415` | Unsupported `Content-Type`                                              |
| `422` | **SHOULD NOT** be used; prefer `400`                                    |
| `428` | Server requires a conditional header to prevent lost updates            |
| `429` | Rate limit exceeded (see §14)                                           |

### 5.3 Server Error Codes

| Code  | When to use                                                             |
|-------|-------------------------------------------------------------------------|
| `500` | Unexpected server error; clients **SHOULD NOT** auto-retry              |
| `502` | Bad gateway; upstream service returned invalid response                 |
| `503` | Service temporarily unavailable; include `Retry-After` header           |
| `504` | Gateway timeout; client **MAY** retry once immediately                  |

### 5.4 Rules

- **MUST** use the most specific applicable status code.
- **MUST NOT** return `2xx` for an operation that partially failed — use `207` for batch or `4xx`/`5xx` for total failure.
- **MUST NOT** use `301`/`302`/`307`/`308` redirect codes in API responses — handle redirects at the infrastructure layer.
- Stack traces **MUST NOT** be included in any response body.

---

## 6. Request Bodies

### 6.1 Format

Request and response bodies **MUST** use JSON (`application/json`) unless there is an established reason for another format (e.g., multipart for file upload).

### 6.2 Null Values

Servers **MUST NOT** return `null`-valued fields in responses. Omit the field entirely. Clients **MUST** treat a missing field and a field with `null` value identically.

In `PATCH` requests with Merge Patch, `null` explicitly means "delete this field."

### 6.3 Top-Level Structure

Responses **MUST** be JSON objects at the top level — never bare arrays, strings, or numbers. This allows future extension without breaking clients.

```json
// Good
{ "items": [...], "next": "https://..." }

// Bad
[{ "id": "ord_1" }, { "id": "ord_2" }]
```

### 6.4 Polymorphic Types

When a schema field may contain different object shapes, a discriminator field **MUST** be included. The discriminator field **SHOULD** be named `kind` or `type`.

```json
// Payment method with discriminator
{ "kind": "card", "last4": "4242", "brand": "visa" }
{ "kind": "bank_transfer", "iban": "DE89..." }
```

### 6.5 Secret Fields

Secret values (passwords, tokens) **MUST NOT** be returned in `GET` responses. They **MAY** be returned once at creation time via `POST` and never again.

---

## 7. Pagination

### 7.1 Requirement

All collection endpoints that may return more than a few hundred items **MUST** support pagination. Adding pagination to an unpaginated endpoint is a breaking change — design it in from day one.

### 7.2 Cursor-Based Pagination (Preferred)

Cursor-based pagination **SHOULD** be used in preference to offset-based pagination. Cursors are stable under concurrent inserts/deletes, work efficiently with NoSQL and sharded databases, and prevent missing or duplicate results.

The cursor **MUST** be opaque — clients **MUST NOT** inspect or construct it. The cursor encodes all page position and filter state internally.

```http
GET /orders?limit=25

{
  "items": [...],
  "next": "https://api.example.com/orders?cursor=eyJpZCI6Im9yZF8xMDAifQ&limit=25",
  "prev": "https://api.example.com/orders?cursor=eyJpZCI6Im9yZF8xIn0&limit=25"
}
```

### 7.3 Offset-Based Pagination

Offset-based pagination **MAY** be used when jumping to an arbitrary page is a genuine product requirement and the dataset is bounded.

```http
GET /orders?offset=50&limit=25
```

### 7.4 Pagination Response Shape

Paginated responses **MUST** use this structure:

```json
{
  "items": [ ... ],
  "next": "https://api.example.com/orders?cursor=<next>",
  "prev": "https://api.example.com/orders?cursor=<prev>",
  "self": "https://api.example.com/orders?cursor=<current>"
}
```

- `next` **MUST** be omitted (not null) on the last page.
- `prev` **MUST** be omitted (not null) on the first page.
- Pagination links **MUST** be absolute URLs and **MUST** include all query parameters needed to reproduce the request (including version, filters, and sort order).

### 7.5 Total Count

Total result counts **SHOULD NOT** be returned by default. Counting requires a full index scan and becomes expensive as data grows. If consumers require it, support opt-in via a `Prefer: return=total-count` request header.

### 7.6 Standard Parameters

| Parameter    | Type    | Description                                          |
|--------------|---------|------------------------------------------------------|
| `cursor`     | string  | Opaque cursor for cursor-based pagination            |
| `limit`      | integer | Maximum items per page; minimum 1, default per API   |
| `offset`     | integer | Zero-based offset for offset-based pagination        |
| `pageSize`   | integer | Alias for `limit` if preferred by the domain         |

---

## 8. Filtering

### 8.1 Simple Filters

For simple equality and range filtering, **SHOULD** use dedicated query parameters:

```
GET /orders?status=PENDING
GET /orders?createdAfter=2024-01-01&createdBefore=2024-06-30
GET /orders?customerId=cust_123&status=PENDING,PROCESSING
```

Document each filter parameter: the corresponding field, the comparison semantics, and how multiple values combine.

### 8.2 Complex Filters

For APIs with many filters, dynamic filter sets, or boolean logic (`and`, `or`, `not`), use a structured JSON filter body sent via `POST` to a dedicated search endpoint:

```http
POST /orders/search HTTP/1.1
Content-Type: application/json

{
  "filter": {
    "and": {
      "status": { "in": ["PENDING", "PROCESSING"] },
      "createdAt": { "gte": "2024-01-01T00:00:00Z" }
    }
  },
  "limit": 25
}
```

### 8.3 Filter on Unsupported Fields

The server **MUST** return `400 Bad Request` if the client filters on a field that is not supported by that operation.

### 8.4 Authorization Filtering

If the response set is implicitly filtered based on the caller's permissions (e.g., a tenant only sees their own data), this **MUST** be documented explicitly in the API specification.

---

## 9. Sorting

### 9.1 Sort Parameter

Sorting **MAY** be supported via an `orderBy` query parameter containing a comma-separated list of field expressions.

```
GET /orders?orderBy=createdAt desc,totalAmount asc
```

- Default direction when not specified: **ascending**.
- `null` values **MUST** sort as less than non-null values.
- Sort **MUST** be applied before pagination.
- The sort order **MUST** remain consistent across all pages of a paginated result.

### 9.2 Unsupported Sort Fields

The server **MUST** return `400 Bad Request` if the client requests sorting on a field that is not supported.

### 9.3 Stability Warning

Sorting large collections is expensive. APIs **SHOULD** document which fields are sortable and **SHOULD** limit sort options to indexed fields.

---

## 10. Versioning

### 10.1 Strategy

APIs **MUST** be versioned. Version information **MUST** be carried in the URL path as a major version prefix:

```
https://api.example.com/v1/orders
https://api.example.com/v2/orders
```

The major version in the path signals incompatible surface changes. Within a major version, all changes **MUST** be backward-compatible (see §13).

**Rationale for path versioning over header/media-type versioning:** Path-based versioning is explicit, cacheable, bookmarkable, and universally supported by every HTTP client, proxy, and gateway without additional configuration.

### 10.2 Version Format

The version segment **MUST** be `v` followed by a monotonically increasing integer: `v1`, `v2`, `v3`.

For fine-grained evolution within a major version (e.g., rolling out a specific behavior change), a date-based sub-version **MAY** be communicated via the `API-Version` header:

```http
API-Version: 2024-06-01
```

When using header sub-versioning, the server **MUST**:
- Default to the latest stable sub-version when the header is absent.
- Return the sub-version used in the `API-Version` response header.
- Honor a pinned sub-version for at least 12 months after it is superseded.

### 10.3 Initial Release

Services **SHOULD NOT** ship a v2 until v1 is GA and has real consumers. Begin at `v1`.

### 10.4 Version Lifecycle

| Phase      | Policy                                                                   |
|------------|--------------------------------------------------------------------------|
| Preview    | Labeled `v2-preview`; **MAY** have breaking changes with 30-day notice  |
| GA         | Stable; breaking changes require a new major version                     |
| Deprecated | Still served; `Sunset` and `Deprecation` response headers **MUST** be set|
| Retired    | Returns `410 Gone` with migration documentation URL                      |

Deprecated versions **MUST** be supported for a minimum of **12 months** after the successor GA date, with adequate notice to consumers.

### 10.5 Deprecation Headers

When deprecating a version or a specific operation, **MUST** include these response headers:

```http
Deprecation: Sun, 01 Jun 2025 00:00:00 GMT
Sunset: Sun, 01 Jun 2026 00:00:00 GMT
Link: <https://docs.example.com/migration/v1-to-v2>; rel="deprecation"
```

### 10.6 No Version in the Response Body

The API version **MUST NOT** appear in response body fields. It is transport metadata, not resource data.

---

## 11. Error Responses

### 11.1 Format

All error responses (`4xx`, `5xx`) **MUST** use [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457) with `Content-Type: application/problem+json`.

```json
{
  "type": "/problems/invalid-parameter",
  "title": "Invalid Parameter",
  "status": 400,
  "detail": "The 'currency' field must be a valid ISO 4217 code.",
  "instance": "/orders/ord_123",
  "errors": [
    {
      "field": "currency",
      "code": "INVALID_CURRENCY",
      "message": "'XYZ' is not a recognized currency code."
    }
  ]
}
```

### 11.2 Required Fields

| Field      | Type    | Required | Description                                            |
|------------|---------|----------|--------------------------------------------------------|
| `type`     | string  | **MUST** | A relative URI identifying the problem type            |
| `title`    | string  | **MUST** | Short, human-readable summary (stable, not per-instance)|
| `status`   | integer | **MUST** | The HTTP status code                                    |
| `detail`   | string  | **SHOULD**| Human-readable explanation of this specific occurrence |
| `instance` | string  | **SHOULD**| URI of the specific resource or request involved        |

### 11.3 Machine-Readable Error Codes

Every error **MUST** include a machine-readable `code` that client code can branch on. Error codes are **API contract** — they **MUST NOT** change meaning across minor versions.

```json
{
  "type": "/problems/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "code": "RATE_LIMIT_EXCEEDED",
  "detail": "You have exceeded 100 requests per minute.",
  "retryAfterSeconds": 47
}
```

Error codes **MUST** be documented in the API specification alongside each operation.

### 11.4 Field-Level Errors

When a `400` is caused by multiple invalid fields, all violations **MUST** be returned in a single response — not one per request. Use an `errors` array:

```json
{
  "type": "/problems/validation-failed",
  "title": "Validation Failed",
  "status": 400,
  "errors": [
    { "field": "email", "code": "INVALID_FORMAT", "message": "Must be a valid email address." },
    { "field": "amount", "code": "MUST_BE_POSITIVE", "message": "Amount must be greater than 0." }
  ]
}
```

### 11.5 Prohibited in Errors

- **MUST NOT** expose stack traces, internal exception class names, or SQL.
- **MUST NOT** include sensitive data (credentials, PII, internal IDs) in error messages.
- **MUST NOT** use generic messages like "An error occurred" without a `code` to disambiguate.

### 11.6 Request Correlation

Every response **MUST** include a `X-Request-Id` header containing a unique identifier for the request. Errors **SHOULD** include this ID in the `instance` field or as a top-level `requestId` field to simplify support escalations.

---

## 12. Idempotency

### 12.1 Why Idempotency Matters

Network failures make it impossible to know whether a request succeeded. Clients **MUST** be able to safely retry any operation. All HTTP methods except `POST` and `PATCH` are natively idempotent. These two **MUST** be made idempotent via one of the patterns below.

### 12.2 Idempotency Key Header

`POST` and `PATCH` endpoints **SHOULD** accept an `Idempotency-Key` header containing a client-generated UUID:

```http
POST /payments HTTP/1.1
Idempotency-Key: a8098c1a-f86e-11da-bd1a-00112444be1e
Content-Type: application/json

{ "amount": 2000, "currency": "usd" }
```

Server behavior:
- On first request with a given key: process normally, store the response.
- On subsequent requests with the same key (within a retention window of at least 24 hours): return the stored response with `200 OK` without re-executing.
- If the same key is received while the first request is still being processed: return `409 Conflict`.
- Idempotency keys **MUST** be scoped to the authenticated principal — keys from different callers **MUST NOT** collide.

```http
HTTP/1.1 200 OK
Idempotency-Key: a8098c1a-f86e-11da-bd1a-00112444be1e
X-Idempotent-Replayed: true
```

### 12.3 Secondary Key (Natural Idempotency)

For resources with a natural unique business key, **SHOULD** enforce uniqueness server-side and return `409 Conflict` on duplicate submission rather than creating a duplicate resource:

```json
POST /subscriptions
{ "planId": "plan_pro", "customerId": "cust_123" }

// If customer already has this subscription:
409 Conflict
{ "code": "SUBSCRIPTION_EXISTS", "existingId": "sub_456" }
```

### 12.4 Conditional Updates

`PUT`, `PATCH`, and `DELETE` **SHOULD** support optimistic concurrency via `ETag` and `If-Match`:

```http
GET /orders/ord_123
→ ETag: "abc123"

PATCH /orders/ord_123 HTTP/1.1
If-Match: "abc123"
Content-Type: application/merge-patch+json

{ "status": "CANCELLED" }
```

If the resource changed since the ETag was read, **MUST** return `412 Precondition Failed`.

---

## 13. Backward Compatibility

### 13.1 Additive Changes (Non-Breaking)

The following changes are safe to make within a major version without a new version:

**Safe to add:**
- New optional request fields (with sensible defaults)
- New response fields (clients must tolerate unknown fields)
- New enum values on extensible enums (documented as extensible)
- New optional query parameters
- New endpoints
- New error codes on existing status codes

**Safe to change:**
- Widening input validation (accepting more values)
- Narrowing output (returning fewer fields is acceptable if the field was optional)

### 13.2 Breaking Changes (Require New Major Version)

The following changes **MUST** increment the major version:

| Category         | Examples                                                          |
|------------------|-------------------------------------------------------------------|
| Removal          | Removing a field, endpoint, or enum value                         |
| Rename           | Renaming a field, URL segment, or parameter                       |
| Type change      | Changing a field from string to integer                           |
| Semantic change  | Changing what a field means (e.g., `amount` from cents to dollars)|
| Validation change| Making optional field required, tightening value constraints      |
| Behavior change  | Changing idempotency semantics, response status codes             |
| Pagination change| Adding pagination to a previously-unpaginated endpoint            |

**Never perform breaking changes silently.** If a breaking change is approved, it requires a new major version, a migration guide, and a 12-month deprecation window on the old version.

### 13.3 Schema Evolution Rules

For fields used in both input and output (the typical case):

- **MUST** only add optional fields, never mandatory ones.
- **MUST NOT** remove any fields.
- **MUST NOT** make mandatory fields optional or optional fields mandatory.
- **MUST NOT** extend enum values (extensible enums via `examples` are an exception — see §3.5).
- **MUST NOT** change field types or semantics.

### 13.4 Client Robustness Contract

Document in your API spec that clients **MUST**:
1. Ignore unknown response fields.
2. Handle unknown enum values without throwing.
3. Not treat the absence of an optional field as an error.

This is the client side of the backward compatibility contract — it allows servers to add new fields safely.

---

## 14. Rate Limiting

### 14.1 Requirement

APIs **MUST** enforce rate limits to protect against abuse and overload. Rate-limited responses **MUST** use status code `429 Too Many Requests`.

### 14.2 Response Headers

When returning `429`, the response **MUST** include at minimum a `Retry-After` header. APIs **SHOULD** also return proactive `X-RateLimit-*` headers on every successful response:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 30

{
  "type": "/problems/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "You have exceeded the limit of 100 requests per minute.",
  "retryAfterSeconds": 30
}
```

| Header                  | Description                                                       |
|-------------------------|-------------------------------------------------------------------|
| `Retry-After`           | Seconds to wait before retrying (or an HTTP-date)                 |
| `X-RateLimit-Limit`     | Maximum requests allowed in the current window                    |
| `X-RateLimit-Remaining` | Requests remaining in the current window                          |
| `X-RateLimit-Reset`     | Seconds until the window resets                                   |

### 14.3 Retry Strategy for Clients

Clients **MUST** respect `Retry-After`. Clients **MUST** implement exponential backoff with jitter when retrying after transient errors (`429`, `503`, `504`):

```
delay = min(base * 2^attempt + random_jitter, max_delay)
```

Where:
- `base` = 1 second
- `max_delay` = 60 seconds
- `random_jitter` = random value in [0, base]

Clients **MUST NOT** retry on `4xx` errors other than `429` unless the operation is idempotent and the specific error is documented as retriable.

### 14.4 Granularity

Rate limits **SHOULD** be applied per authenticated principal (API key, OAuth client, or user token), not per IP address. Document the specific limits in the API reference so consumers can design their integration accordingly.

### 14.5 Burst Allowance

APIs **MAY** support a burst allowance that permits short spikes above the sustained rate limit. Burst limits **SHOULD** be documented alongside sustained limits.
