-- 02: First-response time (FRT) and SLA breach rate per brand.
-- Only answered tickets have an FRT. Brands with fewer than 1,000 tickets are left out (too noisy).
SELECT brand,
       count(*) AS tickets,
       round(median(frt_minutes), 1) AS median_frt_min,
       round(quantile_cont(frt_minutes, 0.9), 1) AS p90_frt_min,
       -- breach = first reply came later than the SLA
       round(100.0 * avg((frt_minutes > getvariable('sla_minutes'))::INT), 1) AS breach_pct
FROM tickets
WHERE frt_minutes IS NOT NULL AND frt_minutes >= 0
GROUP BY brand
HAVING count(*) >= 1000
ORDER BY tickets DESC;
