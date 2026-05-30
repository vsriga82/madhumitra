# MadhuMitra — Product Requirements Document
### Clinical Protocol Intelligence Layer for Diabetes Reversal Programs

**Date:** May 27, 2026
**Author:** Product Team
**Status:** Draft
**Version:** 1.0

---

## 1. Executive Summary

### Problem Statement

Health coaches and doctors running structured diabetes reversal programs in India spend 2–3 hours every morning manually reviewing patient logs — food intake, blood glucose readings, sleep, exercise, and medication adherence — before any real coaching can begin. For a coach managing 30–100 patients, this manual triage is not a minor overhead; it is the binding constraint on patient capacity, coaching quality, and program scalability. The problem compounds as programs grow: each new patient enrolled either requires a new hire or degrades existing coach coverage.

### Proposed Solution

MadhuMitra is a B2B clinical protocol intelligence layer that plugs into a diabetes reversal program's existing patient data streams and delivers a coach-facing AI briefing engine. Every morning, each coach opens MadhuMitra and receives a ranked, prioritized patient queue — with protocol-aware summaries, deviation flags, and one-sentence action reasons — built from the previous 24 hours of patient logs. What takes 2–3 hours of manual review today takes under 20 minutes with MadhuMitra, without removing the coach from the clinical loop.

### Business Impact

- **Capacity unlock:** Increases patients-per-coach ratio by 2–5x, enabling programs to scale revenue without proportional headcount growth
- **Defensible moat:** Protocol-specific intelligence and India-native food interpretation are not replicable by US RPM platforms; positions MadhuMitra as the category-defining tool in a white-space market with no direct Indian competitor today
- **Outcome protection:** Slippage detection in the critical weeks 6–12 dropout window reduces churn, protecting the clinical outcomes that programs depend on for credibility and retention

### Key Milestones

| Milestone | Target |
|---|---|
| Design & Prototype Complete | Week 6 |
| MVP Development Complete | Week 14 |
| Closed Beta (3–5 programs) | Week 16 |
| General Availability | Week 24 |

### Success Metrics

| Metric | Baseline | Target (6 months post-launch) |
|---|---|---|
| Morning review time per coach | 2–3 hours | < 20 minutes |
| Patients reviewed per coach-hour | ~15–20 | 60–80 |
| Patient dropout rate (weeks 6–12) | ~40–53% | < 25% |
| Coach daily active usage (DAU/MAU) | — | > 80% |
| Paying programs | 0 | 20–30 |
| Net Promoter Score (coaches) | — | > 50 |

---

## 2. Problem Definition

### 2.1 Customer Problem

**Who:** Health coaches (primary), supervising wellness doctors, and program operators running structured diabetes reversal programs in India — across digital-first programs (Fitterfly-tier), clinic-based programs, and independent practices. Coaches typically manage 20–100 patients simultaneously.

**What:** Coaches have no tool that reads and synthesizes patient logs for them. Each morning, they manually open WhatsApp, program apps, or spreadsheets to review individual logs — glucose readings, meal descriptions, exercise, sleep, and medication notes — one patient at a time. There is no system that interprets what these logs mean in the context of a specific reversal protocol, identifies who needs attention, or explains why.

**When:** Every single working morning, before any coaching begins. The review window is 7:00–10:00 AM — a fixed, high-cognitive-load block that precedes all actual patient interactions. As patient load grows beyond 50, this block expands to 3+ hours, often running into coaching time.

**Where:** Primarily mobile (WhatsApp-first workflows) and desktop dashboards within program management tools, in a fragmented multi-app environment. Coaches operate from home, clinics, and in transit — not fixed desktop workstations.

**Why:** No tool in the Indian market is built for the coach-as-reviewer use case. Patient-facing apps (Fitterfly, BeatO, SugarFit) capture the data but don't synthesize it for coaches. US RPM platforms (Glooko, Welldoc) offer dashboards, not briefings, and are built for US clinical workflows with EHR systems that Indian programs don't have. The interpretation layer — "what does this data mean for this patient on this protocol today?" — exists only in the coach's head.

**Impact of not solving:**

