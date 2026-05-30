import yaml
import json
from pathlib import Path


# ── Load all protocol files ───────────────────────────────────
def load_protocol_files():
    """
    Loads all four protocol components into memory.
    Called once at startup — reused for all patients in batch.
    Returns: alert_guide, thresholds, guardrails, output_schema

    RAG NOTE (Version 2):
    This function will be replaced by a RAG retriever that pulls
    only relevant protocol sections per patient from ChromaDB.
    Each call retrieves ~20% of the protocol instead of 100%.
    See HANDOFF.md → RAG Roadmap for the implementation plan.
    """
    base = Path(__file__).parent / "protocol"

    with open(base / "alert_guide_v1.md", "r") as f:
        alert_guide = f.read()

    with open(base / "thresholds_v1.yaml", "r") as f:
        thresholds = yaml.safe_load(f)

    with open(base / "guardrails_v1.md", "r") as f:
        guardrails = f.read()

    with open(base / "output_schema_v1.md", "r") as f:
        output_schema = f.read()

    return alert_guide, thresholds, guardrails, output_schema


# ── Compact thresholds summary ────────────────────────────────
def extract_key_thresholds(thresholds):
    """
    Extracts only the clinical numbers the LLM needs for reasoning.
    Returns a compact reference table — ~500 chars vs ~15,000.

    The alert_guide explains WHY these numbers matter.
    This table gives the WHAT — exact values only.

    RAG NOTE (Version 2):
    This becomes the fallback when RAG retrieval returns
    nothing relevant. Always included as a baseline reference.
    """
    g = thresholds.get("glucose", {}).get("fasting", {})
    pm = thresholds.get("glucose", {}).get("post_meal", {})
    ex = thresholds.get("exercise", {})
    sl = thresholds.get("sleep", {})
    st = thresholds.get("stress", {})
    bp = thresholds.get("blood_pressure", {})
    ml = thresholds.get("missed_log", {})
    ss = thresholds.get("stress_sleep_combination", {})
    wt = thresholds.get("weight", {})
    nu_p = thresholds.get("nutrition", {}).get("protein", {})
    nu_c = thresholds.get("nutrition", {}).get("carbohydrates", {})

    return f"""
KEY CLINICAL THRESHOLDS (use patient's doctor-set targets when available):

GLUCOSE (FBS mg/dL):
  on_track < {g.get('on_track_max')} | low {g.get('low_min')}-{g.get('low_max')} | medium {g.get('medium_min')}-{g.get('medium_max')} | high > {g.get('high_threshold')}
  spike alert: rise > {g.get('sudden_spike_delta')} mg/dL from previous day
  post-meal: medium {pm.get('medium_min')}-{pm.get('medium_max')} | high > {pm.get('high_threshold')}

EXERCISE:
  target: {ex.get('daily_target')} min/day | missed: low={ex.get('missed_days_severity',{}).get('low')}day, medium={ex.get('missed_days_severity',{}).get('medium')}days, high={ex.get('missed_days_severity',{}).get('high')}days
  strength gap: medium after {thresholds.get('weight_training_gap',{}).get('medium_threshold')} cardio-only days

SLEEP:
  optimal {sl.get('optimal_min')}-{sl.get('optimal_max')}hrs | low < {sl.get('low_threshold')}hrs
  consecutive: medium={sl.get('consecutive_days_medium')}nights, high={sl.get('consecutive_days_high')}nights
  quality flags: "woke up multiple times" | "woke up tired"

STRESS (score 1-5):
  high >= {st.get('high_score_threshold')} | consecutive: medium={st.get('consecutive_days_medium')}days, high={st.get('consecutive_days_high')}days

STRESS + SLEEP COMBINED:
  medium={ss.get('consecutive_days_medium')}days both high | high={ss.get('consecutive_days_high')}days both high (LEADING INDICATOR)

BLOOD PRESSURE (mmHg):
  ADA diabetes threshold: {thresholds.get('blood_pressure',{}).get('ada_diabetes_threshold_systolic')}/{thresholds.get('blood_pressure',{}).get('ada_diabetes_threshold_diastolic')}
  high: systolic > {bp.get('systolic',{}).get('high_threshold')} or diastolic > {bp.get('diastolic',{}).get('high_threshold')}

MISSED LOG:
  low={ml.get('low')} | medium={ml.get('medium_consecutive')}consecutive | high={ml.get('high_consecutive')}consecutive

NUTRITION (% deviation from doctor-set target):
  protein: flag if > {nu_p.get('deviation_threshold_pct')}% below target for {nu_p.get('below_target_days_medium')}+ days
  carbs: flag if > {nu_c.get('deviation_threshold_pct')}% above target for {nu_c.get('above_target_days_medium')}+ days

WEIGHT: normal fluctuation ±{wt.get('normal_fluctuation_ignore')}kg | low gain {wt.get('low_gain_min')}-{wt.get('low_gain_max')}kg | medium {wt.get('medium_gain_min')}+ kg (7-day window)
""".strip()


