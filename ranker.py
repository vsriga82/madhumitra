from parser import load_thresholds


def calculate_score(patient_result, thresholds):
    """
    Calculates priority score for a patient result.
    Works for both rules-alerted and LLM-analysed patients.
    """
    # If parser already calculated score, use it
    if patient_result.get("priority_score") is not None:
        return patient_result["priority_score"]

    ps = thresholds.get("priority_scoring", {})
    score = 0
    signals = patient_result.get("signals", [])
    signal_text = " ".join(signals).lower()

    # Symptom weights
    symptom_weights = ps.get("symptoms", {})
    if "chest" in signal_text:
        score += symptom_weights.get("chest_pain", 50)
    if "foamy" in signal_text:
        score += symptom_weights.get("foamy_urine", 40)
    if "blurry" in signal_text or "vision" in signal_text:
        score += symptom_weights.get("blurry_vision", 40)
    if "numb" in signal_text or "tingling" in signal_text:
        score += symptom_weights.get("numbness_tingling", 35)
    if "dizzy" in signal_text or "dizziness" in signal_text:
        score += symptom_weights.get("persistent_dizziness", 30)
    if "swelling" in signal_text:
        score += symptom_weights.get("foamy_urine", 40)

    # Medication
    med_weights = ps.get("medication", {})
    if patient_result.get("medication_missed"):
        severity = patient_result.get("severity", "")
        if severity in ["High", "Medium"]:
            score += med_weights.get("missed_with_high_glucose", 25)
        else:
            score += med_weights.get("missed_alone", 15)

    # Consecutive days
    days = patient_result.get("consecutive_days", 1)
    weight_per_day = ps.get("consecutive_days", {}).get("weight_per_day", 8)
    max_days = ps.get("consecutive_days", {}).get("max_days_counted", 7)
    score += min(days, max_days) * weight_per_day

    # Glucose trend
    trend_weights = ps.get("glucose_trend", {})
    trend = patient_result.get("glucose_trend", "unknown")
    if trend == "rising":
        score += trend_weights.get("rising", 15)
    elif trend == "improving":
        score += trend_weights.get("improving", -10)

    # Per additional signal
    per_signal = ps.get("per_additional_signal", 5)
    score += len(signals) * per_signal

    # Escalation bonus
    if patient_result.get("escalate_to_doctor"):
        score += 30

    # BP
    bp_weights = ps.get("blood_pressure", {})
    signal_str = " ".join(signals)
    if "above high threshold" in signal_str.lower():
        score += bp_weights.get("stage_2_hypertension", 35)
    elif "above ada" in signal_str.lower():
        score += bp_weights.get("above_ada_threshold", 20)

    return score


def tiebreak_score(patient_result):
    """Secondary sort when priority scores are equal."""
    has_tier1 = 1 if patient_result.get("has_tier1_symptom") else 0
    days = patient_result.get("consecutive_days", 0)
    missed_med = 1 if patient_result.get("medication_missed") else 0
    escalate = 1 if patient_result.get("escalate_to_doctor") else 0
    return (escalate, has_tier1, days, missed_med)


def rank_results(rules_alerted, llm_results, on_track, thresholds):
    """
    Combines all three buckets and produces the final ranked list.
    Returns: auto_list, queue_list, nudge_list, on_track_list
    """
    # Combine rules-alerted and LLM results
    all_alerts = rules_alerted + llm_results

    # Calculate scores for LLM results
    for p in all_alerts:
        if p.get("priority_score") is None:
            p["priority_score"] = calculate_score(p, thresholds)

    # Separate by track
    auto_list  = [p for p in all_alerts if p.get("track") == "auto"]
    queue_list = [p for p in all_alerts if p.get("track") == "queue"]
    nudge_list = [p for p in all_alerts if p.get("nudge_risk") is True]

    # Sort each tier by severity then score
    severity_order = {"High": 0, "Medium": 1, "Low": 2, "On Track": 3, "Unknown": 4}

    def sort_key(p):
        severity_rank = severity_order.get(p.get("severity", "Unknown"), 4)
        score = -(p.get("priority_score") or 0)
        tiebreak = tuple(-x for x in tiebreak_score(p))
        return (severity_rank, score) + tiebreak

    auto_list  = sorted(auto_list, key=sort_key)
    queue_list = sorted(queue_list, key=sort_key)

    return auto_list, queue_list, nudge_list, on_track


def run_ranker(parse_results, llm_results, thresholds):
    """
    Entry point — takes parse_all() output and LLM results.
    Returns final ranked lists ready for the UI.
    """
    auto_list, queue_list, nudge_list, on_track = rank_results(
        parse_results["rules_alerted"],
        llm_results,
        parse_results["on_track"],
        thresholds
    )

    return {
        "auto_list":  auto_list,
        "queue_list": queue_list,
        "nudge_list": nudge_list,
        "on_track":   parse_results["on_track"],
        "summary": {
            "total":     len(auto_list) + len(queue_list) + len(parse_results["on_track"]),
            "high":      len([p for p in auto_list if p.get("severity") == "High"]),
            "medium":    len([p for p in auto_list if p.get("severity") == "Medium"]),
            "low":       len([p for p in auto_list if p.get("severity") == "Low"]),
            "queue":     len(queue_list),
            "on_track":  len(parse_results["on_track"]),
            "escalate":  len([p for p in auto_list + queue_list if p.get("escalate_to_doctor")])
        }
    }
