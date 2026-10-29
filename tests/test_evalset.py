"""Guard the committed eval set: if these change, every reported number changes."""
import pandas as pd

from firstreply import db, evals
from firstreply.labels import QUEUES


def test_evalset_shape_and_labels():
    dev, test = evals.load_evalset()
    assert (len(dev), len(test)) == (100, 300)
    assert set(dev.label) | set(test.label) <= set(QUEUES)
    assert dev.eval_id.is_unique and test.eval_id.is_unique


def test_holdout_is_separate_from_evalset():
    ev = pd.read_csv(db.ROOT / "evalset" / "tickets.csv")
    hold = evals.load_holdout()
    assert len(hold) == 150
    assert not set(ev.ticket_id) & set(hold.ticket_id)


def test_few_shot_examples_come_from_dev_only():
    dev, test = evals.load_evalset()
    examples, ids = evals.few_shot_examples(dev)
    assert ids <= set(dev.eval_id) and not ids & set(test.eval_id)
    assert len(examples) == dev.label.nunique()
