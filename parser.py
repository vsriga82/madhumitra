import json
import csv
import yaml
import pandas as pd
from pathlib import Path

# ── Load protocol thresholds ──────────────────────────────────
def load_thresholds():
    """
    Reads thresholds_v1.yaml and returns it as a Python dict.
    This is the single source of truth for all clinical values.
    """
    path = Path(__file__).parent / "protocol" / "thresholds_v1.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)
    
# ── Load patient data ─────────────────────────────────────────
def load_patients(filepath):
    """
    Accepts CSV or JSON patient data file.
    Returns a list of patient dicts in a standard format.
    """
    path = Path(filepath)

    if path.suffix == ".json":
        with open(path, "r") as f:
            data = json.load(f)
        return data["patients"]

    elif path.suffix == ".csv":
        patients = []
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                patients.append({
                    "name": row.get("name"),
                    "age": row.get("age"),
                    "gender": row.get("gender"),
                    "date": row.get("date"),
                    "structured": {
                        "fbs_mgdl": float(row["fbs_mgdl"]) if row.get("fbs_mgdl") else None,
                        "exercise_minutes": float(row["exercise_minutes"]) if row.get("exercise_minutes") else None,
                        "sleep_hours": float(row["sleep_hours"]) if row.get("sleep_hours") else None,
                        "stress_score": int(row["stress_score"]) if row.get("stress_score") else None,
                        "weight_kg": float(row["weight_kg"]) if row.get("weight_kg") else None,
                        "medication_taken": row.get("medication_taken", "").lower() == "true",
                        "protein_g": float(row["protein_g"]) if row.get("protein_g") else None,
                        "carbs_g": float(row["carbs_g"]) if row.get("carbs_g") else None,
                    },
                    "unstructured": {
                        "food_diary": row.get("food_diary"),
                        "free_text": row.get("free_text"),
                        "coach_notes": row.get("coach_notes"),
                    },
                    "program_history": {}
                })
        return patients

    else:
        raise ValueError(f"Unsupported file type: {path.suffix}. Use .json or .csv")
    
