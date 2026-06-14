"""
db.py — Supabase persistence layer for MadhuMitra

Credentials are read from st.secrets (Streamlit Cloud) or environment
variables (local dev). Never hardcoded.

All functions degrade gracefully: if Supabase is not configured they return
None/False and the caller falls back to local JSON storage.

Privacy rules enforced here:
  - patient_token() hashes the name — raw names never leave this module
  - signal_set stores clinical labels only (no raw patient free-text)
  - reasoning text is intentionally excluded from every insert
"""

import hashlib
from datetime import date
from typing import Optional


# ── Client ────────────────────────────────────────────────────────────────────

def _client():
    """
    Lazy-initialise the Supabase client on each call.
    Returns None silently if credentials are missing (local dev without Supabase).

    Uses SUPABASE_SERVICE_KEY (not the anon key) because:
    - Streamlit runs server-side; the key never reaches a user's browser.
    - RLS is enabled on all tables; the service role bypasses it, so no
      per-row policies are needed until multi-clinic auth is added.
    - The anon key would be blocked by RLS with no policies defined.
    """
    try:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_KEY"]
    except Exception:
        try:
            import os
            url = os.environ["SUPABASE_URL"]
            key = os.environ["SUPABASE_SERVICE_KEY"]
        except KeyError:
            return None

    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


# ── Privacy helper ────────────────────────────────────────────────────────────

def patient_token(name: str) -> str:
    """One-way token derived from patient name. Never store the raw name."""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]


# ── triage_runs ───────────────────────────────────────────────────────────────

def save_triage_run(summary: dict, data_date: Optional[date] = None) -> Optional[str]:
    """
    Insert one triage_run row and return its UUID.
    summary dict shape mirrors run_ranker()'s return value['summary'].
    Returns None if Supabase is not configured or the insert fails.
    """
    db = _client()
    if not db:
        return None

    row = {
        "data_date":      str(data_date or date.today()),
        "patient_count":  summary.get("total", 0),
        "high_count":     summary.get("high", 0),
        "medium_count":   summary.get("medium", 0),
        "low_count":      summary.get("low", 0),
        "queue_count":    summary.get("queue", 0),
        "on_track_count": summary.get("on_track", 0),
        "data_source":    "sample",
    }
    try:
        resp = db.table("triage_runs").insert(row).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception:
        return None


# ── alerts ────────────────────────────────────────────────────────────────────

def save_alert(run_id: str, patient_name: str, result: dict) -> Optional[str]:
    """
    Insert one alert row and return its UUID.
    result dict is the per-patient output from ranker / rules engine.

    Note: reasoning text is intentionally NOT stored (raw LLM free text).
    signal_set stores clinical label strings only.
    """
    db = _client()
    if not db or not run_id:
        return None

    signals = result.get("signals") or [
        d.replace("_", " ") for d in result.get("deviations", [])
    ]

    row = {
        "run_id":              run_id,
        "patient_token":       patient_token(patient_name),
        "severity":            result.get("severity"),
        "track":               result.get("track"),
        "confidence":          result.get("confidence"),
        "source":              result.get("source"),
        "signal_set":          signals,
        "priority_score":      result.get("priority_score"),
        "escalate_to_doctor":  bool(result.get("escalate_to_doctor", False)),
        "has_tier1_symptom":   bool(result.get("has_tier1_symptom", False)),
        "medication_missed":   bool(result.get("medication_missed", False)),
        "glucose_trend":       result.get("glucose_trend"),
        "verified":            bool(result.get("verified", False)),
    }
    try:
        resp = db.table("alerts").insert(row).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception:
        return None


def save_all_alerts(run_id: str, final: dict) -> dict:
    """
    Persist every patient from all four buckets in a single call.
    Returns {patient_token: alert_uuid} mapping for feedback FK lookups.
    """
    token_to_id: dict = {}
    if not run_id:
        return token_to_id

    all_patients = (
        final.get("auto_list", [])
        + final.get("queue_list", [])
        + final.get("nudge_list", [])
        + final.get("on_track", [])
    )
    for p in all_patients:
        name = p.get("name", "")
        if name:
            alert_id = save_alert(run_id, name, p)
            if alert_id:
                token_to_id[patient_token(name)] = alert_id

    return token_to_id


# ── coach_feedback ────────────────────────────────────────────────────────────

def _latest_alert_id(db, tok: str) -> Optional[str]:
    """Look up the most recent alert UUID for a patient token."""
    try:
        resp = (
            db.table("alerts")
            .select("id")
            .eq("patient_token", tok)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0]["id"] if resp.data else None
    except Exception:
        return None


def save_feedback(
    patient_name: str,
    severity: str,
    track: str,
    signals: list,
    reaction: str,
    wrong_reason: Optional[str] = None,
) -> bool:
    """
    Insert one coach_feedback row.
    Tries to populate alert_id FK from the most recent matching alert;
    leaves it NULL if not found (feedback is still stored and queryable).

    Note: reasoning text is intentionally excluded — signal_set is enough
    for eval ground-truth calibration.
    """
    db = _client()
    if not db:
        return False

    tok = patient_token(patient_name)
    alert_id = _latest_alert_id(db, tok)

    row = {
        "alert_id":      alert_id,       # nullable — best-effort FK
        "patient_token": tok,
        "feedback_date": str(date.today()),
        "severity":      severity,
        "track":         track or "auto",
        "signal_set":    signals or [],
        "reaction":      reaction,
        "wrong_reason":  wrong_reason,
    }
    try:
        db.table("coach_feedback").insert(row).execute()
        return True
    except Exception:
        return False


# ── Feedback summary (for sidebar precision tracker) ──────────────────────────

def get_feedback_summary_db() -> Optional[dict]:
    """
    Pull precision stats from Supabase.
    Returns None if Supabase is not configured (caller uses JSON fallback).
    """
    db = _client()
    if not db:
        return None

    try:
        resp = db.table("coach_feedback").select("reaction, wrong_reason").execute()
        rows = resp.data or []
    except Exception:
        return None

    total = len(rows)
    if not total:
        return {"total": 0, "correct": 0, "incorrect": 0,
                "precision": None, "wrong_reasons": {}}

    correct = sum(1 for r in rows if r["reaction"] == "correct")
    wrong_reasons: dict = {}
    for r in rows:
        if r.get("wrong_reason"):
            wr = r["wrong_reason"]
            wrong_reasons[wr] = wrong_reasons.get(wr, 0) + 1

    return {
        "total":         total,
        "correct":       correct,
        "incorrect":     total - correct,
        "precision":     round(correct / total * 100, 1),
        "wrong_reasons": wrong_reasons,
    }
