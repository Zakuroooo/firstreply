"""Sample 400 real opening tweets from retail/delivery/payments brands for the triage eval set.

Labels are added by hand afterwards in evalset/labels.csv (see docs/LABEL-GUIDE.md), before any model is run.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from firstreply import db, text  # noqa: E402

PER_BRAND = {
    "AmazonHelp": 90, "ArgosHelpers": 30, "AskTarget": 30, "AskeBay": 30, "AskPayPal": 30, "Tesco": 30,
    "UPSHelp": 30, "SpotifyCares": 30, "airtel_care": 30, "sainsburys": 25, "marksandspencer": 25, "Morrisons": 20,
}
SEED = 7


def main():
    con = db.connect()
    db.run(con, "01_tickets")
    t = con.sql("SELECT ticket_id, brand, created_at, text, frt_minutes FROM tickets WHERE brand IS NOT NULL").df()
    t = t[t.brand.isin(PER_BRAND)]
    t["clean_text"] = t.text.map(text.clean)
    t = t[t.clean_text.str.len() > 0]
    parts = [g.sample(PER_BRAND[b], random_state=SEED) for b, g in t.groupby("brand")]
    s = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
    s["split"] = ["dev"] * 100 + ["test"] * 300
    s.insert(0, "eval_id", range(1, len(s) + 1))
    out = db.ROOT / "evalset" / "tickets.csv"
    s[["eval_id", "ticket_id", "brand", "created_at", "split", "clean_text", "frt_minutes"]].to_csv(out, index=False)
    print("wrote", out, len(s))


if __name__ == "__main__":
    main()