- Coach burnout and attrition (administrative grind, not clinical complexity, is the leading cause)
- Hard ceiling on program scale: every new patient requires a new coach, making unit economics worse as programs grow
- Outcome degradation: coaches default to first-come-first-served outreach, missing patients who silently drift off-protocol in weeks 6–12 — the highest-dropout window in reversal programs
- Clinical liability: missed early warning signs (medication non-adherence, dangerous glucose trends) that intensive coaching would catch

### 2.2 Market Opportunity

**TAM:** Global digital diabetes management market is ~$23–27 billion (2026), growing to $66–84 billion by 2032–2035 at 12–20% CAGR. The AI clinical workflow sub-segment is projected at $10.5 billion by 2034 (33% CAGR).

**SAM:** India digital health coaching market is USD 541M (2024), growing to USD 1.2B by 2030 at 14.5% CAGR. Structured reversal programs represent an estimated 20–30% of this. MadhuMitra targets program operators (B2B buyers), with an estimated 500–2,000 addressable program operators and clinic networks in India by 2027. **Estimated SAM: USD 50–150M by 2028.**

**SOM (Year 1–3):** 100 programs at ₹5,000–15,000/month = ₹6–18 crore ARR by Year 2; 500 programs = ₹30–90 crore ARR by Year 3.

**Current solutions and their gaps:**

| Existing Approach | Gap |
|---|---|
| Manual log review (WhatsApp, spreadsheets) | No synthesis, no prioritization, takes 2–3 hours |
| Patient-facing apps (Fitterfly, BeatO) | Capture data for patients; no coach briefing layer |
| US RPM dashboards (Glooko) | Data visualization, not AI summarization; US workflow-dependent; not India-native |
| Internal tools built by programs | Non-scalable, program-specific, unavailable to others |

**Why now:** CGM adoption is accelerating in India (12.4% CAGR), generating richer data streams that amplify the review problem. AI-assisted clinical documentation (Nuance DAX, Dragon Copilot) has normalized the concept of AI reducing clinician overhead. India's reversal program sector is in aggressive growth mode (Redial Clinic targeting 1 lakh patients by 2026 alone). The coach-tooling layer is entirely unoccupied.

### 2.3 Business Case

**Revenue potential:** ₹18–90 crore ARR by Year 3 (₹2,000–3,500/coach/month, tiered by program size). Land-and-expand model with upsell modules (analytics, protocol customization, EHR integrations).

**Cost savings for buyers:** A coach saving 2 hours/day at ₹300/hour = ₹18,000/month in recaptured productivity per coach. MadhuMitra at ₹2,500/coach/month delivers approximately 7:1 ROI before any coaching-quality improvement is counted.

**Strategic alignment:** MadhuMitra is infrastructure, not a program. It integrates with existing program platforms rather than competing with them, creating a large pool of potential distribution partners. Protocol intelligence and India-native food interpretation compound as a proprietary data moat over time.

**Risk of inaction:** The coach-tooling layer will be occupied — either by a US platform that adapts to India or by a well-funded Indian startup. First-mover advantage is significant in a market that consolidates around trusted tools over 3–5 years.

---

## 3. Solution Overview

### 3.1 What We're Building

MadhuMitra is a web and mobile application for health coaches and program operators. At its core is the **Morning Brief** — an AI-generated, protocol-aware prioritized patient queue delivered fresh each morning. The system ingests the prior 24 hours of patient log data (via integrations with program apps, manual log uploads, or CSV imports), interprets each patient's data against their assigned reversal protocol, and surfaces a ranked list of patients who need attention — with a one-sentence reason per patient explaining the flag.

Coaches act on the brief rather than generate it. They spend their morning on outreach and coaching conversations, not on data triage. The coach remains in the clinical loop for all decisions; MadhuMitra surfaces and prioritizes, never acts autonomously.

The operator layer provides a program-level view: coach efficiency metrics, cohort health trends, and early warning signals for program-wide drift.

### 3.2 Feature Scope

