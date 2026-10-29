-- 03: When do customers wait longest? FRT and breach rate by hour of day and weekday (UTC).
SELECT dayname(created_at) AS weekday,
       isodow(created_at) AS dow,
       hour(created_at) AS hour_utc,
       count(*) AS tickets,
       round(median(frt_minutes), 1) AS median_frt_min,
       round(quantile_cont(frt_minutes, 0.9), 1) AS p90_frt_min,
       round(100.0 * avg((frt_minutes > getvariable('sla_minutes'))::INT), 1) AS breach_pct
FROM tickets
WHERE frt_minutes IS NOT NULL AND frt_minutes >= 0
GROUP BY ALL
ORDER BY dow, hour_utc;
