# MadhuMitra — Alert Guide v1.0
## Clinical Protocol Intelligence Layer

| Field | Value |
|-------|-------|
| Version | v1.0 |
| Baseline | DiRECT Trial (Lancet 2018) + ADA Standards of Care 2024 |
| Date | May 2026 |
| Approved by | [Pilot diabetologist sign-off required before activation] |
| Clinic | [Clinic name] |
| Status | DRAFT — not active until doctor signs off |

---

## How This Document Works

This document defines **what** each alert tier means and **why** each signal matters clinically.

**It does not contain threshold numbers.** All specific values live in `thresholds_v1.yaml`. This separation means numbers are updated in one place only and this document never drifts out of sync.

When you see `→ rules: glucose.fasting.high_threshold` it means: look up this value in `thresholds_v1.yaml` to find the exact number currently in use.

**Universal vs clinic-specific content:**
Sections 1–8 contain universal clinical reasoning — valid for any diabetes reversal program anywhere. Section 9 (Clinic Context) contains clinic-specific interpretation notes. When onboarding a new clinic, only Section 9 is replaced. The clinical reasoning in Sections 1–8 remains valid.

---

## Evidence Base

1. **DiRECT Trial** — Lean MEJ et al. *Primary care-led weight management for remission of type 2 diabetes.* The Lancet, 2018 [1]. 46% remission under structured supervised lifestyle intervention.

2. **ADA Standards of Medical Care in Diabetes 2024** — American Diabetes Association. *Diabetes Care*, 2024 [2]. Clinical glucose thresholds, complication warning signs, treatment targets.

3. **Indian metabolic profile** — Misra A et al. JAPI 2009 [3]; WHO Expert Consultation, Lancet 2004 [4]. Asian-specific BMI thresholds and visceral adiposity patterns.

4. **Dropout and engagement research** — PMC5320825 [5]. 53% dropout in Indian lifestyle-only programs; intensive coaching reduced this to near zero.

---

## Section 1 — Alert Tiers

### 🔴 HIGH Severity — Urgent. Coach acts today.

A High alert means the patient has signals that, if left unattended today, could result in clinical deterioration, a reversal setback, or a medical emergency.

**Automatic HIGH — glucose:**
- FBS above `→ rules: glucose.fasting.high_threshold`
- Post-meal glucose above `→ rules: glucose.post_meal.high_threshold`
- FBS rise above `→ rules: glucose.fasting.sudden_spike_delta` from previous day

> **Evidence:** ADA 2024 [2] defines preprandial target upper limit for adults with diabetes. Readings significantly above this represent clinically meaningful hyperglycemia. DiRECT trial [1] used immediate nurse contact for sustained glucose above program target.

**Automatic HIGH — symptom signals (regardless of glucose):**

Full keyword lists in `→ rules: symptom_classification.tier_1_always_high`.

| Symptom | Clinical concern | ADA reference |
|---------|-----------------|---------------|
| Foamy or frothy urine | Possible proteinuria — early diabetic kidney disease | ADA 2024, Section 11 [2] |
| Blurry or cloudy vision | Possible retinopathy or osmotic change | ADA 2024, Section 12 [2] |
| Persistent dizziness | Possible hypoglycemia or autonomic neuropathy | ADA 2024, Section 12 [2] |
| Swelling | Possible edema — kidney or cardiac signal | ADA 2024, Section 11 [2] |
| Excessive thirst + urination together | Classic hyperglycemia symptom cluster | ADA 2024, Section 2 [2] |
| Numbness or tingling | Early peripheral neuropathy | ADA 2024, Section 12 [2] |
| Chest pain or discomfort | Cardiac concern — escalate to doctor immediately | ADA 2024, Section 10 [2] |

**Automatic HIGH — behavioural:**
- Missed logs for `→ rules: missed_log.high_consecutive` or more consecutive days
- Free-text matching `→ rules: sentiment.acute_distress_keywords`
- Medication missed + glucose above `→ rules: combination_rules.medication_missed_glucose_high_threshold`

**Confidence level:** High — route to auto-prioritized list.

---

### 🟡 MEDIUM Severity — Attention needed. Coach acts within 24 hours.

**MEDIUM — glucose:**
- FBS between `→ rules: glucose.fasting.medium_min` and `→ rules: glucose.fasting.medium_max`
- FBS in low range combined with any negative free-text signal
- Post-meal glucose between `→ rules: glucose.post_meal.medium_min` and `→ rules: glucose.post_meal.medium_max`

> **Evidence:** ADA 2024 [2] sets preprandial target upper limit. Readings above this warrant coach contact. DiRECT trial [1] used weekly monitoring with contact for sustained above-target readings.

