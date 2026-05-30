# PRD Evaluation Report: MadhuMitra v1.0
### Clinical Protocol Intelligence Layer for Diabetes Reversal Programs

**Evaluated:** May 27, 2026
**PRD Version:** prd-v1.md
**Evaluator:** PRD Evaluator Skill

---

## Overall Score: 11 / 16 items passing

---

## Section 1: Problem Definition — 5/8

| Item | Status | Notes |
|------|--------|-------|
| 1.1 Problem & JTBD | ✅ | Clearly stated: coaches spend 2–3 hours/morning on manual log triage before any coaching begins. JTBD ("know who needs me today") is implicit and well-supported. |
| 1.2 Customer personas defined | ✅ | Four personas with role, context, and pain point. Overloaded Nutritionist-Coach, Stretched Wellness Doctor, Scaling Program Operator, and Independent Coach are all specific and differentiated. |
| 1.3 Problem validated with data | ✅ | Extensively validated: 2–3 hour daily figure, 53% dropout rate, 101M Indian diabetics, market sizing from multiple research firms, and two full research reports as inputs. |
| 1.4 Why this problem is worth solving | ✅ | Section 2.3 enumerates consequences of inaction: coach burnout and attrition, hard patient capacity ceiling, outcome degradation, and clinical liability from missed early-warning signs. |
| 1.5 Defensible moat defined | ✅ | Protocol intelligence, India-native food database, and proprietary data accumulation are mentioned. Passes, but the moat is scattered across three sections (2.3, 3.2, and Strategic Implications) rather than stated once, clearly. |
| 1.6 Justification for AI over rule-based systems | ❌ | The PRD never explains why `if glucose > 250 → flag` rules fail. The case for ML over a deterministic threshold engine is never made. |
| 1.7 Unstructured data types + ML need explained | ❌ | WhatsApp logs, food photos, and vernacular text are named in passing, but there's no explanation of why ML is necessary — i.e., why keyword rules or lookup tables can't parse "2 chapatis + aloo sabzi at 7pm." |
| 1.8 Differentiated from general AI tools | ❌ | No mention of why a coach can't just paste logs into ChatGPT each morning. The PRD doesn't address this obvious objection. |

---

### Gaps to Address — Section 1

**1.6 — Justification for AI over rule-based systems**

- **What's missing:** An explanation of why threshold-based rules (e.g., "flag all glucose readings > 250 mg/dL") fail to solve this problem, and why machine learning or LLM-based interpretation is required.
- **What to write:** Add a paragraph in Section 2.1 or 3.1 such as: *"Rule-based systems fail here because the clinical significance of any data point is contextual. A glucose reading of 160 mg/dL may be a flag on day 3 of a low-carb induction but entirely expected on day 1 of Diwali for a patient whose protocol allows a one-day exception. A patient logging 'roti + dal' may be on-protocol or severely off-protocol depending on their specific carb ceiling and meal timing. The number of meaningful context variables — protocol phase, patient history, deviation pattern, engagement trend — grows non-linearly across 50+ patients and makes hand-written rules brittle and unscalable. MadhuMitra requires ML/LLM reasoning to interpret within-context rather than against a universal threshold."*

---

**1.7 — Unstructured data types + ML need explained**

- **What's missing:** A clear inventory of the unstructured inputs MadhuMitra must process, and an explanation of why each requires ML rather than structured parsing or lookup tables.
- **What to write:** Add a dedicated sub-section (suggested location: Section 2.1 or a new Section 2.2 "Why This Requires ML") structured as:

  | Unstructured Input | Example | Why rules fail |
  |---|---|---|
  | Free-text food logs | "ate normally today, had mom's cooking" | No structured format; meaning requires cultural and contextual inference |
  | Vernacular + mixed-script entries | "2 chapati + dal fry + थोड़ा चावल" | Multi-language, unit-free; lookup tables miss regional dish variations |
  | Food photos | Image of a thali | Visual classification required; no text to parse |
  | WhatsApp conversation logs | "coach, I skipped lunch but had a heavy snack around 4" | Unstructured narrative; timing, quantities, and intent must be inferred |
  | Medication adherence notes | "took metformin late, after dinner instead of before" | Free-form deviation description; requires temporal and protocol-relative interpretation |

