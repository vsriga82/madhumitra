# MadhuMitra — Session Handoff Note
**Date:** May 29, 2026
**For:** Continuing the build in a new Claude conversation

---

## Who I Am
Sri — mid-career Product Manager based in Chennai, India.
Taking a course by Mahesh Yadav on Claude Code and AI-powered PM workflows.
Building MadhuMitra as my course project.
I am personally enrolled in a diabetes reversal program — the signal list reflects my own real program experience.

---

## What MadhuMitra Is
A Clinical Protocol Intelligence Layer for doctor-led diabetes reversal programs.
NOT a patient app. NOT a diabetes management tool.
It is a coach-facing triage tool that helps health coaches monitor 20–100 patients daily.

**The core loop:**
One input (patient daily logs via CSV/JSON upload)
→ One reasoning loop (cross-signal detection → sentiment drift → risk tier assignment)
→ One output (ranked alert list + manual review queue + nudge section for the health coach)

**Win condition:** Coach reviews full patient panel in under 20 minutes instead of 2–3 hours, with zero high-risk cases missed.

**Key constraint:** Every alert is a recommendation to the coach. Coach reviews and acts every time. MadhuMitra never diagnoses, prescribes, auto-sends alerts, or auto-escalates.

---

## The PRD
Full PRD is in VS Code at: `AI-PM-COURSE/Madumitra/Other Docs/prd-v1.md`

**Mentor feedback received:**
> "This is one of the strongest submissions in this cohort — sharp persona, specific agentic justification, validated MOAT, and a structured output artifact."

Key mentor instructions:
- Position as "Clinical Protocol Intelligence Layer" not a diabetes app
- Do not build patient-facing companion in v1
- Do not auto-send alerts or auto-escalate
- Co-design alert taxonomy with diabetologist — that artifact is the moat

---

## Key Insight from Last Session
**The complexity lies in the protocol, not the architecture or code.**
The architecture is simple — 5 steps, ~300 lines of Python total.
The moat is the clinical reasoning encoded in the protocol files.
That knowledge cannot be replicated by copying the code.

---

## Build Plan — 4 Phases

### Phase A — Foundation ✅ COMPLETE
All protocol files built and saved in `Madumitra/protocol/`

### Phase B — Data Layer ← WE ARE HERE — START HERE
Step 1: Python environment setup
Step 2: Write `parser.py`
Step 3: Write `test_reasoning.py` — first Claude API call

### Phase C — Core AI Loop (after B)
Dual agentic loop: reasoning agent + guardrails verifier
Priority scoring and ranking

### Phase D — Coach Dashboard (after C)
Streamlit UI with three sections:
- Auto-prioritized alert list
- Manual review queue
- Nudge section (plateau + disengagement)

### Before Demo — n8n Migration
Course teaches n8n. We build in Python first (to learn the logic), then migrate to n8n before demo day. Clean layer separation in Python makes migration straightforward — each Python file becomes an n8n node.

---

## File Structure in VS Code

```
AI-PM-COURSE/
└── Madumitra/
    ├── Other Docs/
    │   ├── prd-v1.md
    │   ├── market-research-report.md
    │   ├── prd-eval-report.md
    │   └── user-research-report.md
    ├── protocol/
    │   ├── alert_guide_v1.md        ← WHY (clinical reasoning, no numbers)
    │   ├── thresholds_v1.yaml       ← WHAT (exact numbers, single source of truth)
    │   └── validate_versions.py     ← GUARD (checks versions match at startup)
    └── data/
        ├── sample_patients.json     ← 8 realistic patients, full signal set
        └── sample_patients.csv      ← same patients, flat format
```

**Still to create (Phase B onwards):**
```
    ├── parser.py                    ← reads CSV/JSON, splits structured/unstructured,
    │                                   runs rules check, flags deviations
    ├── reasoning.py                 ← calls Claude API concurrently per patient
    ├── ranker.py                    ← priority scoring after all calls complete
    ├── app.py                       ← Streamlit UI
    └── requirements.txt             ← anthropic, streamlit, pyyaml, pandas
```

---

## Architecture — How It All Fits Together

