# Harness University Tidbit — DBDO: Backward-Compatible Schema Changes + Feature Flags

**Level:** DBDO 401 — Expert
**Module:** Database DevOps + Feature Management & Experimentation (FME)
**Stack:** PostgreSQL · Flyway · Python Flask · Harness FME SDK

---

## What This Tidbit Demonstrates

When you bump an application from **v1.0 to v2.0**, SemVer signals a breaking change. But your database schema must survive both versions simultaneously — during a rolling deployment, v1 and v2 pods run side-by-side against the same database.

This Tidbit shows the **Expand → Migrate → Contract** pattern: the only safe way to rename or restructure a column without breaking live traffic. A Harness FME feature flag controls which code path each instance uses, enabling a progressive rollout with instant rollback — no redeployment needed.

**The scenario:** An e-commerce store upgrades from storing a user's full name as a single `name` column (v1) to separate `first_name` and `last_name` columns (v2).

---

## The Pattern

```
V1 Schema:  users(id, name, email, created_at)
                       ^^^^
                  one column, one truth

V2 Schema:  users(id, name, first_name, last_name, email, created_at)
                       ^^^^  ^^^^^^^^^^  ^^^^^^^^^
                  kept for   new cols    new cols
                  v1 compat  (nullable)  (nullable)

V4 Schema:  users(id, first_name, last_name, email, created_at)
                       ^^^^^^^^^^  ^^^^^^^^^
                  name col removed after
                  all v1 traffic is gone
```

### Migration steps

| Migration | Action | Safe to run while v1 is live? |
|-----------|--------|-------------------------------|
| `V1` | Create `users` table with `name` column | — initial schema |
| `V2` | **Expand** — add `first_name`, `last_name` (nullable) | ✅ Yes |
| `V3` | **Migrate** — backfill new columns; add sync trigger | ✅ Yes |
| `V4` | **Contract** — drop `name` column | ❌ Only after 100% v2 |

---

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- A Harness account with FME enabled (or run in localhost mode)

---

## Setup

### 1. Start PostgreSQL

```bash
docker compose up postgres -d
```

### 2. Run Flyway migrations V1–V3 (Expand + Migrate)

```bash
docker compose up flyway
```

This applies migrations up to V3. The database now has both the old `name` column and the new `first_name`/`last_name` columns. A trigger keeps them in sync — any write to `name` auto-populates the new columns, and vice versa.

> **V4 is intentionally deferred.** Applying V4 drops the `name` column and ends backward compatibility. Run it only after the feature flag is at 100% and all v1 instances are gone.

### 3. Configure your SDK key

Open `app/app.py` and replace `YOUR_SERVER_SIDE_SDK_KEY` with your Harness FME Server-side SDK key.

Or set it as an environment variable:

```bash
export SDK_KEY=your_server_side_sdk_key
```

To run in **localhost mode** (no Harness connection), leave the key as `YOUR_SERVER_SIDE_SDK_KEY`. The app reads treatments from `app/flags.yaml`.

### 4. Create the feature flag in Harness FME

- Go to **Feature Management → Feature Flags → Create feature flag**
- Name: `use-split-name`
- Traffic type: `user`
- Treatments: `on` (v2 schema) and `off` (v1 schema)
- Default treatment: `off`

### 5. Run the app

```bash
cd app
pip install -r requirements.txt
python app.py
```

Visit [http://localhost:5001](http://localhost:5001)

---

## The Demo Flow

### Act 1 — v1 schema, flag OFF

The app starts with `use-split-name = off`. It reads from the `name` column. The banner shows **🔵 Flag OFF — using v1 schema**.

```bash
curl http://localhost:5001/api/users
# → users with "name" field populated
```

### Act 2 — Expand the schema (V2 + V3 migrations already applied)

Inspect the database — all three columns now exist:

```bash
docker exec ecommerce-db psql -U postgres -d ecommerce -c "\d users"
docker exec ecommerce-db psql -U postgres -d ecommerce -c "SELECT id, name, first_name, last_name FROM users;"
```

The old `name` column is still there. `first_name` and `last_name` are backfilled. The sync trigger keeps everything consistent.

### Act 3 — Toggle the flag ON (progressive rollout)

In Harness FME, change the targeting rule for `use-split-name` to `on`. Refresh the browser.

The banner switches to **🟢 Flag ON — using v2 schema**. The app now reads `first_name`/`last_name`. No redeployment. No downtime.

### Act 4 — Toggle back to OFF (instant rollback)

Toggle the flag back to `off`. The app immediately reverts to v1 behavior. Still no redeployment.

### Act 5 — Contract (V4)

Once you're confident 100% of traffic is on v2 and all v1 instances are gone:

```bash
docker compose run --rm flyway \
  -url=jdbc:postgresql://postgres:5432/ecommerce \
  -user=postgres -password=postgres \
  -locations=filesystem:/flyway/sql \
  migrate
```

This applies V4: drops the `name` column and removes the sync trigger. The schema is clean. v1 of the app would now break — that's intentional and expected.

---

## Project Structure

```
dbdo-tidbits-backward-compat-schema/
├── migrations/
│   ├── V1__create_users_table.sql         # Initial schema
│   ├── V2__expand_add_name_columns.sql    # Expand — add new columns
│   ├── V3__migrate_backfill_names.sql     # Migrate — backfill + sync trigger
│   └── V4__contract_drop_name.sql         # Contract — drop old column
├── app/
│   ├── app.py                             # Flask app with FME flag
│   ├── requirements.txt
│   ├── flags.yaml                         # Localhost mode flag config
│   └── Dockerfile
├── harness/
│   └── pipeline.yaml                      # Example Harness DBDO pipeline
├── docker-compose.yml
└── README.md
```

---

## Key Concepts

**Backward-compatible schema change** — A schema modification that allows the old and new versions of an application to run against the same database simultaneously.

**Expand-Migrate-Contract** — The three-phase pattern for safe schema evolution: add new structure (expand), move data (migrate), remove old structure (contract).

**Sync trigger** — A PostgreSQL trigger that keeps both the old and new columns consistent during the transition window, so writes from either app version are safe.

**Feature flag** — Controls which code path the app uses without a redeployment. Toggle ON for v2 schema reads, OFF to instantly revert to v1.

**SemVer** — Semantic Versioning. A v1→v2 major bump signals breaking changes. The schema pattern shown here is how you manage the database side of that transition safely.
