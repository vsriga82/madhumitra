import json
import asyncio
import os
import anthropic
from anthropic import AsyncAnthropic
from prompt import load_protocol_files, build_prompt

# Read API key from Streamlit secrets (deployed) or env var (local)
def get_api_key():
    try:
        import streamlit as st
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")

client = AsyncAnthropic(api_key=get_api_key())

# Dual loop verification — disabled for MVP
# Requires higher API tier (100K+ TPM) to run reliably
ENABLE_VERIFICATION = False


# ── Deterministic escalation rules ───────────────────────────
def apply_escalation_rules(result, patient, thresholds):
    """
    Applies deterministic escalation rules after every LLM response.
    Clinical safety decisions use rules — not LLM judgment.
    This runs regardless of whether verification is enabled.
    """
    s = patient.get("structured", {})
    history = patient.get("program_history", {})
    comorbidities = history.get("comorbidities", {})
    free_text = (patient.get("unstructured", {}).get("free_text") or "").lower()
    coach_notes = (patient.get("unstructured", {}).get("coach_notes") or "").lower()
    combined_text = free_text + " " + coach_notes

    escalate = False
    escalation_reasons = []

    # Chest pain — always escalate
    if any(k in combined_text for k in ["chest pain", "chest discomfort", "chest tightness"]):
        escalate = True
        escalation_reasons.append("chest pain or discomfort reported")

    # Foamy urine + CKD
    has_ckd = comorbidities.get("chronic_kidney_disease", False)
    if any(k in combined_text for k in ["foamy urine", "frothy urine"]) and has_ckd:
        escalate = True
        escalation_reasons.append("foamy urine with known CKD")

    # Blurry vision
    if any(k in combined_text for k in ["blurry vision", "cloudy vision", "vision blurred"]):
        escalate = True
        escalation_reasons.append("blurry vision reported")

    # BP above high threshold
    bp_systolic = s.get("blood_pressure_systolic")
    bp_high = thresholds.get("blood_pressure", {}).get("systolic", {}).get("high_threshold", 140)
    if bp_systolic and bp_systolic > bp_high:
        escalate = True
        escalation_reasons.append(f"BP {bp_systolic}/{s.get('blood_pressure_diastolic')} mmHg above high threshold")

    # FBS critically elevated
    fbs = s.get("fbs_mgdl")
    if fbs and fbs > 200:
        escalate = True
        escalation_reasons.append(f"FBS {fbs} mg/dL critically elevated")

    # Patient requests doctor
    if any(k in combined_text for k in ["speak to doctor", "want to see doctor", "need doctor"]):
        escalate = True
        escalation_reasons.append("patient requested doctor contact")

    if escalate:
        result["escalate_to_doctor"] = True
        result["signals"] = result.get("signals", []) + escalation_reasons
        result["escalation_reasons"] = escalation_reasons

    return result


# ── Single patient reasoning call ────────────────────────────
async def reason_one_patient(patient, alert_guide, thresholds,
                              guardrails, output_schema, semaphore=None):
    """
    Calls OpenAI to reason about one patient.
    Uses passed semaphore to stay within TPM rate limits.
    """
    if semaphore is None:
        semaphore = asyncio.Semaphore(2)
    async with semaphore:
        system_prompt, user_message = build_prompt(
            patient, alert_guide, thresholds, guardrails, output_schema
        )

        feedback = patient.get("verification_feedback", "")
        if feedback:
            user_message += f"\n\nPrevious attempt feedback: {feedback}"

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1200
            )
            raw = response.content[0].text if response.content else ""
            # Strip markdown code fences — Sonnet wraps JSON in ```json blocks
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines).strip()
            if not raw:
                raise ValueError("Empty response from model")
            result = json.loads(raw)
            result["name"] = patient.get("name")
            result["source"] = "llm"
            await asyncio.sleep(2)   # brief pause between calls
            return result

        except anthropic.RateLimitError:
            print(f"  ⏳ Rate limited — waiting 30s...")
            await asyncio.sleep(30)
            return None
        except Exception as e:
            print(f"  ✗ Call failed for {patient.get('name')}: {e}")
            return None


