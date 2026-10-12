-- V4: CONTRACT — drop the old 'name' column and its sync trigger
--
-- ⚠️  ONLY run this migration after:
--   1. App v2 is fully deployed to 100% of traffic
--   2. No v1 instances remain running
--   3. The feature flag 'use-split-name' is ON for all users
--
-- Once this runs, v1 of the app will BREAK — it requires the 'name' column.
-- This is the point of no return for the backward compatibility window.

DROP TRIGGER IF EXISTS trg_sync_name ON users;
DROP FUNCTION IF EXISTS sync_name_columns();
ALTER TABLE users DROP COLUMN name;
