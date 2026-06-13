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
import argparse

from parser import parse_all, load_thresholds
from prompt import load_protocol_files
from reasoning import run_reasoning, ENABLE_VERIFICATION
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Run parser/bucketing only — no LLM call, no token spend.")
    args = ap.parse_args()

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