```
INGESTION
─────────
CSV or JSON uploaded by coach
Protocol files loaded (alert_guide + thresholds) → injected into system prompt

PARSER (parser.py)
──────────────────
Structured fields → rules check against thresholds_v1.yaml
On-track patients → skipped (no LLM call, saves cost)
Flagged patients → proceed with deviation flags + unstructured text

DUAL AGENTIC LOOP (reasoning.py)
─────────────────────────────────
Loop 1 — Reasoning agent (Claude)
  Cross-signal detection → sentiment drift → risk tier → confidence score

Loop 2 — Guardrails verifier (Claude)
  Checks: reasoning grounded in log data?
  Checks: no diagnostic language?
  Checks: severity consistent with thresholds?
  If fail → Loop 1 reruns with verifier feedback (max 2 retries)
  If still fail → route to manual queue

RANKING (ranker.py)
────────────────────
All concurrent calls complete
Python deterministic ranker scores each patient
Sort within tier: High #1 → High #2 → Medium #1 etc.
Score drives order but is hidden from coach by default

OUTPUT (app.py — Streamlit)
────────────────────────────
Track 1: Auto-prioritized alert list (ranked High → Medium → Low)
Track 2: Manual review queue (low confidence or failed verification)
Track 3: Nudge section (plateau + silent disengagement)
```

---

## Key Design Decisions Made

### 1. Two-file protocol architecture
- `alert_guide_v1.md` = clinical reasoning, references, NO hardcoded numbers
- `thresholds_v1.yaml` = exact numbers only, NO clinical reasoning
- Numbers live in exactly ONE place
- Version validator runs at startup — app refuses to start if versions don't match

### 2. Three output tracks
- Auto-prioritized list — clinical alerts, high confidence
- Manual review queue — low confidence or failed guardrails
- Nudge section — plateau and disengagement, NOT mixed with clinical alerts

### 3. Per-patient targets
Protein and carb targets are NOT clinic-wide — set by doctor per patient at onboarding.
Each patient record has a `doctor_targets` block and a `program_history` block.

### 4. Concurrent Claude calls
50 patients in → parser filters → ~15 flagged → 15 concurrent Claude calls.
All finish in ~3–4 seconds total using `asyncio.gather`.
NOT sequential (which would take 45+ seconds).

### 5. Deterministic priority scoring
After all Claude calls complete, Python ranker assigns a weighted score.
Score weights live in `thresholds_v1.yaml → priority_scoring`.
Doctor can adjust weights during calibration without touching code.
No extra LLM call for ranking — fast, auditable, explainable.

### 6. Dual agentic loop
Matches course Week 2 teaching. Loop 1 reasons, Loop 2 verifies.
Max 2 retries, then route to manual queue.
Maps to Component 9 (Guardrails) in the PRD.

### 7. n8n compatibility
Python code has clean separate layers (parser, reasoning, ranker, UI).
Each layer becomes an n8n node during migration before demo.
Logic stays the same — only the container changes.

---

## Full Signal Set

| Signal | Type | Notes |
|--------|------|-------|
| Glucose (FBS + post-meal) | Structured | Core — ADA 2024 thresholds |
| Exercise duration | Structured | Minutes per day, 30 min target |
| Exercise type | Structured | Cardio vs strength — both required |
| Weight training gap | Pattern | 5 days cardio-only = Medium |
| Sleep | Structured | Hours per night, <6hrs = flag |
| Stress | Structured + free-text | Score 1–5 + keyword detection |
| Stress + Sleep combination | Combination | 3 consecutive days BOTH = High |
| Screen time | Structured | Contributing factor to sleep |
| Blood pressure | Structured | ADA threshold 130/80 for diabetics |
| Mood | Structured | Score 1–5 |
| Cravings | Structured | Score 1–5 |
| Energy level | Structured | Score 1–5, dropout risk |
| Protein intake | Structured | Per-patient target (e.g. 90–95g) |
| Carb intake | Structured | Per-patient target |
| Fasting consistency | Pattern | % of expected fasting days met |
| Body measurements | Structured | Weekly, Indian waist thresholds |
| Missed log | Structured | 3 consecutive = High |
| Symptom signals | Free-text | Foamy urine, blurry vision = always High |
| Sentiment | Free-text | Distress keywords + Indian context |
| Food diary | Free-text | Unstructured, LLM interprets |
| Coach notes | Free-text | WhatsApp/Telegram summary |
| Plateau + disengagement | Multi-day pattern | 14-day trend, nudge not alert |

