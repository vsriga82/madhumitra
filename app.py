import streamlit as st
import json
from datetime import date
from parser import parse_all, load_thresholds, load_patients
from prompt import load_protocol_files
from reasoning import run_reasoning
from ranker import run_ranker
from feedback import (
    mark_contacted, get_contact_status, should_alert,
    record_feedback, get_feedback_summary, get_all_feedback,
    extend_cooling
)

st.set_page_config(
    page_title="MadhuMitra",
    page_icon="🩺",
    layout="wide"
)

st.markdown("""
<style>
.main { background-color: #F8F7F4; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; }

/* Table layout */
.alert-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.alert-table th {
    font-size: 10px; font-weight: 500; text-transform: uppercase;
    letter-spacing: 0.05em; color: #6B6B65;
    padding: 8px 10px; text-align: left;
    border-bottom: 1px solid #E5E3DC;
    background: #F8F7F4;
}
.alert-table td {
    padding: 9px 10px;
    border-bottom: 0.5px solid #E5E3DC;
    vertical-align: middle;
    color: #1A1A18;
}
.alert-table tr:hover td { background: #F1EFE8; cursor: pointer; }
.alert-table tr.selected td { background: #E1F5EE; }
.alert-table tr:last-child td { border-bottom: none; }

/* Severity pills */
.pill { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 20px; white-space: nowrap; }
.pill-h { background: #FCEBEB; color: #A32D2D; }
.pill-m { background: #FAEEDA; color: #633806; }
.pill-l { background: #EAF3DE; color: #27500A; }
.pill-q { background: #EFF6FF; color: #1E40AF; }

/* Severity dots */
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; vertical-align: middle; flex-shrink: 0; }
.dot-h { background: #E24B4A; }
.dot-m { background: #EF9F27; }
.dot-l { background: #639922; }
.dot-q { background: #2563EB; }
.dot-f { background: #7C3AED; }

/* Signal chips */
.chip { display: inline-block; background: #F1EFE8; color: #5F5E5A; padding: 1px 7px; border-radius: 10px; font-size: 10px; margin: 1px 2px 1px 0; white-space: nowrap; }
.chip-more { background: #E6F1FB; color: #185FA5; }

/* Detail panel */
.detail-panel {
    background: white; border-radius: 10px;
    border: 0.5px solid #E5E3DC;
    padding: 16px; height: 100%;
}
.detail-name { font-size: 15px; font-weight: 500; color: #1A1A18; margin-bottom: 2px; }
.detail-sub { font-size: 12px; color: #6B6B65; margin-bottom: 12px; }
.detail-section { margin-bottom: 12px; }
.detail-section-label {
    font-size: 10px; font-weight: 500; text-transform: uppercase;
    letter-spacing: 0.05em; color: #9B9B94; margin-bottom: 5px;
}
.detail-field { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 0.5px solid #F1EFE8; }
.detail-field:last-child { border: none; }
.detail-key { color: #6B6B65; }
.detail-val { color: #1A1A18; font-weight: 500; text-align: right; }
.escalate-bar { background: #FEF2F2; border: 0.5px solid #FECACA; border-radius: 6px; padding: 6px 10px; font-size: 11px; color: #991B1B; margin-bottom: 10px; }
.reasoning-text { font-size: 12px; color: #6B6B65; line-height: 1.6; }

/* Action buttons */
.action-row { display: flex; gap: 5px; align-items: center; flex-wrap: wrap; }
.btn-sm { font-size: 12px; background: white; border: 0.5px solid #E5E3DC; border-radius: 5px; padding: 3px 8px; cursor: pointer; }
.btn-contact { font-size: 11px; background: #E1F5EE; color: #085041; border: 0.5px solid #5DCAA5; border-radius: 5px; padding: 3px 9px; cursor: pointer; white-space: nowrap; }

/* Empty states */
.empty-state { text-align: center; padding: 40px 20px; color: #9B9B94; font-size: 13px; }
</style>
""", unsafe_allow_html=True)


# ── Protocol cache ────────────────────────────────────────────
@st.cache_resource
def load_protocol():
    return load_protocol_files()