**MEDIUM — behavioural:**
- Exercise missed for `→ rules: exercise.missed_days_severity.medium` or more consecutive days
- Negative mood detected across `→ rules: sentiment.negative_drift_medium_days` consecutive days
- `→ rules: stress_sleep_combination.consecutive_days_medium` days of BOTH high stress AND poor sleep

**MEDIUM — combination rule:**
Two Low signals on the same day escalate to Medium. See `→ rules: combination_rules.two_low_signals_escalate_to`.

**Confidence level:** High for clear combinations. Low for borderline single signals — route to manual queue.

---

### 🟢 LOW Severity — Monitor. Note at next scheduled check-in.

**LOW signals:**
- FBS between `→ rules: glucose.fasting.low_min` and `→ rules: glucose.fasting.low_max` with no other negative signals
- Single missed exercise day (first occurrence in the week)
- Single minor dietary deviation with controlled glucose
- Mild negative mood with no other deviations
- Weight gain between `→ rules: weight.low_gain_min` and `→ rules: weight.low_gain_max`

**Confidence level:** High for clear single deviations. Route to auto-prioritized list at bottom.

---

### ✅ ON TRACK — No action needed.

**All must be true:**
- FBS below `→ rules: glucose.fasting.on_track_max`
- Exercise at or above `→ rules: exercise.daily_target` minutes
- No significant dietary deviations
- No symptom signals
- Neutral or positive mood

---

### 🔵 MANUAL REVIEW QUEUE — Coach applies clinical judgement.

Route here when:
- Single borderline glucose within `→ rules: confidence.borderline_glucose_queue` range with no other signals
- Ambiguous free-text — could be normal fatigue or clinical signal
- First `→ rules: combination_rules.new_patient_queue_days` days of program
- Conflicting signals — controlled glucose but strongly negative free-text
- Log incomplete

---

### 🟣 NUDGE — Warm check-in when convenient.

Not a clinical alert. Appears in a separate UI section below the alert list and queue.

Route here when plateau or disengagement pattern detected. See Section 7.

---

## Section 2 — Signal Combination Rules

Full rules in `→ rules: combination_rules`. Clinical reasoning behind key combinations:

| Primary signal | Combined with | Result | Why |
|---------------|---------------|--------|-----|
| Borderline FBS | Tier 1 symptom in symptoms array | Escalate to High | Symptom always overrides |
| Borderline FBS | Strong positive mood | Keep at Medium | Positive engagement reduces weight |
| Missed exercise | First occurrence | Low | Single deviation, no pattern |
| Missed exercise | Consecutive days at medium threshold | Medium | Pattern forming |
| Social event context | Dietary deviation | Reduce weight — Low unless glucose elevated | Expected context |
| "Feeling tired" | No other signals | Manual queue | Cannot distinguish fatigue from clinical signal |
| High stress score | 3 consecutive days + poor sleep | High | Cortisol elevated — glucose spike imminent |
| All 3 craving types selected | Same day | High dietary risk flag | Stress-eating pattern |

---

## Section 3 — Symptom Tiers

Symptoms arrive as a multi-select array. See `→ rules: symptom_classification` for full lists.

**Tier 1 — Always High:** Caught by parser before LLM. Dizziness, swelling, foamy urine, blurry vision, chest pain, numbness, tingling.

**Tier 2 — Medium amplifier:** Elevate severity when combined with other signals. Sleepy/drowsy, headache, anxiety, constipation, snoring, body pain.

**Tier 3 — Monitor:** Note and track. Do not alert alone. Acidity, acne, hair fall, burping, gas, dry cough, boil.

> **Note on Tier 3:** Acne and hair fall can indicate hormonal rebalancing during reversal — sometimes a positive metabolic signal. Do not over-flag. Monitor trend over 2+ weeks.

> **Note on snoring:** Sleep apnea signal. Combine with sleep quality and glucose. Persistent snoring + poor sleep quality + elevated glucose = escalate to Medium and note for doctor.

---

## Section 4 — Mood and Cravings

Arrive as a multi-select array. Parser splits into mood signals and craving signals before LLM processing. See `→ rules: mood_classification`.

**Mood signals:** Happy, Sad, Frustrated, Bored, Angry, Other

**Craving signals:** Craving Sweet, Craving Salty, Craving Crunchy

**Clinical significance of cravings:**
- Sweet craving → possible low glucose or insulin spike — high dietary deviation risk next 24 hours
- Salty craving → possible dehydration or adrenal stress — common on fasting days
- Crunchy craving → texture-based stress craving — often linked to anxiety or emotional eating
- All three selected in one day → highest dietary deviation risk — LLM flags as strong pattern

**Multiple negative moods same day** = stronger signal than one alone. Sad + Frustrated + Craving Sweet is a compound signal.

---

## Section 5 — Sleep Assessment

Sleep requires two fields together — duration alone is insufficient.