# ── Rules check ───────────────────────────────────────────────
def check_rules(patient, thresholds):
    """
    Compares patient's structured fields against thresholds.
    Returns a list of deviations found.
    No LLM involved — pure deterministic logic.
    """
    deviations = []
    s = patient.get("structured", {})
    history = patient.get("program_history", {})
    t = thresholds

    # ── Glucose ──────────────────────────────────────────────
    fbs = s.get("fbs_mgdl")
    if fbs is not None:
        high = t["glucose"]["fasting"]["high_threshold"]
        med_min = t["glucose"]["fasting"]["medium_min"]
        low_min = t["glucose"]["fasting"]["low_min"]

        if fbs > high:
            deviations.append(f"fbs_high: {fbs} mg/dL (threshold: {high})")
        elif fbs > med_min:
            deviations.append(f"fbs_medium: {fbs} mg/dL (threshold: {med_min})")
        elif fbs > low_min:
            deviations.append(f"fbs_low: {fbs} mg/dL (threshold: {low_min})")

    # ── Missed log ────────────────────────────────────────────
    if fbs is None and s.get("exercise_minutes") is None:
        deviations.append("missed_log: no structured data submitted today")

    # ── Exercise ──────────────────────────────────────────────
    exercise = s.get("exercise_minutes")
    if exercise is not None:
        target = t["exercise"]["daily_target"]
        if exercise < target:
            deviations.append(f"exercise_low: {exercise} min (target: {target})")

    # ── Sleep ─────────────────────────────────────────────────
    sleep = s.get("sleep_hours")
    if sleep is not None:
        low = t["sleep"]["low_threshold"]
        if sleep < low:
            deviations.append(f"sleep_low: {sleep} hrs (threshold: {low})")

    # ── Sleep quality ─────────────────────────────────────────
    sleep_quality = s.get("sleep_quality")
    if sleep_quality in ["woke up multiple times", "woke up tired"]:
        deviations.append(f"sleep_quality_poor: {sleep_quality}")

    # ── Stress ────────────────────────────────────────────────
    stress = s.get("stress_score")
    if stress is not None:
        high_stress = t["stress"]["high_score_threshold"]
        if stress >= high_stress:
            deviations.append(f"stress_high: score {stress} (threshold: {high_stress})")

    # ── Medication ────────────────────────────────────────────
    medication = s.get("medication_taken")
    if medication is False:
        deviations.append("medication_missed")

    # ── Tier 1 symptoms — always High ─────────────────────────
    symptoms = s.get("symptoms", [])
    tier1 = t["symptom_classification"]["tier_1_always_high"]["symptoms"]
    for symptom in symptoms:
        if symptom.lower() in [s.lower() for s in tier1]:
            deviations.append(f"tier1_symptom: {symptom}")

    # ── Tier 2 symptoms — Medium amplifier ────────────────────
    tier2 = t["symptom_classification"]["tier_2_medium_amplifier"]["symptoms"]
    for symptom in symptoms:
        if symptom.lower() in [s.lower() for s in tier2]:
            deviations.append(f"tier2_symptom: {symptom}")

    # ── Blood pressure ────────────────────────────────────────
    systolic = s.get("blood_pressure_systolic")
    diastolic = s.get("blood_pressure_diastolic")
    if systolic is not None:
        if systolic > t["blood_pressure"]["systolic"]["high_threshold"]:
            deviations.append(f"bp_high: {systolic}/{diastolic} mmHg")
        elif systolic > t["blood_pressure"]["ada_diabetes_threshold_systolic"]:
            deviations.append(f"bp_above_ada: {systolic}/{diastolic} mmHg")

    # ── Nutrition — protein ───────────────────────────────────
    protein = s.get("protein_g")
    protein_target = history.get("protein_target_g")
    if protein is not None and protein_target is not None:
        threshold_pct = t["nutrition"]["protein"]["deviation_threshold_pct"]
        min_acceptable = protein_target * (1 - threshold_pct / 100)
        if protein < min_acceptable:
            deviations.append(f"protein_low: {protein}g (target: {protein_target}g)")

    # ── Nutrition — carbs ─────────────────────────────────────
    carbs = s.get("carbs_g")
    carb_target = history.get("carb_target_g")
    if carbs is not None and carb_target is not None:
        threshold_pct = t["nutrition"]["carbohydrates"]["deviation_threshold_pct"]
        max_acceptable = carb_target * (1 + threshold_pct / 100)
        if carbs > max_acceptable:
            deviations.append(f"carbs_high: {carbs}g (target: {carb_target}g)")

    # ── Mood — negative ───────────────────────────────────────
    moods = s.get("moods", [])
    negative_moods = t["mood_classification"]["negative_moods"]
    found_negative = [m for m in moods if m in negative_moods]
    if found_negative:
        deviations.append(f"negative_mood: {', '.join(found_negative)}")

    # ── Cravings ──────────────────────────────────────────────
    craving_types = t["mood_classification"]["craving_signals"]
    found_cravings = [m for m in moods if m in craving_types]
    if len(found_cravings) >= 2:
        deviations.append(f"multiple_cravings: {', '.join(found_cravings)}")
    elif len(found_cravings) == 1:
        deviations.append(f"craving: {found_cravings[0]}")

    return deviations

# ── Generate alert from rules (no LLM needed) ─────────────────
def generate_rules_alert(patient, deviations, thresholds):
    """
    For clear-cut High cases caught by rules check.
    Generates the alert the same way the LLM would —
    but deterministically. No API call needed.
    """
    t = thresholds
    s = patient.get("structured", {})
    name = patient.get("name")

    # Check for Tier 1 symptoms
    tier1_found = [d for d in deviations if d.startswith("tier1_symptom")]
    medication_missed = "medication_missed" in deviations
    fbs_high = [d for d in deviations if d.startswith("fbs_high")]
    missed_log = [d for d in deviations if d.startswith("missed_log")]

    # Build reasoning trace from actual data
    reasons = []
    if tier1_found:
        symptoms = [d.split(": ")[1] for d in tier1_found]
        reasons.append(f"Tier 1 symptom(s) detected: {', '.join(symptoms)}")
    if fbs_high:
        reasons.append(fbs_high[0].replace("fbs_high: ", "FBS "))
    if medication_missed:
        reasons.append("Medication missed today")
    if missed_log:
        reasons.append("No log submitted — third consecutive missed log")

    reasoning = " — ".join(reasons) + ". Same-day coach contact required."

    # Calculate priority score from thresholds
    score = 0
    ps = t["priority_scoring"]

    if tier1_found:
        symptoms_list = [d.split(": ")[1] for d in tier1_found]
        for sym in symptoms_list:
            sym_lower = sym.lower()
            if "chest" in sym_lower:
                score += ps["symptoms"]["chest_pain"]
            elif "foamy" in sym_lower:
                score += ps["symptoms"]["foamy_urine"]
            elif "blurry" in sym_lower or "vision" in sym_lower:
                score += ps["symptoms"]["blurry_vision"]
            elif "numb" in sym_lower or "tingling" in sym_lower:
                score += ps["symptoms"]["numbness_tingling"]
            elif "dizzy" in sym_lower or "dizziness" in sym_lower:
                score += ps["symptoms"]["persistent_dizziness"]
            elif "swelling" in sym_lower:
                score += ps["symptoms"]["foamy_urine"]  # same weight

    if medication_missed and fbs_high:
        score += ps["medication"]["missed_with_high_glucose"]
    elif medication_missed:
        score += ps["medication"]["missed_alone"]

    # Add per-signal score
    score += len(deviations) * ps["per_additional_signal"]

    return {
        "name": name,
        "severity": "High",
        "confidence": "high",
        "source": "rules",        # came from rules check, not LLM
        "reasoning": reasoning,
        "priority_score": score,
        "deviations": deviations,
        "has_tier1_symptom": len(tier1_found) > 0,
        "medication_missed": medication_missed,
        "consecutive_days": 1,
        "send_to_llm": False,
        "track": "auto"
    }

