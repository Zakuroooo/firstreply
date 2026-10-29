"""LLM triage through Groq's OpenAI-compatible API, with a disk cache so evals re-run for free.

The key is read from the GROQ_API_KEY environment variable (or .env). It is never logged.
Every call is cached in outputs/llm_cache/<model>.jsonl keyed by (model, prompt). If a result is cached,
no key is needed - that is how CI and the demo reproduce the numbers.
"""
import hashlib
import json
import os
import time

import requests

from firstreply import db
from firstreply.labels import QUEUES

API = "https://api.groq.com/openai/v1/chat/completions"
CACHE_DIR = db.ROOT / "outputs" / "llm_cache"  # one JSONL file per model

# USD per 1M tokens, from console.groq.com/docs/models, checked 2026-10-29
PRICES = {
    "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30},
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60},
}

GUIDE = """Route the customer-support tweet to ONE queue:
delivery: where is my order, late/missed/misdelivered, courier, delivery options
order_change: place, change or cancel an order; change shipping address
refund_return: refund, return, exchange; damaged/wrong/faulty/missing/expired item the customer wants fixed
billing_payment: payment fails, unknown or wrong charge, invoice, discount, price, fees, payment methods
account: login, password, locked/hacked/suspended, suspicious activity, account details, SIM, plans, subscriptions
complaint_feedback: venting, praise or suggestion with nothing specific to fix
talk_to_human: "check my DM", how to contact support, can't get through, vague "please help"
other: app/site bugs, network, streaming, stock or product questions, off-topic, unclear
Any language, emoji, slang or Hinglish. urgent = fraud or money taken, safety/health risk, locked or hacked account, legal threat, or stuck right now."""

OUTPUT = 'Reply with JSON only: {"queue": "<one queue name>", "urgent": true|false}'

_caches = {}


def _cache_file(model):
    return CACHE_DIR / (model.replace("/", "__") + ".jsonl")


def _load_cache(model):
    if model not in _caches:
        _caches[model] = {}
        if _cache_file(model).exists():
            for line in _cache_file(model).read_text().splitlines():
                row = json.loads(line)
                _caches[model][row["key"]] = row
    return _caches[model]


def _key(model, messages, extra):
    raw = json.dumps([model, messages, extra], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _api_key(required=True):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        env = db.ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("GROQ_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key and required:
        raise RuntimeError("GROQ_API_KEY not set and result not in cache")
    return key


def has_key():
    return bool(_api_key(required=False))


def is_cached(model, messages, json_mode=True, reasoning_effort="low", max_tokens=600):
    """True if this exact call is already in the cache (same arguments as chat())."""
    extra = {"json": json_mode, "effort": reasoning_effort, "max_tokens": max_tokens}
    return _key(model, messages, extra) in _load_cache(model)


def chat(model, messages, json_mode=True, reasoning_effort="low", max_tokens=600):
    """One chat call. Returns dict(text, input_tokens, output_tokens, latency_ms, cached)."""
    extra = {"json": json_mode, "effort": reasoning_effort, "max_tokens": max_tokens}
    key = _key(model, messages, extra)
    cache = _load_cache(model)
    if key in cache:
        return {**cache[key], "cached": True}

    body = {"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort, "include_reasoning": False}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {_api_key()}"}
    for attempt in range(6):
        start = time.perf_counter()
        r = requests.post(API, json=body, headers=headers, timeout=60)
        latency = (time.perf_counter() - start) * 1000
        if r.status_code == 429 or r.status_code >= 500:  # rate limit / server busy: wait and retry
            wait = float(r.headers.get("retry-after", 2 ** attempt))
            time.sleep(min(wait, 60))
            continue
        if r.status_code == 400 and json_mode and "json" in r.text.lower():
            # model produced invalid JSON; record it as a failure instead of crashing
            row = {"key": key, "text": "", "input_tokens": 0, "output_tokens": 0, "latency_ms": latency,
                   "error": "invalid_json"}
            break
        r.raise_for_status()
        data = r.json()
        row = {"key": key, "text": data["choices"][0]["message"]["content"] or "",
               "input_tokens": data["usage"]["prompt_tokens"],
               "output_tokens": data["usage"]["completion_tokens"], "latency_ms": round(latency, 1)}
        break
    else:
        raise RuntimeError("Groq kept rate-limiting; try again later")
    cache[key] = row
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with _cache_file(model).open("a") as f:
        f.write(json.dumps(row) + "\n")
    return {**row, "cached": False}


def triage_messages(ticket, examples=()):
    """Build the prompt. `examples` = [(text, queue, urgent)] for few-shot; empty for zero-shot."""
    system = GUIDE
    if examples:  # compact one-line examples inside the system prompt (cheaper than extra chat turns)
        system += "\nExamples:\n" + "\n".join(
            f'"{t[:120]}" -> {q}{", urgent" if u else ""}' for t, q, u in examples)
    messages = [{"role": "system", "content": system + "\n" + OUTPUT}]
    messages.append({"role": "user", "content": ticket or "(empty message)"})
    return messages


def parse(text):
    """Read the model's JSON. Anything malformed or outside the queue list becomes "other"."""
    try:
        data = json.loads(text)
        queue = str(data.get("queue", "")).strip().lower()
        urgent = data.get("urgent", False)
        # a string "false" is truthy in Python, so read strings explicitly
        urgent = urgent.strip().lower() == "true" if isinstance(urgent, str) else bool(urgent)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return "other", False, False
    if queue not in QUEUES:
        return "other", urgent, False
    return queue, urgent, True


def cost_usd(model, input_tokens, output_tokens):
    p = PRICES[model]
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


def triage(model, ticket, examples=()):
    out = chat(model, triage_messages(ticket, examples))
    queue, urgent, valid = parse(out["text"])
    return {"queue": queue, "urgent": urgent, "valid_json": valid,
            "input_tokens": out["input_tokens"], "output_tokens": out["output_tokens"],
            "latency_ms": out["latency_ms"], "cost_usd": cost_usd(model, out["input_tokens"], out["output_tokens"])}


DRAFT_RULES = """You write a FIRST REPLY for a human support agent to check before it is sent. Brand: {brand}. Queue: {queue}.
Rules: 2-3 short sentences, friendly and plain. Acknowledge the problem. Ask the customer to send a private
message with the order or account reference if needed. Never promise a refund, date or outcome. Never ask for
passwords or full card numbers. Never invent policies. No hashtags. Reply in the customer's language."""


def draft_reply(model, ticket, brand, queue):
    messages = [{"role": "system", "content": DRAFT_RULES.format(brand=brand, queue=queue)},
                {"role": "user", "content": ticket or "(empty message)"}]
    out = chat(model, messages, json_mode=False, max_tokens=400)
    return {"draft": out["text"].strip(), "cost_usd": cost_usd(model, out["input_tokens"], out["output_tokens"]),
            "latency_ms": out["latency_ms"]}