| # | Feature | Priority | Description |
|---|---|---|---|
| F1 | Morning Brief — Prioritized Patient Queue | P0 | AI-generated ranked list of patients requiring coach attention today, with one-sentence protocol-aware reason per patient. Delivered by 7:30 AM. Refreshes on-demand. |
| F2 | Protocol-Aware Log Interpretation Engine | P0 | Interprets patient logs (glucose, food, medication, sleep, exercise) in the context of their assigned reversal protocol. Distinguishes meaningful deviations from expected fluctuations. |
| F3 | India-Native Food Recognition | P0 | Parses Indian food log entries (text, photos, vernacular names, regional dishes) and maps them to macro/carb profiles relevant to reversal protocols. Covers 5,000+ Indian dishes at launch. |
| F4 | Patient Profile + 30-Day Timeline | P0 | Per-patient view: protocol phase, recent log summary, 30-day glucose trend, logging frequency, and coach interaction history. Accessible in one tap from the Morning Brief. |
| F5 | Slippage Detection Alerts | P1 | Proactively flags patients in the weeks 6–12 window showing declining log frequency, plateauing glucose trends, or engagement patterns correlated with historical dropout. Separate alert category from clinical flags. |
| F6 | Coach Notes & Action Log | P1 | Allows coaches to record interventions, tag patients with follow-up actions, and mark patients as reviewed. Builds an auditable coaching record per patient. |
| F7 | Operator Dashboard | P1 | Program-level view: patients-per-coach ratio, average review time, cohort glucose trends, at-risk patient count, and coach efficiency metrics. Visible to program operators only. |
| F8 | Data Ingestion Integrations | P1 | API connectors and CSV import for major Indian program platforms (initially: manual upload, WhatsApp log parsing, CSV; later: Fitterfly, BeatO API integrations). |
| F9 | Protocol Library | P2 | Configurable protocol templates (low-carb, intermittent fasting, Mediterranean-Indian hybrid, etc.) that operators define once and apply across their patient cohort. |
| F10 | Doctor Escalation View | P2 | Filtered view for supervising physicians showing only coach-escalated patients and MadhuMitra's highest-urgency flags. Reduces clinical review to a sub-5-minute daily task. |
| F11 | Multi-language Support (Hindi) | P2 | Hindi-language interface and food log parsing for coaches and patients in Hindi-speaking markets. |
| F12 | Analytics & Outcomes Reporting | P2 | Program-level HbA1c trajectory, medication reduction tracking, and patient outcome cohort reports. Designed for operator use and enterprise sales conversations. |

### 3.3 Out of Scope (v1)

- Patient-facing features of any kind (MadhuMitra is a coach/operator tool, not a patient app)
- Autonomous AI coaching or AI-generated patient messages sent without coach review
- Direct CGM device integrations (addressed via CSV/manual upload in v1; API in v2)
- EHR integrations for Indian hospital systems (v2 / enterprise tier)
- Tamil, Telugu, and other regional language support (v2)
- Billing, payments, or appointment scheduling
- Telemedicine or video consultation features
- Medication prescription or clinical decision support classified as a medical device under CDSCO

### 3.4 MVP Definition

**Core features for MVP (P0 only + F5, F6, F8):** Morning Brief, Protocol-Aware Engine, India Food Recognition, Patient Profile, Slippage Detection, Coach Notes, and CSV-based data ingestion.

**MVP success criteria:**
- Coach completes full patient queue review in < 20 minutes for a 30-patient panel
- Morning Brief correctly prioritizes the top 5 "needs attention" patients (validated by coach agreement rate > 70%)
- Food recognition correctly identifies and parses > 85% of logged Indian food entries
- 3+ beta programs complete 4-week pilot without requesting to revert to prior workflow

**MVP target date:** Week 16 (beta release)

**Learning goals:**
- Does the prioritization order match coach intuition? Where does AI ranking diverge?
- Which protocol types require the most calibration in the interpretation engine?
- Do coaches adopt mobile or desktop? What is the morning access pattern?
- What is the minimum data freshness required for the Brief to feel trustworthy?

---

## 4. User Stories & Requirements

### 4.1 User Stories

---

**Story 1 — The Morning Brief (Core)**

As a **health coach managing 40 patients in a diabetes reversal program**,
I want to **open MadhuMitra each morning and immediately see which patients need my attention today, ranked by urgency, with a plain-language reason for each flag**,
So that **I can spend my first 20 minutes on decisions and outreach instead of data triage**.

Acceptance Criteria:
- [ ] Brief is available by 7:30 AM based on logs submitted up to midnight
- [ ] Each patient in the queue shows: name, flag reason (1 sentence), severity level (urgent / watch / routine), and last log timestamp
- [ ] Coach can tap any patient to open their full profile without leaving the queue
- [ ] Coach can mark a patient as "reviewed" and optionally add a note
- [ ] Queue re-sorts after coach actions; unreviewed urgent patients remain at top
- [ ] Brief can be refreshed on-demand for real-time updates

