"""
run_eval.py — MadhuMitra evaluation runner
===========================================

WHAT THIS DOES (and why it exists)
----------------------------------
You built a test harness (the Google Sheet: 20 cases, each with a ground-truth
tier). But nothing in the codebase actually ran your pipeline and *scored* its
output against that ground truth — "running the eval" was always a manual,
eyeball-against-the-sheet activity. This script closes that gap.

It runs your REAL pipeline (parser -> reasoning -> ranker), exactly the way
app.py does, then for each of the 8 sample patients it compares the tier the
system produced against the tier your eval sheet says is correct, and prints:

  1. A per-patient PASS/FAIL table (with the system's reasoning on any miss)
  2. High-risk recall   -- the non-negotiable safety number (must be 100%)
  3. Alert precision     -- of patients flagged High, how many truly were High
  4. Exact-tier accuracy -- did every patient land on the exact right tier

HOW TO RUN (on your Mac, in the Madumitra folder)
--------------------------------------------------
    source venv/bin/activate
    python run_eval.py              # full run (spends OpenAI tokens, like app.py)
    python run_eval.py --dry-run    # parser/bucketing only, NO LLM call, $0

NOTE ON TIER VOCABULARY
-----------------------
Your pipeline routes a patient into one of four output buckets (from run_ranker):
    auto_list   -> tier is the patient's severity: High / Medium / Low
    queue_list  -> "Manual Queue"
    nudge_list  -> "Nudge"
    on_track    -> "On Track"
The EXPECTED tiers below use that same vocabulary so the comparison is apples-to-apples.
"""

import sys
import csv
import json
import asyncio
import argparse

from parser import parse_all, load_patients, load_thresholds
from prompt import load_protocol_files
from reasoning import run_reasoning, ENABLE_VERIFICATION, client
from ranker import run_ranker


# ─────────────────────────────────────────────────────────────────────────────
# GROUND TRUTH — the canonical expected tier per patient.
# Sourced from your eval sheet (Eval Cases) + HANDOFF "Sample Patients" table.
# Edit here if you change a patient's designed behaviour.
#
# NOTE on Anita Rao: eval sheet TC-07 says "Manual Queue"; TC-16's tier column
# says "On Track" while its text says "Manual Queue". We treat TC-07 as canonical
# (low-confidence borderline -> manual queue). Change to "On Track" if you decide
# her positive signals should fully clear her.
# ─────────────────────────────────────────────────────────────────────────────
EXPECTED = {
    "Priya Sharma":   "High",          # glucose + dizziness + wedding + 3-day mood decline
    "Suresh Nair":    "High",          # foamy urine + dizziness (Tier 1) + CKD -> escalate
    "Meena Patel":    "Medium",        # wk4 silence w/ good HbA1c, no symptoms — wait ~2d before High (program-week-aware)
    "Deepak Verma":   "High",          # max complexity: BP + stress 5/5 + missed meds
    "Fatima Sheikh":  "Medium",        # social event + apology tone -> Medium, not High
    "Anita Rao":      "Manual Queue",  # borderline FBS, no weights yet, ambiguous
    "Rajan Kumar":    "Nudge",         # plateau + shortening logs (disengagement, not clinical)
    "Karthik Iyer":   "On Track",      # all signals green (true negative)
    "Arjun Sharma":   "Medium",        # rising FBS trend + exercise drop, no acute symptoms (Watch)
    "Lakshmi Menon":  "Nudge",         # second slippage case: plateau + disengaging logs
}

# Which expected tiers count as "high-risk" for the recall metric (the safety number).
HIGH_RISK_TIERS = {"High"}

DATA_FILE = "data/sample_patients.json"


def effective_tier(name, final):
    """Map a patient name to the single tier the system actually produced,
    by finding which output bucket they landed in."""
    def names(bucket):
        return {p.get("name"): p for p in final.get(bucket, [])}

    auto  = names("auto_list")
    queue = names("queue_list")
    nudge = names("nudge_list")
    ontr  = names("on_track")

    if name in auto:
        return auto[name].get("severity", "Unknown"), auto[name]
    if name in queue:
        return "Manual Queue", queue[name]
    if name in nudge:
        return "Nudge", nudge[name]
    if name in ontr:
        return "On Track", ontr[name]
    return "MISSING", None


def norm(t):
    return (t or "").strip().lower()


