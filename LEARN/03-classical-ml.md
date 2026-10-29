# 03 - The classical model: TF-IDF + logistic regression

## The job
Read a ticket, output one of 8 queues: delivery, order_change, refund_return, billing_payment, account,
complaint_feedback, talk_to_human, other. This is **text classification**.

## Train, dev, test
- **Train**: data the model learns from (Bitext, about 25,000 tidy example questions).
- **Dev**: data we use to make choices (here: the "other" threshold, and the few-shot examples). 100 real tweets.
- **Test**: data we only use once, at the end, to report the score. 300 real tweets.
If you tune on test, your score is a lie: you have seen the exam paper.

> Hinglish: Test set exam paper hai - usse dekh ke tayyari karoge toh marks fake honge.

## TF-IDF (turning words into numbers)
A model cannot read words, only numbers. TF-IDF gives every word (and every 2-word phrase) a score per ticket:
- **TF (term frequency)**: how often the word appears in this ticket.
- **IDF (inverse document frequency)**: how rare the word is across all tickets. "the" is everywhere, so low.
  "refund" is rarer, so high.
TF x IDF = high for words that are frequent here but rare in general - the words that tell you the topic.

> Hinglish: TF-IDF un words ko zyada weight deta hai jo is ticket mein baar baar aaye par baaki tickets mein kam - jaise "refund".

## Logistic regression
For each queue, the model learns a weight for every word. "refund" pushes up refund_return, "parcel" pushes
up delivery. It adds up the weights and turns the total into a probability for each queue (they add to 1).
The queue with the highest probability wins.

It is fast (under a millisecond per ticket on a laptop), free to run, and you can open it and see which words
drove the answer. That is why it is the baseline.

> Hinglish: Logistic regression har word ko weight deta hai, sab jod ke har queue ki probability nikalta hai.

## The "other" threshold
Bitext has no "other" class, but real tweets often are "other" (app bugs, network, random chat). So if the
top probability is below a threshold, we say "other". The threshold is picked on **dev**, never test.

## Domain shift (the main lesson)
Bitext text is tidy: "I want to cancel my order". Real tweets are messy: typos, slang, emoji, sarcasm,
several languages, "@user check DM". A model can score very high on held-out Bitext and much lower on real
tweets. That gap is **domain shift**. It is why a 99% score on tidy data is not a production number.

> Hinglish: Saaf-suthre data pe 99% aana easy hai; asli customer ke messy tweet pe score gir jaata hai - isko domain shift kehte hain.