---

**1.8 — Differentiation from general AI tools (ChatGPT, Copilots)**

- **What's missing:** An explicit answer to the question: "Why can't a coach just use ChatGPT to summarize patient logs each morning?"
- **What to write:** Add a short paragraph or bullet group in Section 3.1 or a new "Why Not a General AI Tool?" sidebar:
  *"A coach could theoretically paste 30 patient logs into ChatGPT each morning. This fails in practice for four reasons: (1) **No protocol context** — a general LLM has no knowledge of a specific program's reversal protocol, carb thresholds, or patient history; each prompt would require re-explaining the entire context. (2) **No persistent memory** — patient baseline, prior interventions, and 30-day trends are invisible to a stateless chat interface. (3) **No structured output** — a chat response is a paragraph; coaches need a ranked, actionable queue they can act on in 20 minutes, not a wall of text. (4) **No integration** — logs must be manually copy-pasted from every source, negating any time savings. MadhuMitra is purpose-built with program protocol context, longitudinal patient data, and a structured coach-optimized output format that a general AI tool cannot replicate without becoming MadhuMitra."*

---

## Section 2: Solution Definition — 3/4

| Item | Status | Notes |
|------|--------|-------|
| 2.1 Visual user flow included | ❌ | No diagram, flowchart, or structured [Input → Processing → Output] sequence is present. User stories imply a flow, but no explicit flow is drawn. |
| 2.2 AI drawbacks addressed | ✅ | Coach-in-the-loop principle stated throughout, false positive rate target set in Story 2 (<30% month 1, <15% after 4 weeks), audit log in FR15, and graceful degradation on AI failure (Section 4.3 Reliability). Hallucination isn't named explicitly but the mitigations are substantive and cover the risk. |
| 2.3 Functional requirements in user story format | ✅ | Five well-formed stories using "As a / I want / So that" format, each with specific, testable acceptance criteria. |
| 2.4 Agent capabilities and system behavior described | ✅ | Autonomy boundaries are clearly stated: "surfaces and prioritizes, never acts autonomously." Out-of-scope items explicitly exclude autonomous patient messaging. FR13–FR15 define role-based access and audit behavior. |

---

### Gaps to Address — Section 2

**2.1 — Visual user flow**

- **What's missing:** A structured representation of how data flows through MadhuMitra from ingestion to the coach's action. This is the most common thing engineering, design, and stakeholders ask for first.
- **What to write:** Add a flow between Sections 3.1 and 3.2, structured like this:

  ```
  DATA SOURCES          MADHUMITRA ENGINE             COACH INTERFACE
  ─────────────         ──────────────────            ───────────────
  Patient app logs  ──► Data Ingestion Layer      ──► Morning Brief
  WhatsApp logs     ──► (CSV / API / parsing)         (prioritized queue)
  Manual CSV upload ──►                                     │
                        Protocol Engine             Coach taps patient
                        (flag scoring vs.      ──►  ↓
                         assigned protocol)         Patient Profile
                                                    (30-day trend, logs,
                        India Food Recognizer        notes history)
                        (macro mapping)                    │
                                                    Coach adds note /
                        Slippage Detector       ──►  marks reviewed /
                        (weeks 6–15 signals)         escalates to doctor
                             │
                        Operator Dashboard
                        (review time, cohort
                         health, efficiency)
  ```

  The key thing to convey: MadhuMitra is a **read → synthesize → surface** system. It never writes back to patients. All actions flow through the coach.

---

## Section 3: Core Metrics — 3/4

