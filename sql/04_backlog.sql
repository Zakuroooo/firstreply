-- 04: Backlog = tickets waiting for a first reply at the end of each hour.
-- A ticket is "waiting" at time h if it was created before h and its first reply came after h.
-- hours = every hour in the window
WITH hours AS (
    SELECT unnest(generate_series(getvariable('window_start') + INTERVAL 1 HOUR,
                                  getvariable('window_end'), INTERVAL 1 HOUR)) AS h
),
-- only answered tickets: unanswered ones are not in this dataset (see docs/DATA.md)
answered AS (
    SELECT created_at, first_reply_at FROM tickets WHERE frt_minutes >= 0
)
SELECT h AS hour_end,
       count(a.created_at) AS waiting
FROM hours
LEFT JOIN answered a ON a.created_at < h AND a.first_reply_at > h
GROUP BY h
ORDER BY h;