---

## Sample Patients — What Each Tests

| Patient | Week | Designed to test |
|---------|------|-----------------|
| Priya Sharma | 6 | High glucose + dizziness + wedding event + stress |
| Rajan Kumar | 13 | Plateau nudge — strong start, results flat, logs getting brief |
| Meena Patel | 4 | Missed log — third consecutive, no data at all |
| Suresh Nair | 8 | Symptom escalation — foamy urine + dizziness = auto High |
| Anita Rao | 3 | Fasting inconsistency + no weights yet |
| Karthik Iyer | 11 | Perfect adherence — all signals green |
| Fatima Sheikh | 5 | Social event + apology tone + weights gap |
| Deepak Verma | 8 | Maximum complexity — stress 5, sleep 4.5hrs, missed medication, no weights, fasting 1/5 days |

---

## Priority Scoring Logic (in thresholds_v1.yaml)

```
Symptom signals:
  chest_pain: 50, foamy_urine: 40, blurry_vision: 40
  numbness: 35, dizziness: 30

Medication missed with high glucose: 25
Consecutive days × 8 per day (max 7 days)
Glucose trend rising: +15
Per additional signal: +5
Stress + sleep combined × 10 per day
Missed log × 12 per consecutive day
BP above ADA threshold: +20

Score bands:
  ≥80 = critical (contact immediately)
  50–79 = urgent (contact today)
  20–49 = standard (contact within 24hrs)
  <20 = monitor
```

---

## Course Context (Week 2 Concepts)

| Course concept | MadhuMitra equivalent |
|---|---|
| Ingestion flow | Loading CSV/JSON + protocol files |
| RAG | Protocol files injected into system prompt (no vector DB needed for MVP) |
| Text cutter | Structured/unstructured split in parser |
| Decision flow | Two-track + nudge output system |
| Dual agentic loop | Reasoning agent + guardrails verifier |
| Vector DB | Not needed for MVP — logs are short |
| Knowledge graph | Not needed for MVP |
| Connect to OpenAI | Same pattern, using Anthropic/Claude |

---

## What to Do First in Next Session

1. Open VS Code terminal in Madumitra folder
2. Run: `python3 --version` (need 3.8+)
3. Run: `pip3 --version`
4. If both work, create virtual environment:
   ```bash
   cd ~/AI-PM-COURSE/Madumitra
   python3 -m venv venv
   source venv/bin/activate
   pip install anthropic streamlit pyyaml pandas
   ```
5. Create `requirements.txt`
6. Start building `parser.py`

---

## How Sri Learns Best
- Explain WHY before building WHAT
- One step at a time — not everything at once
- Code in small pieces — paste, run, understand, then next piece
- Design before coding
- When in chat: design and decide
- When in VS Code: write and run code side by side with chat

---
*Paste this note at the start of a new Claude conversation to resume exactly here.*

---

## Session Update — Phase B Progress

### parser.py — COMPLETE ✅

Five functions written and tested:
- `load_thresholds()` — reads thresholds_v1.yaml into memory
- `load_patients()` — accepts CSV or JSON, returns standard list
- `check_rules()` — compares structured fields against thresholds, returns deviations list
- `generate_rules_alert()` — builds alert for Bucket 1 cases without LLM
- `is_on_track()` — returns True if no deviations
- `parse_patient()` — wraps everything, returns standardised dict
- `parse_all()` — entry point, returns three lists

### Test results on 8 sample patients:
- On track: 1 (Karthik Iyer — perfect signals)
- Rules alerted: 2 (Priya Sharma score 85, Suresh Nair score 120 — Tier 1 symptoms)
- Send to LLM: 5 (Rajan plateau, Meena missed log, Anita borderline, Fatima multi-signal, Deepak 15 deviations)

