# Database Rules

Assumes PostgreSQL. Principles apply broadly to other relational databases unless otherwise noted.

---

## Naming

- Identifiers (tables, columns, indexes, constraints) MUST use `lowercase_snake_case`. PostgreSQL folds unquoted identifiers to lowercase; quoted mixed-case identifiers require quotes everywhere and break ORMs, AI tools, and migrations.
- SQL keywords MUST be written in `UPPERCASE`; identifiers in `lowercase`.
- Tables MUST be named as plural nouns: `orders`, `users`, `audit_events`.
- Boolean columns SHOULD use an `is_` or `has_` prefix: `is_active`, `has_verified_email`.
- Timestamp columns MUST follow the `<event>_at` pattern: `created_at`, `published_at`, `deleted_at`.
- Foreign key columns MUST be named `<referenced_table_singular>_id`: `customer_id` referencing `customers(id)`.
- Indexes MUST be named `<table>_<columns>_idx` and constraints `<table>_<columns>_<type>` (e.g., `orders_customer_id_idx`, `users_email_unique`).

```sql
-- Correct
CREATE TABLE order_items (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id    bigint NOT NULL REFERENCES orders(id),
  product_id  bigint NOT NULL REFERENCES products(id),
  quantity    int    NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Wrong: quoted camelCase, singular table name, ambiguous FK name
CREATE TABLE "OrderItem" (
  "Id"         serial PRIMARY KEY,
  "orderId"    int,
  "createdAt"  timestamp
);
```

---

## Primary Keys

- Every table MUST have a single-column surrogate primary key.
- For single-database systems, use `bigint GENERATED ALWAYS AS IDENTITY`. It is SQL-standard, sequential, and 8 bytes.
- `serial` MAY be used in existing schemas but MUST NOT be used for new tables; prefer `IDENTITY`.
- For distributed systems or externally exposed IDs, use time-ordered UUIDs (UUIDv7 via `pg_uuidv7`) or ULIDs. Random UUIDv4 MUST NOT be used as a primary key on large tables — it causes index fragmentation.
- Composite natural-key primary keys MAY be used on pure junction tables (e.g., `user_roles`) but SHOULD be paired with a surrogate `id` when the table will be referenced widely.

```sql
-- Single database (recommended default)
CREATE TABLE users (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY
);

-- Distributed / exposed IDs (requires pg_uuidv7 extension)
CREATE TABLE events (
  id uuid DEFAULT uuid_generate_v7() PRIMARY KEY
);

-- Junction table with composite PK
CREATE TABLE user_roles (
  user_id bigint NOT NULL REFERENCES users(id),
  role_id bigint NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, role_id)
);
```

---

## Foreign Keys

- Every foreign key column MUST have a `REFERENCES` constraint declared at the database level.
- Every foreign key column MUST have an index. PostgreSQL does not create one automatically, so JOINs and `ON DELETE CASCADE` operations will cause full table scans without it.
- The `ON DELETE` behavior MUST be explicitly specified. Choose `RESTRICT`, `CASCADE`, or `SET NULL` intentionally; never rely on the default (`NO ACTION`).
- Cascading deletes (`ON DELETE CASCADE`) SHOULD be used sparingly. Prefer `RESTRICT` and handle deletion explicitly in application code to avoid unintended data loss.

```sql
CREATE TABLE orders (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id bigint NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
  total       numeric(10,2) NOT NULL
);

-- Required: index the FK column
CREATE INDEX orders_customer_id_idx ON orders (customer_id);
```

To audit missing FK indexes:

```sql
SELECT
  conrelid::regclass AS table_name,
  a.attname          AS fk_column
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  );
```

---

## Constraints

- Columns MUST be `NOT NULL` unless `NULL` has deliberate semantic meaning (e.g., `deleted_at` for soft deletes).
- `CHECK` constraints MUST be used to enforce domain rules at the database level: valid ranges, allowed values, format patterns.
- `UNIQUE` constraints MUST be used to enforce uniqueness instead of application-layer checks.
- Default values SHOULD be defined at the database level for columns that have a predictable default.
- PostgreSQL does not support `ADD CONSTRAINT IF NOT EXISTS`. Migrations that add constraints MUST use a `DO` block for idempotency.