| Item | Status | Notes |
|------|--------|-------|
| 3.1 North Star metric defined | ❌ | Six metrics are listed in the success table with no designation of which one is the North Star. "Morning review time per coach" is the strongest candidate and is listed first, but it's never labeled or elevated above the others. |
| 3.2 Primary metrics listed | ✅ | Morning review time (2–3 hrs → <20 min), patients-per-coach-hour (15–20 → 60–80), patient dropout rate (40–53% → <25%) are all quantifiable with baselines and targets. |
| 3.3 Secondary/supporting metrics | ✅ | DAU/MAU (>80%), paying programs (20–30), NPS (>50) cover adoption, retention, and satisfaction. |
| 3.4 Metrics measurable and trackable | ✅ | All metrics have units, baselines or targets, and are measurable via product instrumentation or operator dashboard. |

---

### Gaps to Address — Section 3

**3.1 — North Star metric**

- **What's missing:** One metric designated as the single indicator of whether MadhuMitra is succeeding at its core purpose. Having six equal metrics makes it hard for the team to know what to optimize for when trade-offs arise.
- **What to write:** Designate one metric explicitly in the success table header, and add a one-sentence rationale. The best candidate is:

  > **North Star: "Morning review time per coach" (target: <20 minutes)**
  >
  > *Rationale: This metric directly captures whether MadhuMitra is delivering its core promise. If coaches are reviewing their full patient panel in under 20 minutes, the AI engine is working, the prioritization is trusted, and coaches are getting their time back. All other metrics either lead (data quality, adoption) or lag (patient outcomes, NPS) this one.*

  The other metrics remain as primary (coach capacity ratio, dropout rate) and secondary (DAU/MAU, NPS, paying programs), but the North Star gives the team a single rallying point.

---

## Top 3 Priorities

**Priority 1 — Add the user flow diagram (2.1)**
This is the single most-requested artifact by engineering and design teams. Without it, every feature conversation requires re-establishing how the system works end-to-end. It's also fast to add — the information exists in the PRD already, it just needs to be structured into a flow. Fix this before the first engineering kickoff.

**Priority 2 — Make the AI case explicit (1.6 + 1.7)**
The PRD currently assumes AI is the right approach without arguing for it. For stakeholders, investors, and clinical advisors who will ask "why can't you just set threshold alerts?", the absence of this argument is a credibility gap. The answer exists in the product's DNA — protocol context, multi-variable interpretation, unstructured Indian food text — but it needs to be written down. This also informs ML architecture decisions, so it's valuable for the engineering team too.

**Priority 3 — Designate a North Star metric and address ChatGPT differentiation (3.1 + 1.8)**
These two items are linked. The North Star ("morning review time") answers "what does success look like?" The ChatGPT differentiation answers "why this product, not a generic tool?" Both are questions every stakeholder and investor will ask, and both have clear answers that are just missing from the document.

---

## Strengths

**1. Exceptional research grounding.** The PRD is built on two full research reports with specific, cited statistics. Every key claim — 2–3 hours of daily review, 53% dropout rate, 101M diabetics, 7:1 ROI calculation — is traceable to a source. This level of evidence is rare in early-stage PRDs and significantly increases stakeholder confidence.

**2. User stories with real acceptance criteria.** The five user stories in Section 4.1 are well-formed and genuinely testable. The false positive rate target in Story 2 (<30% month 1, <15% after 4 weeks), the food recognition accuracy floor (>85%), and the 4-week beta success criteria are specific enough that engineering and QA can build against them. Most PRDs at this stage have vague acceptance criteria; these are not.

**3. Coach-in-the-loop as a first-class design constraint.** The principle that MadhuMitra "surfaces and prioritizes, never acts autonomously" is stated in Section 3.1 and enforced consistently through out-of-scope items, functional requirements, and the risk table. This matters for regulatory positioning (avoids SaMD classification), for coach trust (they feel empowered, not replaced), and for product ethics. Making it explicit rather than implicit is good craft.

---

*Evaluated against the PRD Evaluation Checklist covering Problem Definition (8 items), Solution Definition (4 items), and Core Metrics (4 items). Score: 11/16.*