### Sample data updated with full onboarding structure:
Each patient now has complete program_history including:
- clinical_targets (per-patient FBS target, hypoglycemia threshold)
- comorbidities (hypertension, CKD, thyroid, PCOD, anemia, Vitamin D etc.)
- medications (diabetes, BP, thyroid, cholesterol, supplements)
- baseline_labs (HbA1c, LDL, Vitamin D, creatinine)

Notable patients:
- Suresh Nair: CKD + microalbuminuria — foamy urine today = escalate to doctor
- Deepak Verma: sleep apnea suspected, conservative targets, 15 deviations
- Anita Rao: no diabetes medication — lifestyle only, borderline FBS is encouraging

### Next step — prompt.py
Builds the OpenAI system prompt from:
1. alert_guide_v1.md (clinical reasoning)
2. thresholds_v1.yaml (exact thresholds)
3. patient program_history (comorbidities, targets)
4. patient deviations list (from parser)

Run this to resume:
```bash
cd ~/AI-PM-COURSE/Madumitra
source venv/bin/activate
touch prompt.py
```

---

## RAG Roadmap (For Demo and Beyond)

Sri wants to learn enterprise RAG patterns using MadhuMitra as the use case.
The progression is planned as follows:

### Version 1 — Current (Full protocol in prompt)
- All four protocol files injected into every call
- Thresholds converted to compact JSON (strips comments, ~30% smaller)
- Simple, works perfectly for pilot with one clinic and 8-50 patients
- ~9,000 tokens per call, ~$0.11 per daily batch of 5 patients

### Version 2 — Basic RAG (For demo)
**Goal:** Store protocol in vector DB, retrieve only relevant sections per patient

**What to build:**
1. Chunk alert_guide_v1.md into sections (one chunk per section heading)
2. Chunk thresholds_v1.yaml into topic blocks (glucose, sleep, stress etc.)
3. Embed all chunks using OpenAI text-embedding-3-small
4. Store in ChromaDB (local, no server needed, free)
5. At reasoning time:
   - Take patient's deviations list as query
   - Retrieve top 5 most relevant chunks
   - Inject only those chunks into the prompt

**Expected result:**
- Deepak with stress + sleep issues → retrieves stress, sleep, combination rules sections
- Suresh with CKD + foamy urine → retrieves symptom signals, escalation sections
- Each patient gets ~20% of the protocol instead of 100%
- Token cost drops by ~80%

**Libraries needed:**
```bash
pip install chromadb openai sentence-transformers
```

**Files to create:**
```
rag/
  embedder.py       ← chunks and embeds protocol files
  retriever.py      ← retrieves relevant chunks per patient
  vector_store/     ← ChromaDB storage (auto-created)
```

### Version 3 — Agentic RAG
**Goal:** Agent decides what to retrieve, can do multi-hop retrieval

Instead of a fixed retrieval query, an agent:
1. Reads the patient deviations
2. Decides which aspects of the protocol are most relevant
3. Issues multiple targeted retrieval queries
4. Assembles the retrieved context intelligently

Example for Deepak:
- Query 1: "stress sleep combination rules thresholds"
- Query 2: "medication missed glucose combination"
- Query 3: "conservative targets hypertension fatty liver"
- Assembles three targeted retrievals → richer, more precise context

### Version 4 — Multi-clinic RAG
**Goal:** Each clinic has its own isolated vector store

```
vector_stores/
  clinic_001/   ← Dr. Roshani Sinha's protocol
  clinic_002/   ← UK diabetes clinic protocol
  clinic_003/   ← thyroid management clinic
```

Each clinic's protocol is embedded into their own ChromaDB collection.
At runtime, the clinic ID determines which collection to query.
No cross-clinic data leakage — each clinic's reasoning is isolated.

**This maps directly to Component 2 (Protocol Vault) in the PRD.**
The vector store IS the Protocol Vault at scale.

### When to build Version 2:
- Before the mentor demo
- After reasoning.py and app.py are working (Version 1 complete)
- Estimated time: 2-3 hours once Version 1 is proven

---

## Session Update — reasoning.py Complete

