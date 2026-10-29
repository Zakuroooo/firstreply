-- 05: New tickets per hour for one brand (input to the forecast and staffing model).
WITH hours AS (
    SELECT unnest(generate_series(getvariable('window_start'),
                                  getvariable('window_end') - INTERVAL 1 HOUR, INTERVAL 1 HOUR)) AS hour_start
),
counts AS (
    SELECT date_trunc('hour', created_at) AS hour_start, count(*) AS tickets
    FROM tickets
    WHERE brand = getvariable('brand')
    GROUP BY 1
)
SELECT hour_start, coalesce(tickets, 0) AS tickets
FROM hours LEFT JOIN counts USING (hour_start)
ORDER BY hour_start;
