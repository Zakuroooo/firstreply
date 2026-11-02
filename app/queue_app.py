"""FirstReply agent queue: urgent tickets first, a suggested queue and draft, and a human who decides.

Run: streamlit run app/queue_app.py
Needs outputs/eval_predictions.csv (made by `make evals`). An LLM draft is used only if GROQ_API_KEY is
set or the draft is cached; otherwise a safe template draft is shown and labelled as such.
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from firstreply import db, hitl, llm  # noqa: E402
from firstreply.labels import QUEUES  # noqa: E402

DB_PATH = Path(os.environ.get("FIRSTREPLY_DB", ROOT / "app" / "approvals.db"))
DRAFT_MODEL = "openai/gpt-oss-120b"
LEVEL_COLOUR = {"P1": "red", "P2": "orange", "P3": "gray"}

st.set_page_config(page_title="FirstReply queue", layout="wide")


@st.cache_data
def load_queue(model_column):
    preds_path = ROOT / "outputs" / "eval_predictions.csv"
    if not preds_path.exists():
        return None
    preds = pd.read_csv(preds_path)
    tickets = pd.read_csv(ROOT / "evalset" / "tickets.csv")
    t = tickets.merge(preds[["eval_id", model_column]], on="eval_id")
    return hitl.build_queue(t, t[model_column], db.SLA_MINUTES)


def get_draft(text, brand, queue):
    """LLM draft when we can make or reuse one; template otherwise. Returns (draft, source)."""
    messages = [{"role": "system", "content": llm.DRAFT_RULES.format(brand=brand, queue=queue)},
                {"role": "user", "content": text or "(empty message)"}]
    if llm.has_key() or llm.is_cached(DRAFT_MODEL, messages, json_mode=False, max_tokens=400):
        try:
            return llm.draft_reply(DRAFT_MODEL, text, brand, queue)["draft"], "LLM draft (gpt-oss-120b)"
        except Exception as e:  # network or rate limit: fall back, never block the agent
            return hitl.template_draft(queue), f"template (LLM failed: {type(e).__name__})"
    return hitl.template_draft(queue), "template (no LLM key)"


log = hitl.ApprovalLog(DB_PATH)
st.title("FirstReply - agent queue")
st.caption("Suggestions only. Nothing is sent until an agent approves or edits it. "
           f"Urgency: rules first, AI may only raise it. SLA = first reply within {db.SLA_MINUTES} min.")

with st.sidebar:
    agent = st.text_input("Agent name", value="agent_1")
    preds_cols = []
    p = ROOT / "outputs" / "eval_predictions.csv"
    if p.exists():
        preds_cols = [c for c in pd.read_csv(p, nrows=1).columns
                      if c not in ("eval_id", "brand", "clean_text", "label", "urgent")]
    options = preds_cols or ["tfidf_logreg"]
    # Open on the most accurate model (gpt-oss-120b, 72.3% on the test set) when its predictions exist.
    default = next((i for i, c in enumerate(options) if "120b" in c), 0)
    model_column = st.selectbox("Suggestion model", options, index=default)
    st.subheader("Eval loop")
    decisions = log.decisions()
    stats = hitl.loop_stats(decisions)
    for k, v in stats.items():
        st.write(f"**{k}**: {v}")
    if not decisions.empty:
        st.download_button("Download corrected labels", hitl.corrected_labels(decisions).to_csv(index=False),
                           "corrected_labels.csv")

queue = load_queue(model_column)
if queue is None:
    st.error("No predictions yet. Run `make evals` first (it writes outputs/eval_predictions.csv).")
    st.stop()

pending = queue[~queue.eval_id.isin(log.done_ids())]
c1, c2, c3 = st.columns(3)
c1.metric("Waiting", len(pending))
c2.metric("P1 waiting", int((pending.level == "P1").sum()))
c3.metric("Handled", len(queue) - len(pending))

if pending.empty:
    st.success("Queue empty.")
    st.stop()

t = pending.iloc[0]
if st.session_state.get("ticket") != t.eval_id:
    st.session_state.ticket = t.eval_id
    st.session_state.started = time.time()

st.subheader(f":{LEVEL_COLOUR[t.level]}[{t.level}] ticket {t.eval_id} - {t.brand}")
st.write(f"> {t.clean_text}")
answered = f"real first reply took {t.frt_minutes:.0f} min" if pd.notna(t.frt_minutes) else "never answered"
st.caption(f"why {t.level}: {t.reasons} | sentiment {t.sentiment} | created {t.created_at} UTC | {answered}")

final_queue = st.selectbox("Queue", QUEUES, index=QUEUES.index(t.suggested_queue),
                           help=f"Model suggested: {t.suggested_queue}")
draft, source = get_draft(t.clean_text, t.brand, final_queue)
st.caption(f"Draft source: {source}")
reply = st.text_area("Reply (edit freely)", value=draft, height=120, key=f"reply_{t.eval_id}_{final_queue}")

b1, b2 = st.columns(2)
if b1.button("Approve and send", type="primary"):
    action = log.log(agent, t.eval_id, t.suggested_queue, final_queue, draft, reply,
                     time.time() - st.session_state.started)
    st.toast(f"Logged: {action}")
    st.rerun()
if b2.button("Reject draft (reply by hand later)"):
    log.log(agent, t.eval_id, t.suggested_queue, final_queue, draft, "", time.time() - st.session_state.started,
            action="rejected")
    st.rerun()

st.divider()
st.write("Up next")
st.dataframe(pending.iloc[1:21][["eval_id", "level", "brand", "suggested_queue", "clean_text"]],
             hide_index=True, width="stretch")
