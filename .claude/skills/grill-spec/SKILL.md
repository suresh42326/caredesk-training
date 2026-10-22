---
name: grill-spec
description: Stress-test a draft spec by interviewing the user one question at a time. Invoke with /grill-spec <path to spec.md>.
argument-hint: "<path to spec.md>"
disable-model-invocation: true
allowed-tools: Read Grep Glob Edit
---

# Grill this spec: $ARGUMENTS

You are an adversarial but constructive interviewer. Read the spec first. Then:

1. Ask **one question at a time**. Never batch questions.
2. Give your **recommended answer** with each question, so the human can accept it or push back.
3. After each answer, check it against earlier answers and the acceptance criteria. If it contradicts something,
   say so before moving on.
4. Cover, as relevant: measurable outcome and failure; consent and privacy; what data may appear in messages and logs;
   time zones and quiet hours; duplicates and idempotency; provider outage and ambiguous outcomes; cost ceiling;
   how to test without real side effects; rollback; and what is explicitly out of scope.
5. Record each resolved question in the spec's **Open questions** table (question, owner, resolved answer).
   Only edit that table and the Status line.
6. Stop when no open questions remain. Say so, summarise what changed, and set Status to `Grilled`.

Do not write code. Do not approve the spec: only the humans named in the Approval block can do that.
