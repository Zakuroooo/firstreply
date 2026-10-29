"""Make the LLM calls the evals need, one model per process, so the two models run in parallel.

Usage: python scripts/warm_llm_cache.py small|large
Groq's free tier allows ~8K tokens/minute and 200K tokens/day per model; the client waits on 429s.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from firstreply import evals, llm  # noqa: E402

DRAFT_TICKETS = 60  # drafts for the first 60 test tickets, used by the demo queue


def main(which):
    dev, test = evals.load_evalset()
    examples, example_ids = evals.few_shot_examples(dev)
    dev_rest = dev[~dev.eval_id.isin(example_ids)]
    if which == "small":
        jobs = [(test.clean_text, ()), (dev_rest.clean_text, ()), (dev_rest.clean_text, examples)]
        model = evals.SMALL
    else:
        jobs = [(test.clean_text, ()), (evals.load_holdout().clean_text, ())]
        model = evals.LARGE
    for texts, ex in jobs:
        for i, t in enumerate(texts):
            llm.triage(model, t, ex)
            if i % 50 == 0:
                print(which, i, flush=True)
    if which == "large":
        for r in test.head(DRAFT_TICKETS).itertuples():
            queue = llm.triage(model, r.clean_text)["queue"]
            llm.draft_reply(model, r.clean_text, r.brand, queue)
    print(which, "done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
