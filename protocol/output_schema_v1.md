# MadhuMitra — Output Schema v1.0
## Required JSON Structure for Every Reasoning Response

| Field | Value |
|-------|-------|
| Version | v1.0 |
| Date | May 2026 |
| Status | ACTIVE — enforced on every reasoning call |

---

## Purpose

This schema defines the exact JSON structure every reasoning
response must follow. Responses that do not match this schema
are rejected by the guardrails verifier and routed to the
manual review queue.

---

## Required Schema

```json
{
  "name": "string — patient name exactly as provided",

  "severity": "one of: High | Medium | Low | On Track",

  "confidence": "one of: high | low",

  "track": "one of: auto | queue | on_track",

  "reasoning": "string — one sentence maximum, citing specific data",

  "signals": ["array of strings — each signal that contributed to severity"],

  "has_tier1_symptom": "boolean — true if any Tier 1 symptom present",

  "medication_missed": "boolean — true if medication_taken is false",

  "consecutive_days": "integer — estimated days this pattern present",

  "glucose_trend": "one of: rising | stable | improving | unknown",

  "escalate_to_doctor": "boolean — true if any Rule 10 trigger present",

  "nudge_risk": "boolean — true if plateau or disengagement pattern detected"
}
```

---

## Field Rules

**severity:**
- High → patient needs same-day coach contact
- Medium → patient needs coach contact within 24 hours
- Low → note at next scheduled check-in
- On Track → no action needed today

**confidence:**
- high → signals are clear and unambiguous → track must be "auto" or "on_track"
- low → signals are ambiguous or conflicting → track must be "queue"

**track:**
- auto → appears in auto-prioritized alert list
- queue → appears in manual review queue
- on_track → appears in on-track section, no alert

**Routing logic — these combinations are the only valid ones:**

| severity | confidence | track |
|----------|-----------|-------|
| High | high | auto |
| High | low | queue |
| Medium | high | auto |
| Medium | low | queue |
| Low | high | auto |
| Low | low | queue |
| On Track | high | on_track |

**reasoning:**
- Maximum one sentence
- Must cite specific data: exact glucose values, exact phrases from free text
- Must not contain diagnostic language (see guardrails Rule 1)
- Must not contain prescriptive language (see guardrails Rule 2)
- Must not contain inferred assumptions (see guardrails Rule 4)
- Must reference comorbidities when they affect interpretation

**signals:**
- List every signal that contributed to the severity decision
- Use plain language: "FBS 165 mg/dL above medium threshold"
- Include both structured signals and free-text signals
- Minimum 1 signal for any non-on-track response

**consecutive_days:**
- Use program_history and coach_notes to estimate
- If unknown, return 1
- Do not guess — if no evidence of pattern, return 1

**glucose_trend:**
- rising → today's FBS higher than initial or previous reading
- improving → today's FBS lower than initial or previous reading
- stable → little change from previous readings
- unknown → no comparison data available

**escalate_to_doctor:**
- Triggers defined in guardrails Rule 10
- When true, reasoning must explain why

**nudge_risk:**
- True when plateau or disengagement pattern detected
- Based on: flat glucose trend + flat weight + declining log quality
- Use program_history week_number and coach_notes for context

---

## Example Valid Response — High Severity

```json
{
  "name": "Deepak Verma",
  "severity": "High",
  "confidence": "high",
  "track": "auto",
  "reasoning": "FBS 165 mg/dL above medium threshold with medication missed, stress score 5/5 for third consecutive day, sleep 4.5 hrs fragmented, and all three craving types selected — multiple compounding signals with conservative targets given hypertension and fatty liver",
  "signals": [
    "FBS 165 mg/dL above 130 threshold",
    "medication missed today",
    "stress score 5 — above threshold of 4",
    "sleep 4.5 hrs below threshold of 6",
    "woke up multiple times",
    "BP 145/92 above high threshold",
    "all three craving types selected",
    "protein 50g vs target 95g",
    "carbs 200g vs target 80g"
  ],
  "has_tier1_symptom": false,
  "medication_missed": true,
  "consecutive_days": 3,
  "glucose_trend": "stable",
  "escalate_to_doctor": false,
  "nudge_risk": false
}
```

## Example Valid Response — On Track

```json
{
  "name": "Karthik Iyer",
  "severity": "On Track",
  "confidence": "high",
  "track": "on_track",
  "reasoning": "FBS 112 mg/dL below target, full body weights completed, fasting day observed, sleep quality good, all signals positive",
  "signals": ["FBS 112 mg/dL — below target of 90", "strength training completed", "fasting day observed"],
  "has_tier1_symptom": false,
  "medication_missed": false,
  "consecutive_days": 0,
  "glucose_trend": "improving",
  "escalate_to_doctor": false,
  "nudge_risk": false
}
```

---

## Schema Validation Checks

The guardrails verifier checks every response against these rules:

1. All 12 fields present
2. severity is one of the four valid values
3. confidence is high or low
4. track matches the severity+confidence routing table above
5. reasoning does not contain diagnostic keywords
6. reasoning does not contain prescriptive keywords
7. signals array is not empty for non-on-track responses
8. escalate_to_doctor is true when Rule 10 triggers are present
9. Response is valid JSON — no markdown, no extra text

Failed checks → route to manual review queue with failure reason noted.