# ── Format patient context ────────────────────────────────────
def format_patient_context(patient):
    """
    Converts patient dict into readable context for the user message.
    Includes full clinical context, structured data, and free text.
    """
    name = patient.get("name", "Unknown")
    history = patient.get("program_history", {})
    structured = patient.get("structured", {})
    unstructured = patient.get("unstructured", {})
    deviations = patient.get("deviations", [])

    # Comorbidities
    comorbidities = history.get("comorbidities", {})
    active_comorbidities = [
        k.replace("_", " ")
        for k, v in comorbidities.items()
        if v is True
    ]
    other_condition = comorbidities.get("other")
    if other_condition:
        active_comorbidities.append(other_condition)

    # Medications
    medications = history.get("medications", {})
    active_medications = [
        k.replace("_", " ")
        for k, v in medications.items()
        if v is True
    ]
    other_meds = medications.get("other")
    if other_meds:
        active_medications.append(other_meds)

    # Clinical targets
    targets = history.get("clinical_targets", {})
    fbs_target = targets.get("fbs_target_mgdl", 95)
    hypo_risk = targets.get("fbs_hypoglycemia_risk_mgdl", 80)
    conservative = targets.get("conservative_targets", False)

    # Baseline labs
    labs = history.get("baseline_labs", {})

    # Moods split into mood + cravings
    all_moods = structured.get("moods", [])
    craving_types = ["Craving Sweet", "Craving Salty", "Craving Crunchy"]
    mood_signals = [m for m in all_moods if m not in craving_types]
    craving_signals = [m for m in all_moods if m in craving_types]

    context = f"""
PATIENT: {name}
Age: {patient.get("age")} | Gender: {patient.get("gender")} | Week {history.get("week_number", "?")} of program

CLINICAL CONTEXT:
- Doctor-set FBS target: {fbs_target} mg/dL
- Hypoglycemia risk threshold: {hypo_risk} mg/dL
- Conservative targets: {"Yes" if conservative else "No"}
- Comorbidities: {", ".join(active_comorbidities) if active_comorbidities else "None reported"}
- Medications: {", ".join(active_medications) if active_medications else "None"}
- Baseline HbA1c: {labs.get("hba1c_pct", "not recorded")}%
- Baseline creatinine: {labs.get("creatinine", "not recorded")}

TODAY'S STRUCTURED DATA:
- FBS: {structured.get("fbs_mgdl", "not logged")} mg/dL (doctor target: {fbs_target})
- Post-meal glucose: {structured.get("postmeal_mgdl", "not logged")} mg/dL
- Exercise: {structured.get("exercise_minutes", "not logged")} min — {structured.get("exercise_type", "type not specified")}
- Exercise note: {structured.get("exercise_note", "none")}
- Weight: {structured.get("weight_kg", "not logged")} kg
- Sleep: {structured.get("sleep_hours", "not logged")} hrs — {structured.get("sleep_quality", "quality not logged")}
- Stress score: {structured.get("stress_score", "not logged")} / 5
- Blood pressure: {structured.get("blood_pressure_systolic", "not logged")}/{structured.get("blood_pressure_diastolic", "not logged")} mmHg
- Protein: {structured.get("protein_g", "not logged")}g (target: {history.get("protein_target_g", "not set")}g)
- Carbs: {structured.get("carbs_g", "not logged")}g (target: {history.get("carb_target_g", "not set")}g)
- Medication taken: {structured.get("medication_taken", "not logged")}
- Fasting day: {structured.get("fasting_day", False)}
- Mood signals: {", ".join(mood_signals) if mood_signals else "none"}
- Craving signals: {", ".join(craving_signals) if craving_signals else "none"}
- Symptoms selected: {", ".join(structured.get("symptoms", [])) if structured.get("symptoms") else "none"}

TODAY'S FREE TEXT:
- Food diary: {unstructured.get("food_diary", "not logged")}
- Patient notes: {unstructured.get("free_text", "not logged")}
- Coach notes: {unstructured.get("coach_notes", "not logged")}

DEVIATIONS FLAGGED BY RULES CHECK:
{chr(10).join(f"- {d}" for d in deviations) if deviations else "- None detected"}

PROGRAM CONTEXT:
- Started: {history.get("program_start_date", "unknown")}
- Initial FBS: {history.get("initial_fbs_mgdl", "unknown")} mg/dL
- Initial weight: {history.get("initial_weight_kg", "unknown")} kg
- Fasting protocol: {"Yes — " + str(history.get("fasting_expected_days_per_week", 0)) + " days/week" if history.get("fasting_protocol") else "No"}
- Strength training required: {"Yes" if history.get("strength_training_required") else "No"}
""".strip()
    return context


