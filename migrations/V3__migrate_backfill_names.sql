-- V3: MIGRATE — backfill first_name and last_name from existing name data
--
-- Safe to run while both app v1 and v2 are live.
-- v1 still reads/writes 'name'. v2 reads 'first_name'/'last_name'.
-- After this migration, new rows written by v2 will have all three columns populated.

UPDATE users
SET
    first_name = SPLIT_PART(name, ' ', 1),
    last_name  = CASE
                   WHEN POSITION(' ' IN name) > 0
                   THEN SUBSTRING(name FROM POSITION(' ' IN name) + 1)
                   ELSE ''
                 END
WHERE first_name IS NULL;

-- Also add a trigger so any future v1 writes to 'name' auto-populate the new columns
CREATE OR REPLACE FUNCTION sync_name_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.name IS NOT NULL AND NEW.first_name IS NULL THEN
        NEW.first_name := SPLIT_PART(NEW.name, ' ', 1);
        NEW.last_name  := CASE
                            WHEN POSITION(' ' IN NEW.name) > 0
                            THEN SUBSTRING(NEW.name FROM POSITION(' ' IN NEW.name) + 1)
                            ELSE ''
                          END;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_name
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION sync_name_columns();