# ── Is patient on track? ──────────────────────────────────────
def is_on_track(deviations):
    """
    Returns True if no deviations found.
    On-track patients skip the LLM entirely.
    """
    return len(deviations) == 0


# ── Parse single patient ──────────────────────────────────────
def parse_patient(patient, thresholds):
    """
    Main function — runs one patient through the full parser.
    Returns a standardised dict ready for the reasoning loop.
    """
    name = patient.get("name", "Unknown")
    deviations = check_rules(patient, thresholds)

    # On track — skip LLM
    if is_on_track(deviations):
        return {
            "name": name,
            "severity": "On Track",
            "confidence": "high",
            "source": "rules",
            "reasoning": "No deviations detected across all signals.",
            "priority_score": 0,
            "deviations": [],
            "has_tier1_symptom": False,
            "medication_missed": False,
            "consecutive_days": 0,
            "send_to_llm": False,
            "track": "on_track",
            "structured": patient.get("structured", {}),
            "unstructured": patient.get("unstructured", {}),
            "program_history": patient.get("program_history", {})
        }

    # Check for Bucket 1 — clear High cases
    tier1_symptoms = [d for d in deviations if d.startswith("tier1_symptom")]
    is_bucket1 = len(tier1_symptoms) > 0

    if is_bucket1:
        result = generate_rules_alert(patient, deviations, thresholds)
        result["structured"] = patient.get("structured", {})
        result["unstructured"] = patient.get("unstructured", {})
        result["program_history"] = patient.get("program_history", {})
        return result

    # Bucket 2 and 3 — send to LLM
    return {
        "name": name,
        "severity": None,           # LLM will determine this
        "confidence": None,         # LLM will determine this
        "source": "llm",
        "reasoning": None,          # LLM will generate this
        "priority_score": None,     # ranker will calculate this
        "deviations": deviations,
        "has_tier1_symptom": False,
        "medication_missed": "medication_missed" in deviations,
        "consecutive_days": 1,
        "send_to_llm": True,        # flag for reasoning.py
        "track": None,              # LLM will determine this
        "structured": patient.get("structured", {}),
        "unstructured": patient.get("unstructured", {}),
        "program_history": patient.get("program_history", {})
    }


# ── Parse all patients ────────────────────────────────────────
def parse_all(filepath):
    """
    Entry point — loads patients, runs parser on all of them.
    Returns three lists: flagged, rules_alerted, on_track.
    """
    thresholds = load_thresholds()
    patients = load_patients(filepath)

    on_track = []
    rules_alerted = []    # Bucket 1 — parser handled
    send_to_llm = []      # Bucket 2 + 3 — LLM needed

    for patient in patients:
        result = parse_patient(patient, thresholds)

        if result["track"] == "on_track":
            on_track.append(result)
        elif result["send_to_llm"] is False and result["track"] == "auto":
            rules_alerted.append(result)
        else:
            send_to_llm.append(result)

    return {
        "on_track": on_track,
        "rules_alerted": rules_alerted,
        "send_to_llm": send_to_llm
    }