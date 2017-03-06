DELETE FROM entry
USING (
  SELECT
    id,
    ROW_NUMBER() OVER (PARTITION BY feed_id ORDER BY retrieved DESC) AS row
  FROM entry
) AS numbered
WHERE entry.id = numbered.id
  AND (row > 2000 OR retrieved < CURRENT_DATE - INTERVAL '365 days');
