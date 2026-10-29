-- 01: Build one row per support ticket.
-- A "ticket" = a customer tweet that starts a conversation (inbound, not a reply to anything).
-- First response = the earliest company tweet that replies directly to it.
CREATE OR REPLACE TABLE tickets AS
-- company replies that answer a tweet
WITH replies AS (
    SELECT in_response_to_tweet_id AS ticket_id,
           author_id AS brand,
           created_at AS reply_at
    FROM tweets
    WHERE NOT inbound AND in_response_to_tweet_id IS NOT NULL
),
-- the first company reply per ticket (earliest one wins)
first_reply AS (
    SELECT ticket_id, arg_min(brand, reply_at) AS brand, min(reply_at) AS first_reply_at
    FROM replies
    GROUP BY ticket_id
),
-- customer tweets that open a conversation, inside the analysis window
opens AS (
    SELECT tweet_id AS ticket_id, author_id AS customer_id, created_at, text
    FROM tweets
    WHERE inbound
      AND in_response_to_tweet_id IS NULL
      AND created_at >= getvariable('window_start')
      AND created_at <  getvariable('window_end')
)
SELECT o.ticket_id, o.customer_id, o.created_at, o.text,
       f.brand, f.first_reply_at,
       date_diff('second', o.created_at, f.first_reply_at) / 60.0 AS frt_minutes
FROM opens o
LEFT JOIN first_reply f USING (ticket_id);