### reasoning.py — COMPLETE ✅

**Key decisions made:**

1. **Dual loop verification DISABLED for MVP**
   - Flag: `ENABLE_VERIFICATION = False`
   - Reason: doubles token usage, hits 30K TPM limit on starter tier
   - Architecture is built and ready — flip flag to True with Tier 1+ OpenAI (100K TPM)
   - For demo: show the code exists, explain it's a production feature

2. **Deterministic escalation rules always run**
   - `apply_escalation_rules()` runs after every LLM response
   - Checks: chest pain, foamy urine + CKD, blurry vision, BP > 140, FBS > 200
   - Sets `escalate_to_doctor: true` and adds to signals list
   - Does NOT modify reasoning text (prevents verifier false positives)

3. **Rate limiting handled with:**
   - `asyncio.Semaphore(2)` — max 2 concurrent calls
   - 2 second pause after every call
   - 30 second wait when 429 rate limit hit
   - max_retries = 1 (2 total attempts)

**Test results — full panel of 8 patients:**
```
Rules alerted (no LLM needed):
  Priya Sharma   High  score: 85  (dizziness — Tier 1 symptom)
  Suresh Nair    High  score: 120 (dizziness + swelling — two Tier 1 symptoms)

LLM analysed:
  Rajan Kumar    Low   (plateau forming — borderline FBS)
  Meena Patel    High  (third consecutive missed log)
  Anita Rao      Medium (FBS + sleep + fasting missed)
  Fatima Sheikh  Medium (FBS + exercise + carbs + cravings)
  Deepak Verma   High  🚨 ESCALATE (BP 145 + medication missed + stress 5/5)

On track (skipped LLM entirely):
  Karthik Iyer   (perfect signals across all fields)
```

### Next step — ranker.py
Takes all three buckets, combines them, produces final sorted list.

**Ranking logic:**
- Sort by severity tier: High → Medium → Low → On Track
- Within each tier: sort by priority_score (from thresholds priority_scoring)
- For LLM results without a score: calculate score from signals
- Tiebreaker: has_tier1_symptom → consecutive_days → medication_missed

**Files still to build:**
```
ranker.py    ← next (short, ~15 mins)
app.py       ← Streamlit UI (~60 mins)
deploy       ← GitHub + Streamlit Cloud (~20 mins)
```

**To resume:**
```bash
cd ~/AI-PM-COURSE/Madumitra
source venv/bin/activate
export OPENAI_API_KEY="your-key-here"
touch ranker.py
```

---

## UI Improvements Backlog (Design Sprint Items)

### 1. Sample data preview in UI
Coach and mentor should be able to see WHO is loaded before running analysis.
- Show a table/expander with patient names, age, week number, key signals
- Helps mentor understand what's being tested
- Builds confidence before running the loop

### 2. Disable Run button until data is loaded
- Run reasoning loop button should be greyed out / disabled
- Until either sample data is loaded OR file is uploaded
- Prevents confusion of clicking Run with no data

### 3. Mobile + web friendly design
- Current layout works but needs proper responsive design
- Mobile: single column, larger tap targets
- Web: two-column (sidebar + main), clean cards
- Consider using Streamlit columns carefully for mobile
- Color-coded severity cards need to work on small screens
- Possibly use st.container with custom CSS

### 4. Coach feedback loop — CRITICAL for MVP
Current: Mark contacted + Dismiss buttons (UI only, not stored)
Need:
- Coach can mark: Acted On / Reprioritised / Dismissed / False Positive
- Each action stored with timestamp + original signal set
- Stored in a local JSON file (feedback_log.json) for MVP
- This becomes the ground truth dataset for calibration
- Every correction = labelled data point
- Maps to US-09 (Coach feedback loop) and US-14 (Coach override) in PRD
- Without this, MadhuMitra is just an alert tool not a learning system

### Design Sprint Plan
When resuming — do this BEFORE coding:
1. Sketch the mobile layout (what coach sees on phone)
2. Sketch the web layout (what mentor sees on desktop)
3. Design the feedback capture modal/form
4. Then code the improved app.py

