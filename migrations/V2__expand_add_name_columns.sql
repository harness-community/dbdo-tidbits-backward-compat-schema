-- V2: EXPAND — add first_name and last_name columns (nullable)
--
-- This is the backward-compatible step.
-- The old 'name' column is kept — v1 of the app continues to work.
-- The new columns are nullable so existing rows are not broken.
-- Both app v1 (reads 'name') and app v2 (reads 'first_name'/'last_name')
-- can run against this schema simultaneously during a rolling deployment.

ALTER TABLE users ADD COLUMN first_name VARCHAR(255);
ALTER TABLE users ADD COLUMN last_name  VARCHAR(255);
