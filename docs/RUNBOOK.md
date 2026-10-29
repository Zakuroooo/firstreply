# Runbook

## Run everything locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make test        # unit tests, no data needed
make all         # download data (~540 MB), verify it, SLA analytics, evals, ROI -> outputs/
make app         # agent queue at http://localhost:8501
```
`make evals` alone needs only Bitext (~20 MB). LLM rows use `outputs/llm_cache/`; to make new LLM calls put
`GROQ_API_KEY=...` in `.env` (git-ignored) or the environment. To use Kaggle instead of the mirror, put
`kaggle.json` in `~/.kaggle/`.

## Run everything in GitHub Actions (no laptop needed)
1. Optional: repo **Settings -> Secrets and variables -> Actions -> New repository secret**, name
   `GROQ_API_KEY`. Without it the LLM rows are skipped (or come from the cache).
2. **Actions -> ci -> Run workflow** (branch `main`, "reproduce" ticked).
3. The `reproduce` job downloads data, runs `make all` and the tests, and commits `outputs/` back with
   `[skip ci]`. Takes about 15-30 minutes.

## Deploy the agent queue (not done yet - steps only)
The app needs `outputs/eval_predictions.csv` (committed) and nothing secret. LLM drafts are optional.
Keep the GitHub repo private; the hosts below can read private repos once you grant access.

### Option A: Streamlit Community Cloud (free, simplest)
1. Sign in at share.streamlit.io with GitHub and allow access to `Zakuroooo/firstreply`.
2. **Create app** -> repo `Zakuroooo/firstreply`, branch `main`, main file `app/queue_app.py`.
3. **Advanced settings** -> Python 3.13. Secrets (optional): `GROQ_API_KEY = "..."`.
   Streamlit exposes secrets as environment variables, which `llm.py` reads.
4. Deploy. `requirements.txt` at the repo root is installed automatically.
5. Set the app to **private / viewers by invite** if the data licence or a recruiter demo needs it.
Note: the SQLite log lives on the app's disk and resets when the app restarts. That is fine for a demo; a
pilot needs a real database (Postgres) - change `ApprovalLog` only.

### Option B: any Docker host (Render, Railway, Fly.io, Hugging Face Spaces with Docker)
```bash
docker build -t firstreply .
docker run -p 8501:8501 -e GROQ_API_KEY=... firstreply   # key optional
```
On Render: New -> Web Service -> connect repo -> Runtime "Docker" -> port 8501 -> add `GROQ_API_KEY` as an
environment variable if wanted.

## When something breaks
| Symptom | Cause | Fix |
|---|---|---|
| `verify_data.py` fails | partial or different `twcs.csv` | delete `raw/twcs/` and re-run `make data` |
| `RuntimeError: GROQ_API_KEY not set` | uncached LLM call with no key | set the key, or accept that `evals` skips LLM rows |
| `RuntimeError: Groq kept rate-limiting` | free tier: ~8K tokens/min, 200K/day per model | wait; the cache keeps finished calls, re-run continues |
| App says "No predictions yet" | `outputs/eval_predictions.csv` missing | `make evals` |
| DuckDB out of memory | small machine | lower `memory_limit` in `db.py` / `to_parquet.py` |