def run_pipeline(dry_run=False):
    """Mirror of app.py's wiring."""
    alert_guide, thresholds, guardrails, output_schema = load_protocol_files()
    thresholds_data = load_thresholds()
    parse_results = parse_all(DATA_FILE)

    if dry_run:
        print("DRY RUN — parser/bucketing only, no LLM call.\n")
        print(f"  on_track     : {[p['name'] for p in parse_results['on_track']]}")
        print(f"  rules_alerted: {[p['name'] for p in parse_results['rules_alerted']]}")
        print(f"  send_to_llm  : {[p['name'] for p in parse_results['send_to_llm']]}")
        return None

    llm_results = run_reasoning(
        parse_results["send_to_llm"],
        alert_guide, thresholds, guardrails, output_schema
    )
    final = run_ranker(parse_results, llm_results, thresholds_data)
    return final


def score(final):
    rows = []
    tp = fp = 0                      # for precision (system-High that is / isn't truly High)
    high_risk_total = high_risk_caught = 0
    exact_matches = 0

    for name, expected in EXPECTED.items():
        actual, result = effective_tier(name, final)
        match = norm(actual) == norm(expected)
        if match:
            exact_matches += 1

        # High-risk recall bookkeeping
        if expected in HIGH_RISK_TIERS:
            high_risk_total += 1
            if actual in HIGH_RISK_TIERS:
                high_risk_caught += 1

        # Precision bookkeeping (system said High)
        if actual in HIGH_RISK_TIERS:
            if expected in HIGH_RISK_TIERS:
                tp += 1
            else:
                fp += 1

        reasoning = (result or {}).get("reasoning", "") if result else ""
        rows.append((name, expected, actual, match, reasoning))

    # ── Print per-patient table ──
    print("=" * 78)
    print(f"{'PATIENT':<16}{'EXPECTED':<16}{'ACTUAL':<16}{'RESULT':<8}")
    print("-" * 78)
    for name, expected, actual, match, reasoning in rows:
        flag = "PASS" if match else "FAIL"
        print(f"{name:<16}{expected:<16}{actual:<16}{flag:<8}")
        if not match and reasoning:
            print(f"    ↳ system reasoning: {reasoning[:90]}")
    print("=" * 78)

    # ── Metrics ──
    n = len(EXPECTED)
    recall = (high_risk_caught / high_risk_total * 100) if high_risk_total else 0.0
    precision = (tp / (tp + fp) * 100) if (tp + fp) else 0.0
    accuracy = exact_matches / n * 100

    print(f"\nVerification mode : {'ON' if ENABLE_VERIFICATION else 'OFF (MVP baseline)'}")
    print(f"Exact-tier accuracy : {exact_matches}/{n}  ({accuracy:.0f}%)")
    print(f"Alert precision     : {precision:.0f}%   (of {tp+fp} flagged High, {tp} truly High)")
    print(f"High-risk recall    : {recall:.0f}%   ({high_risk_caught}/{high_risk_total} high-risk caught)"
          f"   {'✅ SAFE' if recall == 100 else '🚨 MISS — non-negotiable failure'}")
    print()
    if recall < 100:
        missed = [n for n, e, a, m, _ in rows if e in HIGH_RISK_TIERS and a not in HIGH_RISK_TIERS]
        print(f"⚠️  High-risk patients NOT surfaced as High: {missed}")
        print("    This is the one metric that must be 100% even at the earliest stage.\n")

    # ── Write results to CSV (open in Excel / Google Sheets to review & mark) ──
    out_path = "eval_results.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Patient", "Expected", "Actual", "Result", "System Reasoning"])
        for name, expected, actual, match, reasoning in rows:
            w.writerow([name, expected, actual,
                        "PASS" if match else "FAIL", reasoning])
    print(f"📄 Results written to {out_path} — open it in Excel/Sheets to review.\n")


# ─────────────────────────────────────────────────────────────────────────────
# NAKED MODE — bare Claude baseline, zero scaffolding
#
# Ground truth remapping: "Nudge" and "Manual Queue" are protocol-specific
# routing categories that don't exist in a bare LLM world. For fair scoring
# we remap them to their closest tier equivalents before comparing:
#   Nudge        → Low    (behavioral, not clinical — lowest-priority action)
#   Manual Queue → Medium (borderline confidence — mid-tier attention)
# The remapping is printed in the output so the slide is transparent.
# ─────────────────────────────────────────────────────────────────────────────
NAKED_REMAP = {"Nudge": "Low", "Manual Queue": "Medium"}