| Duration | Quality | Assessment |
|---------|---------|------------|
| 7+ hours | Slept well, woke fresh | Genuine good sleep — no flag |
| 7+ hours | Woke up tired | Poor quality despite adequate hours — flag |
| 6–7 hours | Trouble falling asleep | Moderate concern — watch trend |
| <6 hours | Any quality | Flag — see `→ rules: sleep` |
| Any | Woke up multiple times | Fragmented sleep — amplify flag weight |

> **Principle:** Quality overrides quantity when they conflict. See `→ rules: sleep_quality.combination_rules`.

> **Snoring + poor sleep + high glucose** = possible sleep apnea driving glycaemic disruption. Flag for doctor awareness.

---

## Section 6 — Exercise Assessment

Exercise requires three fields together — duration and type alone are insufficient.

**Duration:** See `→ rules: exercise.daily_target`

**Type:** Cardio vs strength — both required. See `→ rules: exercise_types` for full lists.

**Note (free-text):** LLM assesses intensity quality. A note saying "used 2kg dumbbells, very easy" alongside `exercise_type: weights` means the strength stimulus was likely insufficient. See `→ rules: exercise_notes.low_intensity_indicators`.

**Weight training gap:** After `→ rules: weight_training_gap.medium_threshold` consecutive cardio-only days, a Medium alert fires. This is a balance alert — patient IS exercising. Coach nudges toward adding strength sessions.

**Reasoning language for exercise alerts:**
- ✅ "Patient has logged exercise consistently but no strength training in X days — balance between cardio and weights needed"
- ✅ "Exercise logged as weights but note indicates very light intensity — strength stimulus may be insufficient"
- ❌ "Patient is not exercising enough" — incorrect if they are exercising
- ❌ "Patient needs to go to the gym" — prescriptive

---

## Section 7 — Plateau and Silent Disengagement (Nudge)

**This is not a clinical alert. It is a coach nudge.**

**The pattern:** Patient had a strong start. Results have plateaued over `→ rules: plateau_nudge.detection_window_days` days. Log quality is declining — entries getting shorter, less detailed, repetitive. Each individual day looks fine. Only the trend reveals the risk.

**Why the LLM catches this and a coach reviewing 50 patients manually does not:** The LLM examines the multi-week trend. A coach sees today's log. The plateau is invisible in a single day's data.

**Fires when** `→ rules: plateau_nudge.combined_trigger.minimum_signals` of these are true:
1. Glucose change below `→ rules: plateau_nudge.glucose_plateau.change_threshold_mgdl` over window
2. Weight change below `→ rules: plateau_nudge.weight_plateau.change_threshold_kg` over window
3. Log quality declining
4. Fasting inconsistency present
5. Weight training gap present

**Good silence vs risk silence:**

| Good silence | Risk silence |
|---|---|
| Logs brief but complete | Logs increasingly incomplete |
| Metrics still improving slowly | Metrics flat 2+ weeks |
| Positive or neutral tone | Tone absent or minimal |
| Fasting and weights consistent | Fasting and weights slipping |

**What the coach does:** Warm check-in call. "How are you feeling about your progress this week?" — not a clinical intervention.

**Reasoning language:**
- ✅ "Patient showed strong early results but glucose and weight have been stable for 12 days — log detail also declining; warm check-in recommended"
- ❌ "Patient is plateauing and may drop out" — alarming
- ❌ "Patient is not progressing" — negative framing

---

## Section 8 — Fasting Consistency

Only applies when `fasting_protocol: true` set at onboarding.

Sporadic fasting gives neither metabolic benefit nor habit formation. Consistency is what activates the hormonal and cellular mechanisms.

Alert fires when actual fasting days fall below `→ rules: fasting_consistency.consistency_min_pct`% of expected over the `→ rules: fasting_consistency.window_days` day window. Applies whether patient never built the habit or had it and lost it.

**Reasoning language:**
- ✅ "Patient fasted X of Y expected days this week — fasting consistency below target; coach check-in to understand barriers"
- ❌ "Patient is not following the protocol" — judgemental
- ❌ "Patient needs to fast more" — prescriptive

---

## Section 9 — Clinic Context (Clinic-Specific — Replace for New Clinic)

> **This section is the only part of this document that changes between clinics.**
> All reasoning in Sections 1–8 is universal clinical logic valid for any diabetes reversal program.
> When onboarding a new clinic, replace this section with their specific context.
> The code never changes. Only this section and `thresholds_v1.yaml → clinic_context` are updated.

**Current clinic context:** See `→ rules: clinic_context` for full details.

**Population-specific interpretation notes for this clinic:**

- Indian patients have higher visceral adiposity at lower BMI [3]. Do not discount signals based on normal Western BMI readings.