---

**Story 2 — Protocol-Aware Flagging**

As a **health coach**,
I want to **see flags that account for where a patient is in their protocol**, not just raw threshold breaches,
So that **I don't waste time on false alarms and actually catch what matters**.

Acceptance Criteria:
- [ ] Flags are generated relative to each patient's assigned protocol and protocol phase (e.g., a glucose reading of 140 mg/dL is flagged differently on day 3 of induction vs. day 60 of maintenance)
- [ ] Flags distinguish between clinical urgency (e.g., glucose > 250 mg/dL, missed medication), protocol deviation (e.g., 3 consecutive high-carb meals on a low-carb protocol), and engagement risk (declining log frequency)
- [ ] False positive rate (coach dismisses flag as irrelevant) < 30% in month 1, < 15% after 4 weeks of use

---

**Story 3 — India Food Log Parsing**

As a **health coach**,
I want to **see a coach-readable interpretation of what my patient actually ate**, not just a raw text entry,
So that **I can quickly assess protocol compliance without looking up every dish**.

Acceptance Criteria:
- [ ] System parses free-text food entries and returns: dish name, estimated macros, carb flag (within / exceeding protocol threshold), and a brief note (e.g., "2 chapatis at dinner — exceeds daily carb limit by ~30g")
- [ ] Supports regional Indian dish names, home cooking descriptions, mixed-language entries (Hinglish)
- [ ] Recognition coverage: > 85% of entries correctly classified at launch
- [ ] Unrecognized entries are surfaced to coach clearly, not silently dropped

---

**Story 4 — Slippage Detection**

As a **health coach**,
I want to **be alerted when a patient is showing early signs of disengagement**, not just when they've already dropped off,
So that **I can intervene during the critical window before they quit the program**.

Acceptance Criteria:
- [ ] System identifies patients in weeks 6–15 of their program who show: ≥ 2 consecutive days of missing logs, declining log completeness trend over 7 days, or glucose plateau after 4+ weeks of improvement
- [ ] Slippage alerts are visually distinct from clinical urgency flags in the Morning Brief
- [ ] Coach can snooze a slippage alert with a reason (e.g., "Patient traveling this week") for up to 7 days
- [ ] Slippage alert accuracy tracked and reported to operator dashboard

---

**Story 5 — Operator ROI View**

As a **program operator**,
I want to **see real-time data on how efficiently my coaches are working and how my patient cohort is performing**,
So that **I can justify MadhuMitra's cost, identify underperforming coaches, and present outcomes data to enterprise clients**.

Acceptance Criteria:
- [ ] Operator dashboard shows: average coach morning review time (this week vs. prior week), patients reviewed per coach-hour, at-risk patient count, 30-day cohort glucose trend, and logging compliance rate
- [ ] Data is updated daily; viewable by program and by individual coach
- [ ] "Time saved this month" metric is prominently displayed (format: "Your team recaptured X hours of coaching time")
- [ ] Operator can export cohort data as CSV for reporting

---

