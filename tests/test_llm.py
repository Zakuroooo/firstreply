import pytest

from firstreply import llm


@pytest.mark.parametrize("raw,expected", [
    ('{"queue": "delivery", "urgent": true}', ("delivery", True, True)),
    ('{"queue": "Delivery ", "urgent": "false"}', ("delivery", False, True)),
    ('{"queue": "shipping", "urgent": false}', ("other", False, False)),
    ("not json at all", ("other", False, False)),
    ("", ("other", False, False)),
    ("null", ("other", False, False)),
    ('["delivery"]', ("other", False, False)),
])
def test_parse_never_crashes(raw, expected):
    assert llm.parse(raw) == expected


def test_prompt_handles_empty_ticket_and_examples():
    msgs = llm.triage_messages("")
    assert msgs[-1]["content"] == "(empty message)"
    few = llm.triage_messages("hi", [("where is my parcel", "delivery", False)])
    assert "Examples:" in few[0]["content"]


def test_cost():
    # 1M input + 1M output tokens on gpt-oss-20b = 0.075 + 0.30
    assert llm.cost_usd("openai/gpt-oss-20b", 1_000_000, 1_000_000) == pytest.approx(0.375)


def test_uncached_call_without_key_fails_clearly(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(llm.db, "ROOT", tmp_path)  # no .env file here
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(llm, "_caches", {})
    assert not llm.has_key()
    msgs = llm.triage_messages("a ticket nobody has seen")
    assert not llm.is_cached("openai/gpt-oss-20b", msgs)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.chat("openai/gpt-oss-20b", msgs)


def test_cached_call_needs_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(llm, "_caches", {})
    model = "openai/gpt-oss-20b"
    msgs = llm.triage_messages("where is my parcel")
    key = llm._key(model, msgs, {"json": True, "effort": "low", "max_tokens": 600})
    llm._load_cache(model)[key] = {"key": key, "text": '{"queue":"delivery","urgent":false}',
                                   "input_tokens": 300, "output_tokens": 40, "latency_ms": 500.0}
    out = llm.triage(model, "where is my parcel")
    assert out["queue"] == "delivery" and out["cost_usd"] > 0