# ── Guardrails verifier — Loop 2 (optional) ──────────────────
async def verify_response(patient_name, llm_result, semaphore=None):
    """
    Loop 2 — Verifies output against guardrails.
    Only runs when ENABLE_VERIFICATION is True.

    NOTE FOR DEMO:
    Disabled (ENABLE_VERIFICATION = False) for MVP.
    Architecture is ready — flip the flag above to enable.
    """
    if semaphore is None:
        semaphore = asyncio.Semaphore(2)
    async with semaphore:
        verification_prompt = f"""Safety check for MadhuMitra alert.
Return JSON: {{"passed": true/false, "reason": "brief"}}

FAIL only if:
1. Reasoning contains actual diagnosis: "patient HAS [disease]"
2. Reasoning contains actual prescription: "patient SHOULD take [medication]"
3. Required JSON field completely missing
4. Impossible routing: severity/confidence/track don't match this table:
   High+high→auto, High+low→queue, Medium+high→auto, Medium+low→queue,
   Low+high→auto, Low+low→queue, OnTrack+high→on_track

Surfacing signals, citing values, mentioning comorbidities = PASS.
Recommending coach contact = PASS.

ALERT: {json.dumps(llm_result, indent=2)}"""

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                messages=[{"role": "user", "content": verification_prompt}],
                max_tokens=100
            )
            result = json.loads(response.content[0].text)
            await asyncio.sleep(1)
            return result.get("passed", False), result.get("reason", "")
        except Exception as e:
            return False, f"Verifier failed: {e}"


# ── Full reasoning loop ───────────────────────────────────────
async def reason_with_retry(patient, alert_guide, thresholds,
                             guardrails, output_schema, max_retries=1,
                             semaphore=None):
    """
    Runs reasoning for one patient with retry logic.
    """
    if semaphore is None:
        semaphore = asyncio.Semaphore(2)
    name = patient.get("name", "Unknown")
    attempt = 0
    result = None

    while attempt <= max_retries:
        attempt += 1
        print(f"  → {name}: attempt {attempt}/{max_retries + 1}")

        result = await reason_one_patient(
            patient, alert_guide, thresholds, guardrails, output_schema,
            semaphore=semaphore
        )

        if result is None:
            if attempt <= max_retries:
                print(f"  ↺ {name}: retrying...")
                await asyncio.sleep(10)
                continue
            break

        # Always apply deterministic escalation rules
        result = apply_escalation_rules(result, patient, thresholds)

        # Optional Loop 2 verification
        if ENABLE_VERIFICATION:
            passed, reason = await verify_response(name, result, semaphore=semaphore)
            if passed:
                print(f"  ✓ {name}: verified — {result.get('severity')} / {result.get('track')}")
                result["verified"] = True
                result["verification_note"] = reason
                return result
            else:
                print(f"  ⚠ {name}: verification failed — {reason}")
                if attempt <= max_retries:
                    patient["verification_feedback"] = f"Fix: {reason}"
        else:
            # Verification disabled — trust Loop 1 output
            print(f"  ✓ {name}: {result.get('severity')} / {result.get('track')}")
            result["verified"] = False
            result["verification_note"] = "Verification disabled — enable for production"
            return result

    # Retry exhausted
    print(f"  → {name}: routing to manual queue")
    if result:
        result["track"] = "queue"
        result["confidence"] = "low"
        result["verified"] = False
        result["verification_note"] = "Routed after failed attempts"
        return result

    return {
        "name": name,
        "severity": "Unknown",
        "confidence": "low",
        "track": "queue",
        "reasoning": "Analysis failed — manual review required",
        "signals": [],
        "has_tier1_symptom": False,
        "medication_missed": False,
        "consecutive_days": 1,
        "glucose_trend": "unknown",
        "escalate_to_doctor": False,
        "nudge_risk": False,
        "source": "llm",
        "verified": False,
        "verification_note": "Complete analysis failure"
    }


# ── Run all patients concurrently ─────────────────────────────
async def reason_all_patients(send_to_llm, alert_guide, thresholds,
                               guardrails, output_schema):
    """
    Runs reasoning for all flagged patients concurrently.
    Semaphore created fresh each run — avoids event loop conflict.
    """
    if not send_to_llm:
        return []

    # Create semaphore here — bound to current event loop
    semaphore = asyncio.Semaphore(2)

    mode = "with verification" if ENABLE_VERIFICATION else "without verification (MVP mode)"
    print(f"\nRunning reasoning loop for {len(send_to_llm)} patients ({mode})...")

    tasks = [
        reason_with_retry(
            patient, alert_guide, thresholds, guardrails, output_schema,
            semaphore=semaphore
        )
        for patient in send_to_llm
    ]

    results = await asyncio.gather(*tasks)
    return list(results)


# ── Sync wrapper for Streamlit ────────────────────────────────
def run_reasoning(send_to_llm, alert_guide, thresholds,
                  guardrails, output_schema):
    """
    Synchronous wrapper — Streamlit can't call async directly.
    """
    return asyncio.run(
        reason_all_patients(
            send_to_llm, alert_guide, thresholds,
            guardrails, output_schema
        )
    )