NAKED_VALID = {"High", "Medium", "Low", "On Track"}


def _format_patient_for_naked(patient):
    """Render full patient data as readable plain text for the bare-LLM prompt."""
    s  = patient.get("structured", {}) or {}
    u  = patient.get("unstructured", {}) or {}
    ph = patient.get("program_history", {}) or {}
    comorbidities = [k.replace("_", " ")
                     for k, v in ph.get("comorbidities", {}).items() if v]
    meds_on = [k.replace("_", " ")
               for k, v in ph.get("medications", {}).items() if v]

    def val(v, unit=""):
        return f"{v}{unit}" if v is not None else "not logged"

    bp_sys = s.get("blood_pressure_systolic")
    bp_dia = s.get("blood_pressure_diastolic")
    bp_str = f"{bp_sys}/{bp_dia} mmHg" if bp_sys else "not logged"

    lines = [
        f"Patient: {patient.get('name')}, Age {patient.get('age')}, {patient.get('gender')}",
        f"Week in program: {ph.get('week_number', 'unknown')}",
        f"Initial FBS at enrolment: {val(ph.get('initial_fbs_mgdl'), ' mg/dL')}",
        f"Comorbidities: {', '.join(comorbidities) or 'none'}",
        f"Current medications: {', '.join(meds_on) or 'none'}",
        "",
        "Today's log:",
        f"  Fasting blood sugar : {val(s.get('fbs_mgdl'), ' mg/dL')}",
        f"  Blood pressure      : {bp_str}",
        f"  Exercise            : {val(s.get('exercise_minutes'), ' min')} ({s.get('exercise_type') or '—'})",
        f"  Sleep               : {val(s.get('sleep_hours'), ' hrs')} — {s.get('sleep_quality') or '—'}",
        f"  Stress (1–5)        : {val(s.get('stress_score'))}",
        f"  Weight              : {val(s.get('weight_kg'), ' kg')}",
        f"  Medication taken    : {val(s.get('medication_taken'))}",
        f"  Protein / Carbs     : {val(s.get('protein_g'), 'g')} / {val(s.get('carbs_g'), 'g')}",
        f"  Symptoms reported   : {', '.join(s.get('symptoms', [])) or 'none'}",
        f"  Moods               : {', '.join(s.get('moods', [])) or 'none'}",
        "",
        "Patient's own words:",
        f"  Food diary   : {u.get('food_diary') or 'not provided'}",
        f"  Free text    : {u.get('free_text') or 'not provided'}",
        "",
        "Coach's observation notes:",
        f"  {u.get('coach_notes') or 'not provided'}",
    ]
    return "\n".join(lines)


async def _naked_classify_one(patient, semaphore):
    """Single bare-Claude call — no protocol, no schema, just a tier label."""
    system = (
        "You are a clinical coach at a diabetes reversal program. "
        "Review the patient data and classify their current status as exactly one of:\n"
        "  High     — requires same-day coach contact; possible clinical escalation needed\n"
        "  Medium   — needs coach attention within 24 hours\n"
        "  Low      — routine follow-up at next scheduled check-in\n"
        "  On Track — patient is progressing well, no action needed\n\n"
        "Reply with ONLY the single tier label. Nothing else — no explanation, no punctuation."
    )
    user = _format_patient_for_naked(patient)
    name = patient.get("name", "Unknown")

    async with semaphore:
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=10
            )
            raw = (response.content[0].text if response.content else "").strip()
            # Normalise casing, strip stray punctuation
            for tier in NAKED_VALID:
                if raw.lower() == tier.lower():
                    print(f"  ✓ {name}: {tier}")
                    return name, tier
            # Fallback if model ignored instructions
            print(f"  ? {name}: unrecognised response '{raw}' — defaulting Medium")
            return name, "Medium"
        except Exception as e:
            print(f"  ✗ {name}: call failed ({e}) — defaulting Medium")
            return name, "Medium"


async def _naked_classify_all(patients):
    semaphore = asyncio.Semaphore(2)
    tasks = [_naked_classify_one(p, semaphore) for p in patients]
    return dict(await asyncio.gather(*tasks))