```sql
-- Column constraints
CREATE TABLE products (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sku         text NOT NULL,
  price       numeric(10,2) NOT NULL CHECK (price >= 0),
  status      text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT products_sku_unique UNIQUE (sku)
);

-- Idempotent constraint addition in a migration
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'products_sku_unique'
      AND conrelid = 'products'::regclass
  ) THEN
    ALTER TABLE products
      ADD CONSTRAINT products_sku_unique UNIQUE (sku);
  END IF;
END $$;
```

---

## Indexes

- Every foreign key column MUST be indexed (see Foreign Keys).
- Columns used in `WHERE`, `JOIN ON`, or `ORDER BY` clauses on large tables SHOULD be indexed.
- The default index type is B-tree. Use a different type only when the access pattern requires it.
- Composite indexes SHOULD be used when queries consistently filter on multiple columns. Place equality columns first, range columns last (leftmost-prefix rule).
- Partial indexes SHOULD be used when queries consistently include a fixed `WHERE` condition. They are smaller and faster than full indexes.
- Covering indexes (`INCLUDE`) MAY be used to eliminate heap fetches for read-heavy queries that select a small, fixed column set.
- Multicolumn indexes SHOULD NOT be added speculatively. Add them when a real query pattern justifies it.
- Unused indexes MUST be removed. Every index adds write overhead.

```sql
-- B-tree (default): equality and range queries
CREATE INDEX orders_created_at_idx ON orders (created_at);

-- GIN: JSONB containment, arrays, full-text search
CREATE INDEX products_attributes_idx ON products USING GIN (attributes);

-- GiST: geometric / range types
CREATE INDEX locations_geom_idx ON places USING GIST (location);

-- BRIN: time-series append-only tables (tiny size, fast maintenance)
CREATE INDEX events_created_at_idx ON events USING BRIN (created_at);

-- Hash: equality-only lookups (slightly faster than B-tree for =)
CREATE INDEX sessions_token_idx ON sessions USING HASH (token);

-- Composite: equality column first, range column second
CREATE INDEX orders_status_created_idx ON orders (status, created_at);
-- Satisfies: WHERE status = 'pending'
-- Satisfies: WHERE status = 'pending' AND created_at > '2024-01-01'
-- Does NOT satisfy: WHERE created_at > '2024-01-01' alone

-- Partial: only active (non-deleted) rows
CREATE INDEX users_active_email_idx ON users (email)
WHERE deleted_at IS NULL;

-- Covering: avoid heap fetch for a common read pattern
CREATE INDEX orders_status_cover_idx ON orders (status)
  INCLUDE (customer_id, total);
```

---

## Data Types

- Integer IDs MUST use `bigint`, not `int`. `int` overflows at ~2.1 billion rows.
- Variable-length strings MUST use `text`. `varchar(n)` provides no performance benefit and the arbitrary length limit is almost always wrong.
- `varchar(n)` MAY be used when an external specification mandates a maximum length, expressed as a `CHECK` constraint instead when possible.
- Timestamps MUST use `timestamptz` (timestamp with time zone). Plain `timestamp` loses timezone context and causes bugs across daylight-saving boundaries and distributed systems.
- Monetary values MUST use `numeric(p,s)`. `float` and `double precision` use binary floating-point arithmetic and MUST NOT be used for money.
- Boolean flags MUST use `boolean`, not `char(1)`, `smallint`, or `varchar`.
- JSONB columns SHOULD be avoided. They bypass relational constraints and make queries fragile. Use JSONB only when storing an entire opaque document from an external source.

