# 04 - LLMs and how to evaluate any classifier fairly

## LLM in one paragraph
A large language model reads text and predicts the next words. If we write instructions ("route this tweet
to one queue, reply in JSON"), it can classify without any training on our data.
- **Zero-shot**: only instructions.
- **Few-shot**: instructions plus a few solved examples (we use one per queue, taken from dev).

## Tokens, cost and latency
- A **token** is a piece of a word (about 4 characters of English). APIs charge per million tokens, with
  separate prices for input (prompt) and output (answer).
- **Cost per ticket** = input tokens x input price + output tokens x output price.
  We report **cost per 1,000 tickets** because that is how an ops manager budgets.
- **Latency** = time from sending the ticket to getting the answer. We report **p50** (normal) and **p95**
  (slow tail), same idea as FRT median and p90.

> Hinglish: Cost per ticket matlab ek ticket ko classify karne mein kitne paise lage - tokens x price.

## What an eval is
An **eval** is a fixed exam for a model: the same tickets, the same correct answers (labels), the same
scoring code, for every model. Rules we follow:
1. Labels are written **before** looking at any model output.
2. Every model sees the **same** 300 test tickets with the **same** cleaning.
3. Choices (threshold, examples) are made on dev, not test.
4. LLM answers are cached, so anyone can re-run the eval and get the same numbers.

> Hinglish: Eval ek fixed exam hai - sab models ko same sawaal, same answer key, same marking.

## Accuracy
Share of tickets put in the right queue. Easy to read, but it hides small classes: if 30% of tickets are
"complaint_feedback", a model that is good only at that class still looks OK.

## Precision and recall (for one class)
Take the class "urgent".
- **Recall**: of all truly urgent tickets, how many did we flag? (Did we miss any fraud?)
- **Precision**: of all tickets we flagged, how many were truly urgent? (Did we cry wolf?)
For urgency we care more about recall: missing fraud costs more than an agent glancing at a false alarm.

> Hinglish: Recall = asli urgent mein se kitne pakde. Precision = jo pakde unme se kitne sach mein urgent the.

## F1 and macro-F1
- **F1** combines precision and recall for one class (their harmonic mean).
- **Macro-F1** = average F1 over all 8 queues, each queue counted equally. A model that ignores small queues
  gets punished. That is why we report both accuracy and macro-F1.

## Confusion matrix
A table: rows = true queue, columns = predicted queue. The diagonal is correct. Off-diagonal cells show
**which** mistakes happen (for example refund tickets sent to delivery). See `outputs/eval_confusion_tfidf.csv`.

## Bootstrap 95% confidence interval
300 tickets is a small exam. If we had drawn a different 300, the score would move. Bootstrap: resample the
300 tickets with replacement 1,000 times, score each, and take the middle 95% of scores. If two models' ranges
overlap a lot, we cannot honestly say one is better.

> Hinglish: Confidence interval batata hai ki score kitna upar-neeche ho sakta tha agar tickets alag hote.

## Failure examples
Numbers say how often a model is wrong; examples say **why**. `outputs/eval_failures.csv` lists wrong answers
per model so a human can read them. Always read failures before trusting a score.
