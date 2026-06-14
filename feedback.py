"""
MadhuMitra — Feedback and Contact Tracking
------------------------------------------
Stores coach actions as labelled data points.
Every tap, contact, and correction is ground truth
for future calibration of the alert system.

Storage strategy (in priority order):
  1. Supabase (Postgres) — durable, survives Streamlit Cloud redeploys.
     Credentials read from st.secrets["SUPABASE_URL/KEY"]. Configured via
     the Supabase console + Streamlit Cloud secrets UI.
  2. Local JSON fallback — used automatically when Supabase is not
     configured (local dev, CI, or pre-Supabase deploys).
     contact_log.json / feedback_log.json

Phase 2: this data drives fine-tuning of alert ranking
and confidence thresholds per clinic.
"""

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path

import db as _db

CONTACT_LOG  = Path("contact_log.json")
FEEDBACK_LOG = Path("feedback_log.json")

COOLING_DAYS = {
    "High":   1,
    "Medium": 2,
    "Low":    3
}


# ── Load / save helpers ───────────────────────────────────────
def load_json(path):
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── Contact tracking ──────────────────────────────────────────
def mark_contacted(patient_name, severity, cooling_level, signals):
    """
    Records that a coach contacted a patient today.
    cooling_level: "High" (1 day) / "Medium" (2 days) / "Low" (3 days)
    """
    log = load_json(CONTACT_LOG)
    cooling_days = COOLING_DAYS.get(cooling_level, 2)

    log[patient_name] = {
        "contacted_date":    str(date.today()),
        "contacted_at":      datetime.now().isoformat(),
        "severity_at_contact": severity,
        "cooling_level":     cooling_level,
        "cooling_days":      cooling_days,
        "cooling_expires":   str(date.today() + timedelta(days=cooling_days)),
        "signals_at_contact": signals,
        "status":            "active"
    }
    save_json(CONTACT_LOG, log)
    return log[patient_name]


def extend_cooling(patient_name, extra_days):
    """Coach can extend the cooling period for a patient."""
    log = load_json(CONTACT_LOG)
    if patient_name in log:
        current_expiry = date.fromisoformat(log[patient_name]["cooling_expires"])
        new_expiry = current_expiry + timedelta(days=extra_days)
        log[patient_name]["cooling_expires"] = str(new_expiry)
        log[patient_name]["cooling_days"] += extra_days
        save_json(CONTACT_LOG, log)
    return log.get(patient_name)


def get_contact_status(patient_name):
    """
    Returns contact status for a patient.
    Returns None if never contacted or cooling expired.
    """
    log = load_json(CONTACT_LOG)
    if patient_name not in log:
        return None

    entry = log[patient_name]
    expiry = date.fromisoformat(entry["cooling_expires"])
    today  = date.today()

    if today > expiry:
        return None  # cooling period expired

    days_since = (today - date.fromisoformat(entry["contacted_date"])).days
    days_remaining = (expiry - today).days

    return {
        "contacted_date":      entry["contacted_date"],
        "severity_at_contact": entry["severity_at_contact"],
        "cooling_level":       entry["cooling_level"],
        "cooling_days":        entry["cooling_days"],
        "cooling_expires":     entry["cooling_expires"],
        "days_since_contact":  days_since,
        "days_remaining":      days_remaining,
        "signals_at_contact":  entry.get("signals_at_contact", [])
    }


def is_new_deviation(patient_name, current_signals, thresholds):
    """
    Checks if today's signals are NEW vs what was present at contact.
    New deviation = always alert regardless of cooling period.
    """
    status = get_contact_status(patient_name)
    if not status:
        return False  # not in cooling period

    previous_signals = set(status.get("signals_at_contact", []))
    current_signals_set = set(current_signals)

    # Check cooling period exceptions — always new
    exceptions = thresholds.get("follow_up", {}).get(
        "cooling_period_exceptions", []
    )
    for exception in exceptions:
        if exception in str(current_signals):
            return True

    # Check if any current signal is truly new
    new_signals = current_signals_set - previous_signals
    return len(new_signals) > 0


def should_alert(patient_name, current_signals, current_severity, thresholds):
    """
    Main routing decision for a patient in the system.
    Returns: "alert" | "followup" | "new_deviation_alert"
    """
    status = get_contact_status(patient_name)

    if not status:
        return "alert"  # not in cooling period — normal alert

    # Check for new deviation
    if is_new_deviation(patient_name, current_signals, thresholds):
        return "new_deviation_alert"

    # In cooling period, same deviation — follow-up tab
    return "followup"


# ── Feedback tracking (👍 / 👎) ───────────────────────────────
def record_feedback(patient_name, severity, track, signals,
                    reasoning, reaction, wrong_reason=None):
    """
    Records coach reaction to an alert.
    reaction: "correct" (👍) or "incorrect" (👎)
    wrong_reason: selected from dropdown if 👎

    Writes to Supabase (durable) and local JSON (fallback).
    reasoning is kept in the JSON log for local inspection but is NOT
    sent to Supabase (raw LLM text; excluded per privacy policy).
    """
    # ── Supabase (primary, durable) ──
    _db.save_feedback(
        patient_name=patient_name,
        severity=severity,
        track=track,
        signals=signals,
        reaction=reaction,
        wrong_reason=wrong_reason,
    )

    # ── Local JSON (fallback / local dev) ──
    log = load_json(FEEDBACK_LOG)
    entry_id = f"{patient_name}_{date.today()}"
    log[entry_id] = {
        "patient_name":   patient_name,
        "date":           str(date.today()),
        "timestamp":      datetime.now().isoformat(),
        "severity":       severity,
        "track":          track,
        "signals":        signals,
        "reasoning":      reasoning,
        "reaction":       reaction,
        "wrong_reason":   wrong_reason,
    }
    save_json(FEEDBACK_LOG, log)
    return log[entry_id]


def get_feedback_summary():
    """
    Returns summary stats for mentor/evaluation view.
    Prefers Supabase (durable across deploys); falls back to local JSON.
    """
    db_summary = _db.get_feedback_summary_db()
    if db_summary is not None:
        return db_summary

    # Local JSON fallback
    log = load_json(FEEDBACK_LOG)
    if not log:
        return {"total": 0, "correct": 0, "incorrect": 0, "precision": None}

    total     = len(log)
    correct   = sum(1 for e in log.values() if e["reaction"] == "correct")
    incorrect = total - correct
    precision = round(correct / total * 100, 1) if total > 0 else None

    wrong_reasons = {}
    for e in log.values():
        if e.get("wrong_reason"):
            r = e["wrong_reason"]
            wrong_reasons[r] = wrong_reasons.get(r, 0) + 1

    return {
        "total":         total,
        "correct":       correct,
        "incorrect":     incorrect,
        "precision":     precision,
        "wrong_reasons": wrong_reasons,
    }


def get_all_feedback():
    """Returns all feedback entries for export/display."""
    return load_json(FEEDBACK_LOG)


def get_all_contacts():
    """Returns all contact log entries."""
    return load_json(CONTACT_LOG)