```sql
-- Correct
CREATE TABLE users (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email      text NOT NULL,
  is_active  boolean NOT NULL DEFAULT true,
  balance    numeric(12,2) NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Wrong
CREATE TABLE users (
  id         int PRIMARY KEY,           -- overflows at 2.1B
  email      varchar(255),              -- artificial limit
  is_active  varchar(5),                -- string for boolean
  balance    float,                     -- imprecise for money
  created_at timestamp                  -- no timezone
);
```

---

## Timestamps

- Every table MUST have `created_at timestamptz NOT NULL DEFAULT now()`.
- Tables that support updates MUST have `updated_at timestamptz NOT NULL DEFAULT now()`, kept current via a trigger or ORM hook.
- Timestamp columns MUST follow the `<event>_at` naming convention: `published_at`, `confirmed_at`, `expired_at`.
- All timestamps MUST be stored in UTC. Convert to local time in the application layer.

```sql
CREATE TABLE posts (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title        text NOT NULL,
  published_at timestamptz,                              -- nullable: not yet published
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
```

---

## Soft Deletes

- Soft deletes SHOULD be implemented with a `deleted_at timestamptz` column, set to `now()` on deletion and `NULL` for live rows.
- A partial index MUST be created on the primary lookup column(s) filtering `WHERE deleted_at IS NULL`. Without it, every query on active rows scans deleted rows too.
- Application queries MUST always filter `WHERE deleted_at IS NULL` unless intentionally including deleted rows.
- Hard delete is simpler and SHOULD be preferred unless audit history or recovery is a requirement.

```sql
ALTER TABLE users ADD COLUMN deleted_at timestamptz;

-- Partial index so active-row lookups stay fast
CREATE INDEX users_active_email_idx ON users (email)
WHERE deleted_at IS NULL;

-- Query for active users
SELECT * FROM users
WHERE email = 'alice@example.com'
  AND deleted_at IS NULL;
```

---

## Normalization

- Data MUST be stored in one place. Duplicated facts lead to update anomalies and inconsistent reads.
- Aim for at least third normal form (3NF) by default. Every non-key column depends on the whole key and nothing but the key.
- Each table MUST represent a single entity or relationship. Mixing concerns (e.g., storing order and shipping details in the same row) is a design smell.
- Repeating groups (arrays of values in a single column) MUST be extracted into a child table unless the values are truly opaque and never individually queried.

```sql
-- Wrong: city/state repeated per order, subject to inconsistency
CREATE TABLE orders (
  id           bigint PRIMARY KEY,
  customer_id  bigint,
  customer_city text,
  customer_state text
);

-- Correct: city/state owned by customers, referenced by FK
CREATE TABLE customers (
  id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  city  text,
  state text
);
CREATE TABLE orders (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id bigint NOT NULL REFERENCES customers(id) ON DELETE RESTRICT
);
```

---

## Denormalization

- Denormalization SHOULD only be introduced after a profiled performance problem, not in anticipation of one.
- When denormalizing, the source of truth MUST remain in the normalized table. Derived columns are caches.
- Counter caches (a precomputed `comments_count` on `posts`) MAY be used when aggregate queries on hot tables are too slow. They MUST be kept consistent via triggers or application logic.
- Materialized views MAY be used to cache expensive aggregations. They MUST be refreshed on a schedule or via trigger.
- Document every denormalization decision: what is cached, why, and how it is kept consistent.

```sql
-- Counter cache example
ALTER TABLE posts ADD COLUMN comments_count int NOT NULL DEFAULT 0;

-- Keep consistent via trigger
CREATE OR REPLACE FUNCTION update_post_comments_count()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE posts SET comments_count = comments_count + 1 WHERE id = NEW.post_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE posts SET comments_count = comments_count - 1 WHERE id = OLD.post_id;
  END IF;
  RETURN NULL;
END;
$$;
CREATE TRIGGER comments_count_trigger
AFTER INSERT OR DELETE ON comments
FOR EACH ROW EXECUTE FUNCTION update_post_comments_count();
```

---

## Migrations