### 4.2 Functional Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| FR1 | System generates the Morning Brief by 7:30 AM daily for all active coaches | P0 | Based on logs submitted up to midnight |
| FR2 | Morning Brief ranks patients by urgency using a multi-signal scoring model (clinical severity × protocol deviation × engagement trend) | P0 | Scoring logic must be explainable to coaches |
| FR3 | Each patient flag includes a plain-language reason (max 25 words) | P0 | No clinical jargon; readable in 3 seconds |
| FR4 | System interprets food log entries against assigned protocol carb/macro thresholds | P0 | Per-patient protocol config required |
| FR5 | Food recognition covers ≥ 5,000 Indian dishes at launch, including regional and vernacular names | P0 | Must support Hinglish and mixed-script entries |
| FR6 | Per-patient profile displays: 30-day glucose trend, logging frequency chart, protocol phase, medication list, and coach notes history | P0 | Accessible in ≤ 2 taps from Brief |
| FR7 | Coach can add a note to any patient, tag it with an action type (called, messaged, escalated), and set a follow-up reminder | P1 | Notes are timestamped and stored per patient |
| FR8 | Slippage detection engine flags patients in weeks 6–15 with ≥ 2 of: missing logs, engagement decline, or glucose plateau | P1 | Configurable sensitivity by operator |
| FR9 | Operator dashboard displays: review time saved, patients-per-coach-hour, at-risk count, cohort glucose trend, logging compliance | P1 | Daily refresh; coach-level drill-down |
| FR10 | Data ingestion supports CSV upload (manual) and structured WhatsApp export parsing at launch | P1 | API integrations in v2 |
| FR11 | Operator can configure protocol templates with: carb thresholds, fasting windows, medication schedule, and phase durations | P2 | Applied per-patient at enrollment |
| FR12 | Doctor escalation view shows only coach-escalated and system-urgency-flagged patients | P2 | Read-only; no write access for doctors in v1 |
| FR13 | System supports multi-coach programs with role-based access (coach / operator / doctor) | P1 | Single sign-on per program account |
| FR14 | All patient data is encrypted at rest (AES-256) and in transit (TLS 1.3) | P0 | Non-negotiable for DPDP compliance |
| FR15 | Audit log maintained for all data access and coach actions | P0 | Required for DPDP Act compliance |

### 4.3 Non-Functional Requirements

**Performance:**
- Morning Brief generation: < 2 minutes for a 100-patient cohort after data cutoff
- Individual patient profile load: < 1.5 seconds on a 4G mobile connection
- Food log parsing response: < 3 seconds per entry
- System uptime: 99.5% SLA (Brief generation window 6:00–7:30 AM is highest priority)

**Scalability:**
- Support programs with up to 2,000 active patients per program instance at launch
- Architecture must support 10,000+ concurrent patients across all programs by Year 2
- Data ingestion pipeline must handle burst uploads (end-of-day log batches from 100+ patients)

**Security & Privacy:**
- All patient data stored on India-based cloud infrastructure (AWS Mumbai or equivalent)
- DPDP Act compliance: explicit consent flows for patient data ingestion, data minimization, right-to-deletion support
- Role-based access control: coaches see only their assigned patients; operators see all; doctors see escalated only
- No patient data used for model training without explicit, documented consent

**Reliability:**
- Morning Brief must not fail silently — if data ingestion is incomplete, coach must be notified with a partial brief and explicit data-gap warning
- System must degrade gracefully: if AI engine is unavailable, fall back to last-24-hour raw log view with a status banner

**Usability:**
- Mobile-first design: full Morning Brief workflow must be completable on a phone screen (Android priority, given Indian market composition)
- Coach onboarding to first useful Brief: ≤ 30 minutes from account creation to first AI-generated queue
- No mandatory training requirement for basic use; in-product tooltips sufficient for onboarding

**Compliance:**
- Not classified as a Software as Medical Device (SaMD) under CDSCO in v1 — MadhuMitra surfaces information for coach review, does not make autonomous clinical recommendations
- All communications (including marketing) must accurately represent the tool as a workflow assistant, not a diagnostic or treatment tool

---

## 5. Go-to-Market Strategy

### Target Segments & Sequencing

**Phase 1 — Early Traction (Months 1–6):** Independent diabetes health coaching practices and small clinic-based reversal programs (10–30 coaches). Decision cycle is 4–8 weeks. The doctor or program founder is both the user and the buyer. ROI is personal and immediate.

**Phase 2 — Growth (Months 6–18):** Mid-size digital therapeutics programs (30–150 coaches, 1,000–5,000 patients). Programs like Breathe Well-being, Freedom From Diabetes, and emerging clinic networks. Decision cycle 2–4 months; requires a structured pilot with outcome data.

**Phase 3 — Enterprise (Months 18+):** Hospital-based diabetes centers (Apollo Super6, Narayana specialty programs, corporate wellness programs). 6–18 month decision cycles; requires compliance documentation, EHR integration readiness, and published outcomes.

### Launch Plan

**Beta (Week 16–24):** Invite 3–5 programs identified through design partnership phase. Free access in exchange for weekly feedback sessions and permission to instrument coaching workflows. Target: ≥ 3 programs actively using the Brief after 4 weeks.

**General Availability (Week 24):** Paid access opens. Announce on LinkedIn and through diabetes coach communities (ADCES India, NIN alumni networks, clinical dietitian WhatsApp networks). Publish a case study from a beta program with time-saved and patient-outcome data.

