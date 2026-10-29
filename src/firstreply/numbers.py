"""outputs/numbers.json is the single source of truth for every number in the docs and resume.

Each script writes its own section; nothing is typed by hand.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "outputs" / "numbers.json"


def load():
    return json.loads(PATH.read_text()) if PATH.exists() else {}


def save_section(name, values):
    data = load()
    data[name] = values
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