- Every schema change MUST be made via a migration file committed to version control. Direct DDL changes to production are forbidden.
- Migrations MUST be idempotent where possible. Use `IF NOT EXISTS` / `IF EXISTS` for `CREATE` and `DROP` statements. For constraints, use the `DO` block pattern (see Constraints).
- Multi-row DML inside a migration MUST be wrapped in a transaction.
- Each migration MUST do one logical thing. Mixing unrelated schema changes makes rollback harder and diffs unreadable.
- Migrations SHOULD be written to be reversible. Include a down migration or at minimum document how to reverse it.
- `DROP COLUMN` and `DROP TABLE` MUST NOT be run in the same migration that removes application references. Deploy the application change first, then clean up the schema.

```sql
-- Safe: additive, idempotent
ALTER TABLE orders ADD COLUMN IF NOT EXISTS notes text;

-- Safe: create index concurrently (no table lock)
CREATE INDEX CONCURRENTLY IF NOT EXISTS orders_customer_id_idx
  ON orders (customer_id);

-- Multi-row DML in a transaction
BEGIN;
  UPDATE products SET status = 'archived' WHERE discontinued = true;
COMMIT;
```

---

## Backward Compatibility

- Columns MUST NOT be renamed or dropped in the same deployment that removes application references. Use a two-step migration: first deploy the app ignoring the old column, then drop it in a follow-up migration.
- Adding a new `NOT NULL` column to a large table MUST supply a `DEFAULT` so the migration does not require a full table rewrite or lock. Remove the default afterward if not needed.
- Adding a `NOT NULL` constraint to an existing nullable column MUST be done in two steps: backfill nulls, then add the constraint. Adding it in one step on a live table causes a full table scan and a lock.
- Index creation on large tables MUST use `CREATE INDEX CONCURRENTLY` to avoid locking writes.

```sql
-- Step 1: add column with default (no lock)
ALTER TABLE users ADD COLUMN tier text NOT NULL DEFAULT 'free';

-- Step 2 (later migration): drop the default if not desired going forward
ALTER TABLE users ALTER COLUMN tier DROP DEFAULT;

-- Adding NOT NULL to an existing column safely
-- Step 1: backfill
UPDATE users SET preferences = '{}' WHERE preferences IS NULL;
-- Step 2: add constraint (fast — no nulls remain)
ALTER TABLE users ALTER COLUMN preferences SET NOT NULL;
```

---

## Performance

- Use `EXPLAIN (ANALYZE, BUFFERS)` to diagnose slow queries before adding indexes or restructuring queries. Never guess.
- Paginate large result sets using keyset (cursor) pagination, not `OFFSET`. `OFFSET N` scans and discards N rows; performance degrades linearly with page depth.
- Avoid `SELECT *` in views and production queries. Select only the columns you need.
- Avoid executing `COUNT(*)` inside loops. Use counter caches or aggregate once outside the loop.
- Tables exceeding ~100 million rows SHOULD be partitioned by a natural dimension (usually time). Partitioning enables partition pruning on queries and instant partition drops instead of slow `DELETE`.
- Queries returning results to users MUST include an `ORDER BY` clause. Without it, row order is undefined and non-deterministic.

```sql
-- Diagnose a slow query
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders
WHERE customer_id = 123 AND status = 'pending';

-- Keyset pagination (correct)
-- Page 1
SELECT * FROM products ORDER BY id LIMIT 20;
-- Page 2 (last_id = 20 from previous page)
SELECT * FROM products WHERE id > 20 ORDER BY id LIMIT 20;

-- OFFSET pagination (wrong on large tables)
SELECT * FROM products ORDER BY id LIMIT 20 OFFSET 100000;  -- scans 100,000 rows

-- Partition a large time-series table
CREATE TABLE events (
  id         bigint GENERATED ALWAYS AS IDENTITY,
  created_at timestamptz NOT NULL,
  payload    jsonb
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2025_01 PARTITION OF events
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Drop old data instantly
DROP TABLE events_2024_01;
```