**Enterprise pipeline (Month 6+):** Formal sales motion targeting program operators at Tier-2 digital health programs. Reference customer data from Phase 1 is the primary trust-builder.

### Pricing

Per-coach per-month, tiered by program size:

| Tier | Coaches | Price/Coach/Month | Features |
|---|---|---|---|
| Starter | 1–5 | ₹3,500 | Morning Brief, Protocol Engine, Food Recognition, Patient Profiles |
| Growth | 6–20 | ₹2,500 | All Starter + Slippage Detection, Operator Dashboard, Coach Notes |
| Scale | 21–50 | ₹1,800 | All Growth + Protocol Library, Doctor Escalation View |
| Enterprise | 50+ | Custom | All Scale + SLA, dedicated onboarding, API integrations, audit exports |

Free 30-day pilot for programs ≥ 10 coaches, conditioned on a structured feedback commitment.

### Sales Motion

The primary sales asset is the time-savings ROI number, computed from the first day of use: *"Your coaches reviewed 45 patients in 17 minutes this morning."* This number is displayed prominently in the operator dashboard and referenced in every renewal and expansion conversation.

---

## 6. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| AI brief quality is low in early weeks; coaches lose trust and disengage | High | High | Build explicit feedback loop ("Was this flag useful?") from Day 1; use disagreement data to retrain. Set expectation during onboarding that accuracy improves over 2–4 weeks. Guarantee partial refund if coach agreement rate stays below 60% after 30 days. |
| Data ingestion is inconsistent (patients log irregularly, in varied formats) | High | High | Build graceful degradation into the Brief: show partial data with explicit gaps rather than hallucinating completeness. Train coaches on what "good logging" looks like — MadhuMitra can surface patients with < 2 logs/day as a data quality flag. |
| Program operators don't make the purchase decision (decision stalls in evaluation) | Medium | High | Target independent clinic operators first (single decision-maker). For programs, establish a 30-day free pilot with defined success criteria in writing before starting. Remove purchase friction with no long-term commitment in Year 1. |
| DPDP Act compliance creates procurement blocker | Medium | High | Engage a health-tech legal advisor pre-launch. Publish a clear data processing addendum (DPA). Build consent flows into the patient enrollment step on operator side, not the coach side. |
| A well-funded Indian startup or Glooko/Welldoc clone enters the market | Low | High | Speed of execution matters more than any single feature. Build the protocol library and India food database as proprietary assets. Sign exclusivity or preferred partnerships with 2–3 anchor programs during Year 1. |
| Coach adoption is low if mobile experience is poor | Medium | Medium | Mobile-first in design sprints. Prototype tested on Android mid-range devices (₹10,000–20,000 price range) from Day 1. No desktop-only feature in P0. |
| Program operators change their patient management platforms mid-contract | Low | Medium | API-first data architecture ensures MadhuMitra can ingest from any source. Avoid tight coupling to any single platform. |

---

## 7. Timeline & Milestones

| Milestone | Target Date | Deliverables | Success Criteria |
|---|---|---|---|
| Design Partnership Signed | Week 2 | 2–3 pilot programs committed to co-design | Signed LOIs with access to real coach workflows |
| UX Research & Prototype | Week 4 | Coach workflow map, Morning Brief prototype | 3+ coaches validate prioritization concept in usability test |
| Design Complete | Week 6 | Final mobile + web mockups for P0 features | Design review approved by stakeholders |
| India Food Database v1 | Week 8 | 5,000-dish recognition corpus with macro mappings | 85%+ recognition on test set of 500 real patient logs |
| Protocol Engine v1 | Week 10 | Low-carb, IF, and general reversal protocols configurable | Correct flag generation on 20 synthetic patient scenarios |
| MVP Development Complete | Week 14 | All P0 features + F5, F6, F8 | All acceptance criteria for Stories 1–4 pass QA |
| Closed Beta Launch | Week 16 | 3–5 programs onboarded | ≥ 3 programs actively using Brief after 7 days |
| Beta Feedback Iteration | Week 16–22 | 2 iteration sprints based on beta data | Coach agreement rate > 65%; DAU/MAU > 70% |
| General Availability | Week 24 | Public launch, pricing live | First paying customer; < 1% critical error rate |
| P1 Features Complete | Week 32 | Operator dashboard, slippage detection, coach notes | Operator adoption in 80%+ of signed programs |