@st.cache_resource
def get_thresholds():
    return load_thresholds()


# ── Session state init ────────────────────────────────────────
defaults = {
    "results": None,
    "data_loaded": False,
    "demo_mode": False,
    "uploaded_file": None,
    "selected_patient": None,
    "mobile_view": False,
    "show_wrong": {},
    "show_cooling": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🩺 MadhuMitra")
    st.caption("Clinical Protocol Intelligence Layer")
    st.divider()

    st.markdown("**Step 1 — Patient data**")

    if st.button("🔬 Load sample patients", type="primary", use_container_width=True):
        st.session_state.demo_mode = True
        st.session_state.uploaded_file = None
        st.session_state.data_loaded = True
        st.session_state.results = None
        st.session_state.selected_patient = None

    if st.session_state.demo_mode and st.session_state.data_loaded:
        st.success("✓ 8 sample patients loaded")

    uploaded = st.file_uploader("Or upload CSV / JSON", type=["csv","json"])
    if uploaded:
        st.session_state.demo_mode = False
        st.session_state.uploaded_file = uploaded
        st.session_state.data_loaded = True
        st.session_state.results = None
        st.session_state.selected_patient = None
        st.success(f"✓ {uploaded.name} uploaded")

    st.divider()

    st.markdown("**Step 2 — Run analysis**")
    run_clicked = st.button(
        "▶ Run reasoning loop",
        type="primary",
        use_container_width=True,
        disabled=not st.session_state.data_loaded,
        help="Load patient data first" if not st.session_state.data_loaded else ""
    )
    if not st.session_state.data_loaded:
        st.caption("⬆ Load patient data first")

    st.divider()

    # View toggle
    st.markdown("**View**")
    mobile = st.toggle("📱 Mobile view", value=st.session_state.mobile_view)
    st.session_state.mobile_view = mobile
    st.caption("Desktop: split view · Mobile: table + expand")

    st.divider()

    # Precision tracking
    fb = get_feedback_summary()
    if fb["total"] > 0:
        st.markdown("**Alert precision**")
        color = "green" if (fb["precision"] or 0) >= 80 else "orange"
        st.markdown(f":{color}[**{fb['precision']}%**] ({fb['correct']}/{fb['total']} correct)")
    else:
        st.caption("Precision tracking starts after first 👍/👎")

    st.divider()
    st.caption("Every alert is a recommendation.")
    st.caption("Coach reviews and acts every time.")


# ── Run analysis ──────────────────────────────────────────────
if run_clicked:
    alert_guide, thresholds, guardrails, output_schema = load_protocol()
    thresholds_data = get_thresholds()
    filepath = "data/sample_patients.json" if st.session_state.demo_mode else None

    if st.session_state.uploaded_file:
        import tempfile
        f = st.session_state.uploaded_file
        suffix = ".csv" if f.name.endswith(".csv") else ".json"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(f.read())
            filepath = tmp.name

    with st.status("Running MadhuMitra analysis...", expanded=True) as status:
        st.write("📋 Parsing patient logs...")
        parse_results = parse_all(filepath)

        total = len(parse_results["send_to_llm"])
        rules = len(parse_results["rules_alerted"])
        on_track = len(parse_results["on_track"])

        st.write(f"✓ {rules} patients flagged by rules — no AI needed")
        st.write(f"✓ {on_track} patients on track — skipping AI")
        st.write(f"🧠 Sending {total} patients to AI reasoning loop...")

        llm_results = run_reasoning(
            parse_results["send_to_llm"],
            alert_guide, thresholds, guardrails, output_schema
        )

        st.write("📊 Ranking results by priority...")
        final = run_ranker(parse_results, llm_results, thresholds_data)
        st.session_state.results = final
        st.session_state.selected_patient = None

        total_alerts = len(final["auto_list"]) + len(final["queue_list"])
        status.update(
            label=f"✓ Analysis complete — {total_alerts} alerts generated",
            state="complete"
        )


# ── Helper: get patient details ───────────────────────────────
def get_patient_detail_data(patient):
    """Extracts clean display data from a patient result."""
    s = patient.get("structured", {})
    h = patient.get("program_history", {})
    u = patient.get("unstructured", {})
    comorbidities = h.get("comorbidities", {})
    active_comorbidities = [
        k.replace("_", " ")
        for k, v in comorbidities.items() if v is True
    ]
    return s, h, u, active_comorbidities


# ── Helper: signal chips HTML ─────────────────────────────────
def chips_html(signals, max_show=2):
    html = ""
    for s in signals[:max_show]:
        short = s[:28] + "…" if len(s) > 28 else s
        html += f'<span class="chip">{short}</span>'
    if len(signals) > max_show:
        html += f'<span class="chip chip-more">+{len(signals)-max_show}</span>'
    return html


# ── Helper: severity css ──────────────────────────────────────
def sev_css(severity):
    return {"High": "h", "Medium": "m", "Low": "l"}.get(severity, "q")


# ── Render detail panel ───────────────────────────────────────
def render_detail(patient):
    if not patient:
        st.markdown(
            '<div class="empty-state">Select a patient to see details</div>',
            unsafe_allow_html=True
        )
        return

    name = patient.get("name", "")

    # Merge with raw patient data
    raw_patients = st.session_state.get("raw_patients", {})
    raw = raw_patients.get(name, {})
    s = raw.get("structured", patient.get("structured", {}))
    h = raw.get("program_history", patient.get("program_history", {}))
    u = raw.get("unstructured", patient.get("unstructured", {}))

    severity          = patient.get("severity", "")
    signals           = patient.get("signals", [])
    # Rules-alerted patients use deviations instead of signals
    if not signals:
        raw_deviations = patient.get("deviations", [])
        signals = [d.replace("_", " ") for d in raw_deviations]
    reasoning         = patient.get("reasoning", "") or patient.get("rules_reasoning", "")
    escalate          = patient.get("escalate_to_doctor", False)
    escalation_reasons = patient.get("escalation_reasons", [])
    targets           = h.get("clinical_targets", {})
    comorbidities_dict = h.get("comorbidities", {})
    comorbidities     = [k.replace("_"," ") for k,v in comorbidities_dict.items() if v is True]
    contact_status    = get_contact_status(name)
    age               = raw.get("age") or patient.get("age", "")
    gender            = raw.get("gender") or patient.get("gender", "")

    sev_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(severity, "⚪")

    # ── Header ─────────────────────────────────────────────────
    st.markdown(f"**{sev_emoji} {name} — {severity}**")
    st.caption(
        f"Age {age} · {gender} · Week {h.get('week_number','?')} · "
        f"{', '.join(comorbidities) if comorbidities else 'No comorbidities'}"
    )

    # ── Status badge — severity + escalation flag ─────────────
    if escalate:
        st.markdown(
            f'<div style="background:#FEF2F2;border:0.5px solid #FECACA;'
            f'border-radius:8px;padding:8px 14px;margin:8px 0;font-size:12px;">'
            f'🚨 <strong>Doctor escalation recommended</strong> — '
            f'{", ".join(escalation_reasons)}</div>',
            unsafe_allow_html=True
        )
    elif severity == "High":
        st.markdown(
            '<div style="background:#FEF2F2;border:0.5px solid #FECACA;'
            'border-radius:8px;padding:8px 14px;margin:8px 0;font-size:12px;">'
            '🔴 <strong>High priority</strong> — same-day contact</div>',
            unsafe_allow_html=True
        )
    elif severity == "Medium":
        st.markdown(
            '<div style="background:#FFFBEB;border:0.5px solid #FDE68A;'
            'border-radius:8px;padding:8px 14px;margin:8px 0;font-size:12px;">'
            '🟡 <strong>Medium priority</strong> — within 24 hours</div>',
            unsafe_allow_html=True
        )

    if contact_status:
        days = contact_status["days_since_contact"]
        remaining = contact_status["days_remaining"]
        st.info(
            f"🔄 Contacted {days} day{'s' if days!=1 else ''} ago · "
            f"Cooling expires in {remaining} day{'s' if remaining!=1 else ''}"
        )

    # ── WHY block — colour-coded signals ─────────────────────
    st.markdown("**Why this alert was raised**")

    # Classify signals by urgency for colour coding
    tier1_keywords = ["foamy", "blurry", "chest", "dizziness", "dizzy",
                      "swelling", "numbness", "tingling"]
    high_keywords  = ["medication missed", "above high threshold", "bp 1",
                      "above 200", "consecutive missed log"]
    med_keywords   = ["above medium", "above threshold", "above target",
                      "stress score", "sleep", "exercise 0", "below target",
                      "craving", "negative mood"]

    def signal_colour(sig):
        sl = sig.lower()
        if any(k in sl for k in tier1_keywords):
            return "#DC2626", "#FEF2F2", "🔴"
        if any(k in sl for k in high_keywords):
            return "#DC2626", "#FEF2F2", "🔴"
        if any(k in sl for k in med_keywords):
            return "#D97706", "#FFFBEB", "🟡"
        return "#6B7280", "#F9FAFB", "🟠"

    if signals:
        for sig in signals[:8]:
            color, bg, dot = signal_colour(sig)
            st.markdown(
                f'<div style="background:{bg};border-left:3px solid {color};'
                f'padding:5px 10px;border-radius:0 5px 5px 0;'
                f'font-size:12px;color:#1A1A18;margin-bottom:4px;">'
                f'{dot} {sig}</div>',
                unsafe_allow_html=True
            )

    # ── Reasoning — narrative ─────────────────────────────────
    if reasoning:
        with st.expander("Full reasoning", expanded=False):
            st.caption(reasoning)

    # ── Today's data ──────────────────────────────────────────
    with st.expander("Today's data", expanded=True):
        s_data = [
            ("FBS", f"{s.get('fbs_mgdl','—')} mg/dL",
             f"target {targets.get('fbs_target_mgdl','—')}"),
            ("Exercise", f"{s.get('exercise_minutes','—')} min",
             s.get('exercise_type','') or ""),
            ("Sleep", f"{s.get('sleep_hours','—')} hrs",
             s.get('sleep_quality','') or ""),
            ("BP", f"{s.get('blood_pressure_systolic','—')}/"
             f"{s.get('blood_pressure_diastolic','—')} mmHg", ""),
            ("Stress", f"{s.get('stress_score','—')}/5", ""),
            ("Protein", f"{s.get('protein_g','—')}g",
             f"target {h.get('protein_target_g','—')}g"),
            ("Carbs", f"{s.get('carbs_g','—')}g",
             f"target {h.get('carb_target_g','—')}g"),
            ("Medication",
             "✓ Taken" if s.get('medication_taken') else "✗ Missed", ""),
        ]
        for label, val, sub in s_data:
            cl, cr = st.columns([1.2, 1.8])
            cl.caption(label)
            cr.caption(f"**{val}** {sub}" if sub else f"**{val}**")

        if u.get("free_text"):
            st.caption(f"💬 *\"{u['free_text']}\"*")
        if u.get("coach_notes"):
            st.caption(f"📋 {u['coach_notes']}")

    st.divider()

    # ── Actions ───────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("👍 Correct", key=f"det_up_{name}", use_container_width=True):
            record_feedback(name, severity, patient.get("track","auto"),
                          signals, reasoning, "correct")
            st.success("✓ Saved")
            st.rerun()
    with col_b:
        if st.button("👎 Wrong", key=f"det_dn_{name}", use_container_width=True):
            st.session_state.show_wrong[name] = True
            st.rerun()

    if st.session_state.show_wrong.get(name):
        wr = st.selectbox("Why wrong?",
            ["Select…","Not urgent / false positive","Severity too high",
             "Severity too low","Patient already handled","Other"],
            key=f"wr_{name}")
        if wr != "Select…":
            if st.button("Submit", key=f"wrsub_{name}", use_container_width=True):
                record_feedback(name, severity, patient.get("track","auto"),
                              signals, reasoning, "incorrect", wr)
                st.session_state.show_wrong[name] = False
                st.rerun()

    if not contact_status:
        if st.button("📞 Mark contacted", key=f"det_con_{name}",
                    use_container_width=True):
            st.session_state.show_cooling[name] = True
            st.rerun()
        if st.session_state.show_cooling.get(name):
            cl = st.selectbox("Cooling period",
                ["High priority (1 day)", "Medium priority (2 days)",
                 "Low priority (3 days)"],
                key=f"cl_{name}")
            level = cl.split(" ")[0]
            if st.button("Confirm", key=f"clconf_{name}",
                        use_container_width=True):
                mark_contacted(name, severity, level, signals)
                st.session_state.show_cooling[name] = False
                st.rerun()
    else:
        col_ext, col_ov = st.columns(2)
        with col_ext:
            extra = st.number_input("Extend (days)", 1, 7, 1,
                                   key=f"ext_{name}")
            if st.button("Extend cooling", key=f"extb_{name}",
                        use_container_width=True):
                extend_cooling(name, extra)
                st.rerun()
        with col_ov:
            if st.button("Override → alert", key=f"ov_{name}",
                        use_container_width=True):
                mark_contacted(name, severity, "High", signals)
                st.rerun()


# ── Render patient table ──────────────────────────────────────
def render_table(patients, card_type="alert"):
    if not patients:
        st.markdown('<div class="empty-state">No patients in this category</div>',
                   unsafe_allow_html=True)
        return

    thresholds_data = get_thresholds()

    for i, patient in enumerate(patients):
        name = patient.get("name","")
        severity = patient.get("severity","")
        signals = patient.get("signals", [])
        # Rules-alerted patients use deviations
        if not signals:
            signals = [d.replace("_"," ") for d in patient.get("deviations", [])]
        escalate = patient.get("escalate_to_doctor", False)
        contact_status = get_contact_status(name)

        is_selected = st.session_state.selected_patient == name
        sev_c = sev_css(severity)

        # Row — no dot, pill carries the colour
        col_name, col_sev, col_sig, col_act = st.columns([2.5, 1, 3, 1.5])

        with col_name:
            label = f"**{name}**"
            if escalate: label += " 🚨"
            if contact_status: label += " 📞"
            if st.button(label, key=f"row_{card_type}_{i}", use_container_width=True):
                if st.session_state.selected_patient == name:
                    st.session_state.selected_patient = None
                else:
                    st.session_state.selected_patient = name
                st.rerun()

        with col_sev:
            st.markdown(
                f'<span class="pill pill-{sev_c}">{severity}</span>',
                unsafe_allow_html=True
            )

        with col_sig:
            st.markdown(chips_html(signals, 2), unsafe_allow_html=True)

        with col_act:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👍", key=f"up_{card_type}_{i}",
                            help="Correct alert"):
                    record_feedback(name, severity, patient.get("track","auto"),
                                  signals, patient.get("reasoning",""), "correct")
                    st.rerun()
            with c2:
                if st.button("👎", key=f"dn_{card_type}_{i}",
                            help="Wrong alert"):
                    st.session_state.show_wrong[name] = True
                    st.session_state.selected_patient = name
                    st.rerun()

        # Wrong reason inline
        if st.session_state.show_wrong.get(name):
            wr = st.selectbox("Why wrong?",
                ["Select…","Not urgent / false positive","Severity too high",
                 "Severity too low","Patient already handled","Other"],
                key=f"twr_{name}_{i}")
            if wr != "Select…":
                if st.button("Submit", key=f"twrsub_{name}_{i}"):
                    record_feedback(name, severity, patient.get("track","auto"),
                                  signals, patient.get("reasoning",""), "incorrect", wr)
                    st.session_state.show_wrong[name] = False
                    st.rerun()

        # Expand on mobile
        if st.session_state.mobile_view and is_selected:
            with st.container():
                render_detail(patient)

        st.markdown(
            '<hr style="margin:4px 0;border:none;border-top:0.5px solid #E5E3DC;">',
            unsafe_allow_html=True
        )


