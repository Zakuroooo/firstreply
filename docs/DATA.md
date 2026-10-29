# Data

| Dataset | What it gives us | Licence | Where it comes from |
|---|---|---|---|
| Customer Support on Twitter (Thought Vector, Kaggle) | 2,811,774 real tweets between customers and ~108 brands, with timestamps and reply links (2017) | CC BY-NC-SA 4.0 - **non-commercial use only**, share-alike | Kaggle `thoughtvector/customer-support-on-twitter`; if no Kaggle token, the identical `twcs.csv` re-uploaded at Hugging Face `SunidhiSriram/twcs` |
| Bitext customer-support intents | ~27K tidy, synthetic customer questions with 27 intents | CDLA-Sharing 1.0 | Hugging Face `bitext/Bitext-customer-support-llm-chatbot-training-dataset` |

Neither file is in git (`raw/`, `data/` are ignored). `make data` downloads both, converts the tweets to
Parquet and runs `scripts/verify_data.py`, which checks:
1. the tweet count is exactly 2,811,774 (the Kaggle file), and
2. all 550 tweets in `evalset/` (sampled from the original Kaggle download) are found with identical text.
So a mirror copy is only accepted if it matches the original.

## What we built from it
- **Tickets** (`sql/01_tickets.sql`): an inbound tweet that is not a reply to anything, created between
  Mon 9 Oct and Sun 3 Dec 2017 (8 full weeks; earlier days are thin because the scrape was ramping up).
- **First response**: the earliest brand tweet that replies directly to the ticket.
- **Eval set** (`evalset/tickets.csv`): 400 opening tweets from 12 retail, delivery, payments and telecom brands
  (fixed per-brand counts, seed 7), split 100 dev / 300 test. Labels in `evalset/labels.csv`
  (see `docs/LABEL-GUIDE.md`).
- **Urgency hold-out** (`evalset/urgency_holdout.csv`): 150 different tweets from the same brands (seed 2024),
  labelled urgent yes/no only.

The eval files store cleaned text (handles masked as `@user`, links as `<url>`), which is less personal than
the raw tweets. They are still derived from the Twitter dataset, so the same non-commercial licence applies.

## Known gaps
- Twitter only. No email, chat, phone, or resolution data; we measure **first** response, not resolution.
- Only brand replies that are in the scrape count. A ticket with no reply in the data is "unanswered".
- All times are UTC.
- 2017 data: good for showing the method, not a statement about any brand today.
- Bitext is synthetic and tidy; real tweets are not. That gap is a finding, not a bug (see EVALS.md).