---

## 8. Team & Resources

| Role | Allocation | Notes |
|---|---|---|
| Product Manager | 1 × 100% | Owns roadmap, beta program relationships, success metrics |
| ML / AI Engineer | 2 × 100% | Morning Brief engine, food recognition model, protocol interpretation |
| Backend Engineer | 2 × 100% | Data ingestion pipeline, API layer, user auth, audit logging |
| Frontend / Mobile Engineer | 1 × 100% | Android-first mobile app, web dashboard |
| UX Designer | 1 × 100% | Mobile-first design, coach and operator UI |
| Clinical Advisor | 1 × 20% | Protocol validation, flag logic review, DPDP guidance |
| QA Engineer | 1 × 100% (from Week 10) | Test coverage, performance testing, security review |

**Estimated infrastructure budget (Year 1):**

| Item | Estimated Monthly Cost |
|---|---|
| Cloud compute + storage (AWS Mumbai) | ₹80,000–1,20,000 |
| LLM API costs (food recognition, brief generation) | ₹40,000–80,000 |
| Monitoring, security tooling | ₹20,000–40,000 |
| **Total infrastructure** | **₹1,40,000–2,40,000/month** |

Break-even on infrastructure: ~60–80 paying coaches across programs.

---

## 9. Open Questions

1. **Clinical classification:** At what point does protocol-aware flagging (e.g., "patient's glucose is dangerously elevated") trigger CDSCO SaMD classification? Legal review needed before launch to define the precise boundaries of MadhuMitra's clinical function.

2. **WhatsApp log parsing:** Can patient food/glucose logs submitted via WhatsApp be parsed reliably at scale given the unstructured format? A technical spike is needed in Sprint 1 to assess feasibility and accuracy before committing to this as a primary ingestion path.

3. **Protocol IP:** If program operators define proprietary reversal protocols in MadhuMitra's Protocol Library, who owns that protocol data? Does MadhuMitra have rights to use it for model improvement? This needs to be resolved in the Terms of Service before beta.

4. **Minimum viable logging quality:** What is the minimum logging frequency and completeness required for the Morning Brief to be clinically trustworthy? Define the threshold at which MadhuMitra should display a "insufficient data" warning rather than generate a potentially misleading brief.

5. **Coach-patient ratio benchmarks:** Is there a validated target patients-per-coach ratio for diabetes reversal programs? This number would anchor both the ROI narrative and the slippage detection sensitivity settings.

6. **Integration partnership strategy:** Should MadhuMitra seek formal API partnerships with Fitterfly, BeatO, or SugarFit in Year 1, or is this a competitive risk? Early partnership conversations should explore whether these platforms view MadhuMitra as a complement or a threat.

---

## 10. Assumptions Made

1. Coaches currently spend 2–3 hours daily on manual log review, as described in the problem definition and corroborated by RPM literature. This assumption is the core of the value proposition and must be validated through UX research in Weeks 1–4.

2. Program operators are the economic buyers; coaches are the end users. Sales motion, pricing, and ROI messaging are designed for this distinction.

3. The India food database can be built to 85%+ recognition coverage within 8 weeks using a combination of public nutritional databases (NIN India, IFCT), crowdsourcing from beta programs, and LLM-assisted classification.

4. MadhuMitra does not classify as a Software as Medical Device (SaMD) under CDSCO regulations in its v1 form, given that it surfaces information for coach review rather than making autonomous clinical recommendations. This assumption requires legal validation.

5. Mobile-first design is required because Indian health coaches primarily use Android smartphones in their work. Desktop is secondary.

6. Data residency in India is required for DPDP compliance and is achievable on AWS Mumbai or an equivalent IaaS provider within the engineering budget.

7. The "coach-in-the-loop" principle is a non-negotiable design constraint. MadhuMitra never sends patient communications, makes treatment suggestions, or takes any action without explicit coach initiation.

8. Pricing benchmarks are derived from US RPM markets adjusted downward 5–10x for India SaaS norms. Actual price sensitivity should be validated during beta pilot conversations.

---

*Research inputs: MadhuMitra Market Research Report (May 2026) and MadhuMitra User Research Report (May 2026).*