# ── Main display ──────────────────────────────────────────────
if st.session_state.data_loaded and not st.session_state.results:
    st.markdown("## 🩺 MadhuMitra — Coach Dashboard")
    st.divider()
    # Patient preview before analysis
    st.markdown("### Patient panel")
    try:
        filepath = "data/sample_patients.json" if st.session_state.demo_mode else None
        if filepath:
            preview_patients = load_patients(filepath)
            preview_data = []
            for p in preview_patients:
                h = p.get("program_history", {})
                s = p.get("structured", {})
                comorbidities = h.get("comorbidities", {})
                active = [k.replace("_"," ") for k,v in comorbidities.items() if v is True]
                preview_data.append({
                    "Name": p.get("name",""),
                    "Age/Gender": f"{p.get('age','')}{p.get('gender','')}",
                    "Week": h.get("week_number",""),
                    "FBS": f"{s.get('fbs_mgdl','—')} mg/dL" if s.get('fbs_mgdl') else "No log",
                    "Comorbidities": ", ".join(active[:2]) if active else "None"
                })
            import pandas as pd
            st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
            st.caption(f"{len(preview_patients)} patients loaded · Click Run reasoning loop to analyse")
    except Exception:
        pass

elif st.session_state.results:
    r = st.session_state.results
    summary = r["summary"]
    thresholds_data = get_thresholds()

    # Route patients first — needed for accurate header counts
    # Store raw patient data for detail panel
    raw_filepath = "data/sample_patients.json" if st.session_state.demo_mode else None
    raw_patients = {}
    if raw_filepath:
        try:
            import json as _json
            with open(raw_filepath) as f:
                raw_data = _json.load(f)
            for p in raw_data.get("patients", []):
                raw_patients[p["name"]] = p
        except Exception:
            pass
    st.session_state["raw_patients"] = raw_patients

    # Route patients — deduplicate nudge list
    alert_patients, followup_patients, new_dev_patients = [], [], []
    nudge_names_already = set(p.get("name") for p in r["nudge_list"])

    for p in r["auto_list"] + r["queue_list"]:
        name = p.get("name")
        severity = p.get("severity", "")
        nudge = p.get("nudge_risk", False)
        status = get_contact_status(name)

        if severity == "Low" and nudge and name not in nudge_names_already:
            r["nudge_list"].append(p)
            nudge_names_already.add(name)
            continue
        elif severity == "Low" and nudge:
            continue

        if not status:
            alert_patients.append(p)
        else:
            routing = should_alert(name, p.get("signals",[]),
                                  p.get("severity"), thresholds_data)
            if routing == "new_deviation_alert":
                new_dev_patients.append(p)
            elif routing == "followup":
                followup_patients.append(p)
            else:
                alert_patients.append(p)

    # Accurate counts matching tabs
    total_alerts   = len(alert_patients) + len(new_dev_patients)
    total_followup = len(followup_patients)
    total_queue    = len([p for p in r["queue_list"]
                         if not any(p.get("name")==fp.get("name")
                                   for fp in followup_patients)])
    total_ontrack  = len(r["on_track"])

    # Severity breakdown within alerts (shown inside tab)
    all_alert_patients = alert_patients + new_dev_patients
    high_count = len([p for p in all_alert_patients if p.get("severity") == "High"])
    med_count  = len([p for p in all_alert_patients if p.get("severity") == "Medium"])
    low_count  = len([p for p in all_alert_patients if p.get("severity") == "Low"])

    # Header — counts match tabs exactly
    col_title, col_metrics = st.columns([2.5, 1.5])
    with col_title:
        st.markdown("## 🩺 MadhuMitra — Coach Dashboard")
        st.caption(
            f"Clinical Protocol Intelligence Layer · "
            f"DiRECT/ADA Baseline v1.0 · {date.today().strftime('%d %B %Y')}"
        )
    with col_metrics:
        st.markdown("")
        st.markdown(
            f"🚨 **{total_alerts}** alerts &nbsp;·&nbsp; "
            f"📞 **{total_followup}** follow-up &nbsp;·&nbsp; "
            f"✅ **{total_ontrack}** on track"
        )
        if summary["escalate"] > 0:
            st.caption(f"🚨 {summary['escalate']} escalation(s) — see alert list")

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"🚨 Alerts ({total_alerts})",
        f"📞 Follow-up ({total_followup})",
        f"🔍 Review ({total_queue})",
        f"💡 Nudge · On track ({len(r['nudge_list'])+total_ontrack})",
        "📈 Feedback"
    ])

    def render_tab(patients, card_type):
        if st.session_state.mobile_view:
            # Mobile: table + expand inline
            col_headers = st.columns([2.5,1,3,1.5])
            col_headers[0].caption("Patient")
            col_headers[1].caption("Severity")
            col_headers[2].caption("Key signals")
            col_headers[3].caption("React")
            render_table(patients, card_type)
        else:
            # Desktop: split view
            selected = st.session_state.selected_patient
            selected_patient_obj = next(
                (p for p in patients if p.get("name") == selected), None
            )
            left, right = st.columns([1.2, 1])
            with left:
                col_h1, col_h2, col_h3, col_h4 = st.columns([2.5,1,3,1.5])
                col_h1.caption("Patient")
                col_h2.caption("Severity")
                col_h3.caption("Key signals")
                col_h4.caption("React")
                render_table(patients, card_type)
            with right:
                render_detail(selected_patient_obj)

    with tab1:
        # Severity breakdown — matches the total shown in header
        st.caption(
            f"🔴 {high_count} High &nbsp;·&nbsp; "
            f"🟡 {med_count} Medium &nbsp;·&nbsp; "
            f"🟢 {low_count} Low &nbsp;·&nbsp; "
            f"Act on these today"
        )
        if new_dev_patients:
            st.warning(f"⚠️ {len(new_dev_patients)} patient(s) in cooling period have NEW deviations")
            render_tab(new_dev_patients, "newdev")
            st.divider()
        if alert_patients:
            render_tab(alert_patients, "alert")
        elif not new_dev_patients:
            st.success("No new alerts — all patients on track or in follow-up.")

    with tab2:
        st.caption("Contacted within cooling period — same deviation, stable")
        if followup_patients:
            render_tab(followup_patients, "followup")
        else:
            st.info("No patients in follow-up period.")

    with tab3:
        st.caption("Signals present but confidence is low — apply your clinical judgement")
        queue = [p for p in r["queue_list"]
                if not any(p.get("name")==fp.get("name") for fp in followup_patients)]
        if queue:
            render_tab(queue, "queue")
        else:
            st.success("No cases in the manual review queue.")

    with tab4:
        if r["nudge_list"]:
            st.subheader("💡 Warm check-in recommended")
            for p in r["nudge_list"]:
                st.info(f"**{p.get('name')}** — {p.get('reasoning','')}")
        st.subheader("✅ On track today")
        for p in r["on_track"]:
            st.success(f"**{p.get('name')}** — No deviations detected across all signals")
        if not r["on_track"]:
            st.caption("No patients fully on track today.")

    with tab5:
        st.subheader("📊 Coach feedback log")
        fb = get_feedback_summary()
        if fb["total"] > 0:
            m1,m2,m3 = st.columns(3)
            m1.metric("Alerts reviewed", fb["total"])
            m2.metric("Correct 👍", fb["correct"])
            m3.metric("Precision", f"{fb['precision']}%")
            if fb["wrong_reasons"]:
                st.markdown("**Common correction reasons:**")
                for r_name, count in fb["wrong_reasons"].items():
                    st.caption(f"· {r_name}: {count}x")
            all_fb = get_all_feedback()
            if all_fb:
                st.markdown("**Recent feedback:**")
                for eid, entry in list(all_fb.items())[-8:]:
                    emoji = "👍" if entry["reaction"]=="correct" else "👎"
                    reason = f" — {entry['wrong_reason']}" if entry.get("wrong_reason") else ""
                    st.caption(
                        f"{emoji} **{entry['patient_name']}** | "
                        f"{entry['severity']} | {entry['date']}{reason}"
                    )
        else:
            st.info("No feedback yet. Use 👍/👎 on alerts to track precision.")

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center;padding:80px 20px;color:#9B9B94;">
        <div style="font-size:56px;margin-bottom:16px;">🩺</div>
        <p style="font-size:16px;margin-bottom:6px;color:#6B6B65;">Ready to analyse your patient panel</p>
        <p style="font-size:13px;">Load sample patients or upload a file,<br>then click <strong>Run reasoning loop</strong></p>
    </div>
    """, unsafe_allow_html=True)