- Post-meal glucose excursions are more pronounced with high-glycaemic-index staples (white rice, refined wheat) common in this population [Gopalan et al.]. Interpret post-meal readings in context of the food diary.

- A single dietary deviation at a social event (wedding, festival, family function) is culturally expected and normal. Reduce weight compared to a deliberate dietary break — unless glucose is also elevated above the medium threshold. See `→ rules: clinic_context.social_eating_contexts` for the full list.

- Patient apologies in free-text ("sorry doctor I cheated") indicate self-awareness and continued engagement — a positive behavioural signal, not a distress indicator.

- "Feeling heavy" in this population's English usage means fatigue or physical discomfort — not weight gain. Do not treat as a weight signal.

- Silence (missed log) carries more clinical significance than a brief apologetic message. A patient who writes in is still engaged.

- If free-text appears to be in a regional language (Hindi, Tamil, Telugu etc.), flag in reasoning trace: "Note: log appears to be in [language] — sentiment analysis may be limited." Full multilingual support is a Phase 2 feature.

**What a different clinic replaces here:**

```
UK diabetes reversal clinic:
  - No visceral adiposity note (use standard BMI)
  - Dietary context: bread, pasta, potatoes, meat
  - Social events: pub meals, Christmas dinner, takeaways
  - No regional language note

Indian thyroid management clinic:
  - Same population and dietary notes as this clinic
  - Different program pillars (TSH, T3, T4 signals)
  - Different alert taxonomy for thyroid-specific signals
```

---

## Section 10 — Reasoning Language Guide

Every alert must be:
- **Specific** — cites exact data from the patient's log
- **Non-diagnostic** — surfaces signals, never draws clinical conclusions
- **Coach-directed** — tells the coach what to look at, not what to do
- **Grounded** — no inferred assumptions; only what the log actually contains

**Good reasoning traces:**
- ✅ "FBS above high threshold — patient's symptoms array includes dizziness and swelling; these combined with elevated glucose warrant same-day check-in"
- ✅ "Third consecutive missed log — no data to assess patient status; coach contact needed to confirm engagement"
- ✅ "FBS above medium threshold, exercise missed, patient selected Craving Sweet and Craving Crunchy — multi-signal deviation, check-in within 24 hours"

**Bad reasoning traces — never generate these:**
- ❌ "Patient may be developing kidney disease" — diagnostic
- ❌ "Patient is non-compliant" — judgemental
- ❌ "Glucose spike suggests patient ate a large meal" — inferred assumption
- ❌ "Patient needs to exercise more" — prescriptive
- ❌ "High risk of hypoglycemia" — diagnostic conclusion

---

## Section 11 — The Three Output Categories

| Category | Severity | Coach action | UI location |
|---|---|---|---|
| Clinical alert | High / Medium / Low | Act today / 24hrs / note | Auto-prioritized list |
| Manual review | Uncertain | Apply clinical judgement | Manual review queue |
| Nudge | Informational | Warm check-in when convenient | Separate nudge section |

Never mix categories in the UI. Clinical alerts require a response. Nudges are guidance. Mixing them dilutes urgency.

---

## Section 12 — Escalation to Doctor

Coach handles all alerts independently except for signals in `→ rules: escalate_to_doctor`:
- Any chest pain or discomfort
- Foamy urine combined with elevated glucose on the same day
- Blurry vision persisting more than one day
- Persistent dizziness across multiple consecutive days
- Patient explicitly requests a doctor
- FBS above `→ rules: escalate_to_doctor.glucose_trigger.fbs_above` on `→ rules: escalate_to_doctor.glucose_trigger.consecutive_days` or more consecutive days

---

## References

[1] Lean MEJ et al. Primary care-led weight management for remission of type 2 diabetes (DiRECT). *The Lancet.* 2018;391(10120):541–551.

[2] American Diabetes Association. Standards of Medical Care in Diabetes — 2024. *Diabetes Care.* 2024;47(Supplement 1).

[3] Misra A et al. Consensus statement for diagnosis of obesity for Asian Indians. *JAPI.* 2009;57:163–170.

[4] WHO Expert Consultation. Appropriate BMI for Asian populations. *The Lancet.* 2004;363(9403):157–163.

[5] PMC5320825 — High rates of diabetes reversal in Asian Indian young adults with intensive lifestyle therapy.

---

## Version Control and Sign-off

| Version | Date | Changes | Approved by |
|---------|------|---------|-------------|
| v1.0 | May 2026 | Initial DiRECT/ADA baseline | [Doctor name — pending] |

**Rule:** No changes without doctor sign-off. Version must match `thresholds_v1.yaml`. App refuses to start if they differ.

---

*This document governs an AI triage tool that surfaces signals to a qualified health coach. All alerts are recommendations — not instructions. The supervising doctor and health coach retain full clinical responsibility for all patient care decisions.*