# ── Build system prompt ───────────────────────────────────────
def build_system_prompt(alert_guide, thresholds, guardrails, output_schema):
    """
    Assembles four protocol components into a lean system prompt.

    Token strategy:
    - Thresholds: compact reference table (~500 chars) not full YAML
    - Alert guide: full (clinical reasoning the LLM needs)
    - Guardrails: full (safety rules)
    - Output schema: full (JSON contract)
    - Clinic context: key notes only

    RAG NOTE (Version 2):
    build_system_prompt() becomes build_core_system_prompt() —
    containing only guardrails + schema + core instructions (~2K tokens).
    Alert guide sections are retrieved per patient from ChromaDB.
    Thresholds reference table stays as a compact constant.
    """
    clinic_context = thresholds.get("clinic_context", {})
    program_type = clinic_context.get("program_type", "diabetes reversal")
    population = clinic_context.get("population_description", "")
    dietary_context = clinic_context.get("dietary_context", "")
    interpretation_notes = clinic_context.get("interpretation_notes", [])
    notes_text = "\n".join(f"- {note.strip()}" for note in interpretation_notes)

    # Compact numbers table — not full YAML
    thresholds_table = extract_key_thresholds(thresholds)

    system_prompt = f"""You are MadhuMitra — a Clinical Protocol Intelligence Layer for a {program_type} program.
Your role: help health coaches triage their patient panel safely and efficiently.
Every output is a recommendation to the coach — not a clinical decision.

POPULATION: {population}
Dietary context: {dietary_context}

CLINIC INTERPRETATION NOTES:
{notes_text}

═══════════════════════════════
SECTION 1 — KEY THRESHOLDS
═══════════════════════════════
{thresholds_table}

═══════════════════════════════
SECTION 2 — REASONING GUIDE
═══════════════════════════════
{alert_guide}

═══════════════════════════════
SECTION 3 — GUARDRAILS
═══════════════════════════════
{guardrails}

═══════════════════════════════
SECTION 4 — OUTPUT SCHEMA
═══════════════════════════════
{output_schema}

═══════════════════════════════
THREE-STEP REASONING PROCESS
═══════════════════════════════
1. CROSS-SIGNAL DETECTION
   Review rules-check deviations. Examine free text, food diary,
   coach notes, symptoms. Look for combinations that amplify risk.

2. SENTIMENT DRIFT
   Assess emotional tone across mood signals and free text.
   Is the patient engaged or disengaging?

3. RISK TIER ASSIGNMENT
   Apply the patient's doctor-set clinical targets — not defaults.
   Consider comorbidities. Follow guardrails. Return valid JSON.
"""
    return system_prompt


# ── Build user message ────────────────────────────────────────
def build_user_message(patient_context):
    return f"""Analyse this patient and return the JSON assessment:

{patient_context}

Use doctor-set targets. Consider comorbidities. Cite specific data.
Return valid JSON only — no markdown, no extra text."""


# ── Entry point ───────────────────────────────────────────────
def build_prompt(patient, alert_guide, thresholds, guardrails, output_schema):
    """
    Builds (system_prompt, user_message) for one patient.
    Call this once per patient in the reasoning loop.
    """
    patient_context = format_patient_context(patient)
    system_prompt = build_system_prompt(
        alert_guide, thresholds, guardrails, output_schema
    )
    user_message = build_user_message(patient_context)
    return system_prompt, user_message
