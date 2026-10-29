# One command per step. `make all` rebuilds every number in outputs/numbers.json from the raw data.
PY ?= python
export PYTHONPATH := src

.PHONY: all data bitext sla evals roi test app

all: data sla evals roi

data:            ## download both datasets, convert tweets to Parquet, check the copy is complete
	$(PY) scripts/download_data.py
	$(PY) scripts/to_parquet.py
	$(PY) scripts/verify_data.py

bitext:          ## only the Bitext training data (enough for `make evals`)
	$(PY) scripts/download_data.py --bitext-only

sla:             ## first-response time, breach rate, backlog, forecast, staffing
	$(PY) -m firstreply.analytics

evals: bitext    ## TF-IDF + LR vs LLMs on the same 300 held-out tweets (LLM rows need a key or the cache)
	$(PY) -m firstreply.evals

roi:             ## agent-hours saved, low/base/high + sensitivity (needs sla and evals first)
	$(PY) -m firstreply.roi

test:
	$(PY) -m pytest -q

app:
	streamlit run app/queue_app.py