### Files to update:
- app.py — all UI improvements
- feedback.py — new file for storing coach feedback

---

## UI Design Sprint Decisions

### Layout — responsive
- Mobile (< 768px): Option 1 — table with tap-to-expand rows
- Desktop (>= 768px): Option 3 — split view (list left, detail right)
- Detect screen width via JavaScript injected with st.components.v1.html
- Store selected patient in st.session_state["selected_patient"]

### Alert card redesign
- Compact table row per patient (not full cards)
- Columns: severity dot | name | severity pill | key signal chips (max 2) | actions
- Click row → detail panel opens (expand on mobile, right panel on desktop)
- Detail panel shows: reasoning, all signals, full today's data, comorbidities, actions
- Reasoning hidden by default — shown in detail panel only
- Signal chips: max 2 visible + "+N more" chip

### Progress messages during analysis
Use st.status() context manager:
  "Parsing patient logs..." 
  "Running rules check..."
  "Sending 5 patients to AI reasoning loop..."
  "Patient 1/5 analysed..."
  "Ranking results..."
  "Done — 7 alerts generated"

### Patient preview
- NOT in sidebar (gets unwieldy at 50+)
- Show as collapsible table in main area BEFORE results
- Columns: name, age, gender, week, FBS, key comorbidities
- Disappears once results are shown

### Feedback loop
- 👍 one tap → stored immediately
- 👎 → selectbox appears: "Not urgent / Severity too high / Too low / Already handled / Other"
- Mark contacted → cooling period dropdown: High (1d) / Medium (2d) / Low (3d)
- All stored in contact_log.json and feedback_log.json

### Follow-up tab
- Patients contacted within cooling period + same deviation → Follow-up tab
- New deviation during cooling → alert list with ⚠️ "New deviation" badge
- Coach can override or extend cooling from follow-up tab

### Tab structure (final)
1. 🔴 Alerts (N)
2. 🔄 Follow-up (N)
3. 🔵 Queue (N)
4. 💡 Nudge · On track
5. 📊 Feedback log

### Files to build/update
- app.py ← full rewrite with responsive layout
- feedback.py ← already built ✓
- feedback_log.json ← auto-created on first feedback
- contact_log.json ← auto-created on first contact

### How screen detection works in Streamlit
```python
import streamlit.components.v1 as components

# Inject JS to detect width and store in session state
components.html("""
<script>
const width = window.innerWidth;
window.parent.postMessage({type: 'streamlit:setComponentValue', value: width}, '*');
</script>
""", height=0)
```

Actually simpler approach — use st.session_state with a toggle:
Add a "Mobile view" toggle in sidebar for mentor to switch manually.
Default to desktop (split view). Toggle switches to mobile (table+expand).
Avoids JS complexity and works reliably in Streamlit.

---

## Version 2 — LLM-Based Priority Ranking (Agentic Upgrade)

### The gap Sri identified:
Current ranking uses a deterministic Python ranker (priority_score).
It doesn't account for:
- Patient age (58 = higher risk than 35)
- Comorbidity count and type (3 conditions vs 1)
- Program week context (week 8 not improving = more concerning)
- Signal combination weight (not just count)

The full reasoning text captures this nuance better than the score.

### The fix — LLM scores relative priority:
Instead of Python calculating a score per patient, the LLM reasons
across ALL flagged patients simultaneously and ranks them.

```python
# Version 2 approach
async def rank_by_reasoning(all_flagged_patients, protocol):
    """
    Single LLM call with all flagged patients.
    LLM reasons: "Given these 5 patients and their signals,
    rank them by clinical urgency considering age, comorbidities,
    signal combination, and program context."
    Returns ordered list with reasoning per patient.
    """
```

### Why this is more agentic:
- Agent reasons holistically across patient panel
- Not just per-patient but relative priority
- Considers context the rules engine can't (age, comorbidities, week)
- One LLM call replaces entire ranker.py logic
- This is the "prioritized alert list" vision from the PRD

### When to build:
- After pilot validation (4-6 weeks of coach corrections)
- Coach correction data tells us if current ranking is wrong
- If override rate > 20% — LLM ranking is worth building