def run_naked_pipeline():
    """Load all patients (no rules filter), classify each with bare Claude."""
    patients = load_patients(DATA_FILE)
    print(f"\nNAKED LLM — sending all {len(patients)} patients (no rules pre-filter)...\n")
    return asyncio.run(_naked_classify_all(patients))


def score_naked(name_to_tier):
    """Score the naked results against ground truth, with protocol-concept remapping."""
    rows = []
    tp = fp = 0
    high_risk_total = high_risk_caught = 0
    exact_matches = 0

    for name, expected_raw in EXPECTED.items():
        expected = NAKED_REMAP.get(expected_raw, expected_raw)  # remap Nudge/Manual Queue
        actual   = name_to_tier.get(name, "MISSING")
        match    = actual.lower() == expected.lower()
        if match:
            exact_matches += 1

        if expected_raw in HIGH_RISK_TIERS:
            high_risk_total += 1
            if actual in HIGH_RISK_TIERS:
                high_risk_caught += 1

        if actual in HIGH_RISK_TIERS:
            if expected_raw in HIGH_RISK_TIERS:
                tp += 1
            else:
                fp += 1

        rows.append((name, expected_raw, expected, actual, match))

    # ── Per-patient table ──
    print("=" * 88)
    print("NAKED LLM (no protocol)  —  same model (claude-sonnet-4-6), zero scaffolding")
    print("=" * 88)
    print(f"{'PATIENT':<16}{'GROUND TRUTH':<16}{'REMAPPED':<14}{'LLM SAID':<14}{'RESULT'}")
    print("-" * 88)
    for name, expected_raw, expected, actual, match in rows:
        remap_note = f"({NAKED_REMAP[expected_raw]})" if expected_raw in NAKED_REMAP else ""
        flag = "PASS" if match else "FAIL"
        print(f"{name:<16}{expected_raw:<16}{expected:<14}{actual:<14}{flag}  {remap_note}")
    print("=" * 88)

    n = len(EXPECTED)
    recall    = (high_risk_caught / high_risk_total * 100) if high_risk_total else 0.0
    precision = (tp / (tp + fp) * 100) if (tp + fp) else 0.0
    accuracy  = exact_matches / n * 100

    print(f"\nNote: 'Nudge'→'Low' and 'Manual Queue'→'Medium' remapped (protocol-only concepts).")
    print(f"Exact-tier accuracy : {exact_matches}/{n}  ({accuracy:.0f}%)")
    print(f"Alert precision     : {precision:.0f}%   (of {tp+fp} flagged High, {tp} truly High)")
    print(f"High-risk recall    : {recall:.0f}%   ({high_risk_caught}/{high_risk_total} high-risk caught)"
          f"   {'✅ SAFE' if recall == 100 else '🚨 MISS — non-negotiable failure'}")
    print()
    if recall < 100:
        missed = [n for n, er, e, a, _ in rows if er in HIGH_RISK_TIERS and a not in HIGH_RISK_TIERS]
        print(f"⚠️  High-risk patients NOT caught as High: {missed}\n")

    out_path = "eval_results_naked.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Patient", "Ground Truth", "Remapped Expected", "Naked LLM", "Result"])
        for name, expected_raw, expected, actual, match in rows:
            w.writerow([name, expected_raw, expected, actual, "PASS" if match else "FAIL"])
    print(f"📄 Results written to {out_path}\n")

    return {"accuracy": accuracy, "precision": precision, "recall": recall,
            "exact": exact_matches, "n": n, "tp": tp, "fp": fp,
            "hr_caught": high_risk_caught, "hr_total": high_risk_total}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Run parser/bucketing only — no LLM call, no token spend.")
    ap.add_argument("--naked", action="store_true",
                    help="Bare-Claude baseline: no protocol, no rules, no schema.")
    args = ap.parse_args()

    if args.naked:
        name_to_tier = run_naked_pipeline()
        score_naked(name_to_tier)
        return

    final = run_pipeline(dry_run=args.dry_run)
    if final is None:   # dry run
        return
    score(final)

    # ── Freeze the full per-patient output for the demo build to replay ──
    # Captures every field (severity, confidence, nudge_risk, reasoning, signals)
    # across all buckets — this is what the Morning Brief UI renders.
    with open("frozen_output.json", "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    print("🧊 Full pipeline output frozen to frozen_output.json — feed this to the demo build.\n")


if __name__ == "__main__":
    main()
