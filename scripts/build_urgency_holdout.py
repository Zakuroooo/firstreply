"""Fresh 150 tweets (not in the eval set) to test the urgency rules on text not seen while writing them.

The rules in src/firstreply/urgency.py were frozen before this sample was drawn and labelled.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from firstreply import db, text  # noqa: E402

BRANDS = ["AmazonHelp", "ArgosHelpers", "AskTarget", "AskeBay", "AskPayPal", "Tesco", "UPSHelp",
          "SpotifyCares", "airtel_care", "sainsburys", "marksandspencer", "Morrisons"]


def main():
    con = db.connect()
    db.run(con, "01_tickets")
    used = set(pd.read_csv(db.ROOT / "evalset" / "tickets.csv").ticket_id)
    t = con.sql("SELECT ticket_id, brand, text FROM tickets WHERE brand IS NOT NULL").df()
    t = t[t.brand.isin(BRANDS) & ~t.ticket_id.isin(used)]
    t["clean_text"] = t.text.map(text.clean)
    t = t[t.clean_text.str.len() > 0].sample(150, random_state=2024).reset_index(drop=True)
    t.insert(0, "holdout_id", range(1, len(t) + 1))
    t[["holdout_id", "ticket_id", "brand", "clean_text"]].to_csv(db.ROOT / "evalset" / "urgency_holdout.csv", index=False)


if __name__ == "__main__":
    main()
