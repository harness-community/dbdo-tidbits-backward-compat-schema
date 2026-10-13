# DBDO | Tidbits | Backward-Compatible Schema Changes + Feature Flags

> **Bite-sized how-to** | ~30 min setup

---

## What is Backward-Compatible Schema Change?

A backward-compatible schema change is a database migration that allows the old and new versions of an application to run against the same database simultaneously. During a rolling deployment, v1 and v2 pods are both live at the same time — the schema must work for both.

The industry-standard approach is the **Expand → Migrate → Contract** pattern:
- **Expand** — add new columns alongside the old ones (safe while v1 is live)
- **Migrate** — backfill data and install a sync trigger to keep columns consistent
- **Contract** — drop the old column only after v2 is fully deployed

A Harness FME feature flag controls the progressive rollout to v2 and enables instant rollback — without any redeployment.

---

## What does this Tidbit demonstrate?

An e-commerce store upgrades from storing a user's full name in a single `name` column (v1) to separate `first_name` and `last_name` columns (v2).

- **Harness DBDO pipeline** — four stages, each applying one Liquibase changeset with a shell script proving the DB state after each migration
- **Feature flag `use-split-name`** — controls which code path the app uses, enabling progressive rollout and instant rollback
- **Sync trigger** — keeps all three columns consistent during the transition window so writes from v1 and v2 are both safe

**The demo:** Run the Harness DBDO pipeline stage by stage → toggle the feature flag → run the Contract stage → watch `name` disappear.

---

## Repository Structure

```
dbdo-tidbits-backward-compat-schema/
├── migrations/
│   ├── expand/
│   │   ├── v1/changelog.yaml   — Create users table (name column)
│   │   ├── v2/changelog.yaml   — Add first_name, last_name (nullable)
│   │   └── v3/changelog.yaml   — Backfill data + sync trigger
│   └── contract/
│       └── changelog.yaml      — Drop name column (point of no return)
├── app/
│   ├── app.py                  — Flask app with use-split-name flag
│   ├── requirements.txt
│   └── flags.yaml              — Localhost mode flag config
├── harness/
│   └── pipeline.yaml           — Harness DBDO pipeline (4 stages)
└── docker-compose.yml
```

---

## Prerequisites

- A Harness account with Database DevOps and FME modules enabled
- A PostgreSQL database (local, cloud, or any managed provider)
- Python 3.11+ (for the Flask app demo)
- A Harness Kubernetes delegate running in your environment

---

## Step 1 — Create the Feature Flag in Harness FME

1. Go to **Feature Management → Feature Flags → + Create feature flag**
2. **Name:** `use-split-name`
3. **Traffic Type:** `user`
4. Click **Create**
5. Click **Initiate Environment** on your production environment
6. Treatments: `on` = v2 schema (first_name/last_name), `off` = v1 schema (name)
7. **Default treatment:** `off`
8. Save

---

## Step 2 — Set Up PostgreSQL

Use any PostgreSQL database — local Docker, Neon, Supabase, RDS, or any managed provider.

Your connection string will look like:
```
postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:5432/YOUR_DB_NAME
```

For a quick free cloud option: [neon.tech](https://neon.tech) or [supabase.com](https://supabase.com)

For local Docker:
```bash
docker compose up postgres -d
```

---

## Step 3 — Set Up Harness DBDO

Create four DB Schemas in **Database DevOps → DB Schemas**:

| Schema Name | Identifier | Path to Changelog |
|---|---|---|
| `backward-compat-v1` | `backwardcompatv1` | `migrations/expand/v1/changelog.yaml` |
| `backward-compat-v2` | `backwardcompatv2` | `migrations/expand/v2/changelog.yaml` |
| `backward-compat-v3` | `backwardcompatv3` | `migrations/expand/v3/changelog.yaml` |
| `backward-compat-contract` | `backwardcompatcontract` | `migrations/contract/changelog.yaml` |

For each schema:
- **Migration Type:** Liquibase
- **Connector:** your GitHub connector pointing to this repo
- **DB Instance:** your PostgreSQL DB instance connector

---

## Step 4 — Run the Pipeline

1. Go to **Pipelines → backward-compat-migration**
2. Paste the YAML from `harness/pipeline.yaml` — update the placeholders (`YOUR_PROJECT_IDENTIFIER`, `YOUR_ORG_IDENTIFIER`, `YOUR_KUBERNETES_CONNECTOR`, `YOUR_DB_USER`, `YOUR_DB_HOST`, `YOUR_DB_NAME`)
3. Click **Run**

The pipeline has five stages:

| Stage | What happens |
|---|---|
| V1 Create Users Table | Creates `users` table — shell shows `id, name, email, created_at` |
| V2 Expand Add Name Columns | Adds `first_name`, `last_name` (nullable) — shell shows all 5 columns |
| V3 Migrate Backfill Sync Trigger | Backfills data + installs sync trigger — shell shows all 3 name columns populated |
| **Approve to Run Contract** | ⚠️ Pipeline pauses here — verify flag is ON for 100% before approving |
| V4 Contract Drop name Column | Drops `name` column — shell shows only `first_name`, `last_name` remain |

---

## Step 5 — Run the Flask App

```bash
cd app
pip install -r requirements.txt
```

Set your database connection and SDK key, then run:

```bash
DATABASE_URL="postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:5432/YOUR_DB_NAME" \
SDK_KEY=your_server_side_sdk_key \
python3 app.py
```

Visit [http://localhost:5001](http://localhost:5001)

> **Important:** Use the same database that the Harness DBDO pipeline ran migrations on — so the app reflects the same schema state.

**Local testing (no Harness connection):**
Leave `SDK_KEY` unset. Edit `flags.yaml` to set `treatment: "on"` or `treatment: "off"`.

---

## Step 6 — Toggle the Flag

When the pipeline pauses at the **Approve to Run Contract** gate, do the flag demo first:

1. Go to **Feature Management → Feature Flags → use-split-name**
2. Change targeting rule to `on` → Save
3. Refresh the browser → green banner — app now reads `first_name`/`last_name`
4. Toggle back to `off` → instant rollback to v1 behavior — no redeployment needed

---

## Step 7 — Approve and Run the Contract Stage

Once the flag is confirmed ON for 100% of traffic and no v1 instances remain:

1. Go back to the pipeline execution → click **Approve** on the approval gate
2. V4 Contract stage runs — shell script confirms `name` column dropped, sync trigger removed
3. v1 of the app will now break — that's correct and expected
4. The backward-compatibility window is closed

---

## Resources

- [Harness Database DevOps Documentation](https://developer.harness.io/docs/database-devops/)
- [Liquibase Documentation](https://docs.liquibase.com/)
- [Harness FME Documentation](https://developer.harness.io/docs/feature-management-experimentation/)
- [Semantic Versioning](https://semver.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
