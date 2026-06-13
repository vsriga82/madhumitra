import re
import streamlit as st
import json
from datetime import date, datetime
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
    layout="centered"
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background-color: #F0FDFA !important; }
[data-testid="stAppViewContainer"] { background-color: #F0FDFA !important; }
[data-testid="stHeader"] { background-color: transparent !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 3rem; }

/* ── Brief header ─────────────────────────────── */
.brief-header {
  background: #0D9488; border-radius: 12px;
  padding: 18px 20px 0; color: white; margin-bottom: 1.2rem;
}
.brief-greeting { font-size: 11px; opacity: 0.8; margin-bottom: 2px; font-weight: 500; }
.brief-title-row { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 14px; }
.brief-title { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }
.brief-date { font-size: 11px; background: rgba(255,255,255,0.18); padding: 3px 10px; border-radius: 20px; font-weight: 500; }

/* Nav pills — anchor links, all browser states overridden */
.summary-bar { display: flex; gap: 8px; padding-bottom: 16px; }
.summary-pill,
.summary-pill:link,
.summary-pill:visited,
.summary-pill:hover,
.summary-pill:active,
.summary-pill:focus {
  flex: 1; border-radius: 8px; padding: 9px 10px; text-align: center;
  color: white !important; text-decoration: none !important;
  display: block; transition: opacity 0.15s; outline: none;
}
.summary-pill:hover { opacity: 0.82; }
.summary-pill .num { font-size: 22px; font-weight: 700; line-height: 1; }
.summary-pill .lbl { font-size: 10px; opacity: 0.85; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.04em; }
.pill-urgent  { background: rgba(239,68,68,0.35); }
.pill-watch   { background: rgba(245,158,11,0.35); }
.pill-routine { background: rgba(16,185,129,0.35); }
.pill-slip    { background: rgba(249,115,22,0.35); }
.pill-queue   { background: rgba(99,102,241,0.35); }

/* ↑ top anchor in section headers */
.top-link,
.top-link:link,
.top-link:visited,
.top-link:hover,
.top-link:active {
  font-size: 10px; color: #9CA3AF !important; text-decoration: none !important;
  letter-spacing: 0.03em; cursor: pointer;
}
.top-link:hover { color: #0D9488 !important; }

/* ── Section labels ───────────────────────────── */
.section-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 0 8px; }
.section-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #6B7280; }

/* ── Patient cards ────────────────────────────── */
.patient-card {
  background: white; border-radius: 10px 10px 0 0;
  border: 1px solid #E5E7EB; border-bottom: none; overflow: hidden;
}
.patient-card.urgent  { border-left: 4px solid #EF4444; }
.patient-card.watch   { border-left: 4px solid #F59E0B; }
.patient-card.routine { border-left: 4px solid #10B981; }
.patient-card.ontrack { border-left: 4px solid #10B981; }
.patient-card.queue   { border-left: 4px solid #6366F1; }
.patient-card.slippage{ border-left: 4px solid #F97316; }

.card-top { padding: 12px 14px 8px; }
.card-row1 { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 5px; }
.patient-name { font-size: 14px; font-weight: 600; color: #111827; }

/* Fix: ensure card reason text wraps fully */
.flag-reason {
  font-size: 12px; color: #374151; line-height: 1.5;
  margin-bottom: 8px; white-space: normal;
  word-wrap: break-word; overflow-wrap: break-word;
}
.meta-row { display: flex; gap: 10px; flex-wrap: wrap; }
.meta-tag { font-size: 10px; color: #9CA3AF; }

/* ── Severity badges ──────────────────────────── */
.severity-badge {
  font-size: 10px; font-weight: 700; padding: 2px 9px;
  border-radius: 20px; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
}
.badge-urgent   { background: #FEF2F2; color: #EF4444;  border: 1px solid #FECACA; }
.badge-watch    { background: #FFFBEB; color: #B45309;  border: 1px solid #FDE68A; }
.badge-routine  { background: #ECFDF5; color: #065F46;  border: 1px solid #A7F3D0; }
.badge-queue    { background: #EEF2FF; color: #4338CA;  border: 1px solid #C7D2FE; }
.badge-slippage { background: #FFF7ED; color: #C2410C;  border: 1px solid #FED7AA; }
.badge-ontrack  { background: #ECFDF5; color: #065F46;  border: 1px solid #A7F3D0; }

/* ── Signal chips (card) ──────────────────────── */
.signal-chips { display: flex; gap: 4px; flex-wrap: wrap; padding: 0 14px 10px; }
.chip     { font-size: 10px; background: #F3F4F6; color: #6B7280; padding: 2px 7px; border-radius: 20px; font-weight: 500; }
.chip-red { background: #FEF2F2; color: #EF4444; }
.chip-amb { background: #FFFBEB; color: #92400E; }

/* ── Card action row — connected to card via :has() ── */
.element-container:has(.patient-card) + .element-container [data-testid="stHorizontalBlock"],
.element-container:has(.patient-card) + div [data-testid="stHorizontalBlock"] {
  background: white !important;
  border-right: 1px solid #E5E7EB !important;
  border-bottom: 1px solid #E5E7EB !important;
  border-top: 1px solid #F3F4F6 !important;
  border-radius: 0 0 10px 10px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
  margin-top: -2px !important; margin-bottom: 0 !important;
  overflow: hidden; padding: 0 !important;
}
.element-container:has(.patient-card.urgent) + .element-container [data-testid="stHorizontalBlock"],
.element-container:has(.patient-card.urgent) + div [data-testid="stHorizontalBlock"] { border-left: 4px solid #EF4444 !important; }
.element-container:has(.patient-card.watch) + .element-container [data-testid="stHorizontalBlock"],
.element-container:has(.patient-card.watch) + div [data-testid="stHorizontalBlock"] { border-left: 4px solid #F59E0B !important; }
.element-container:has(.patient-card.routine) + .element-container [data-testid="stHorizontalBlock"],
.element-container:has(.patient-card.routine) + div [data-testid="stHorizontalBlock"] { border-left: 4px solid #10B981 !important; }
.element-container:has(.patient-card.slippage) + .element-container [data-testid="stHorizontalBlock"],
.element-container:has(.patient-card.slippage) + div [data-testid="stHorizontalBlock"] { border-left: 4px solid #F97316 !important; }
.element-container:has(.patient-card.ontrack) + .element-container [data-testid="stHorizontalBlock"],
.element-container:has(.patient-card.ontrack) + div [data-testid="stHorizontalBlock"] { border-left: 4px solid #10B981 !important; }
.element-container:has(.patient-card.queue) + .element-container [data-testid="stHorizontalBlock"],
.element-container:has(.patient-card.queue) + div [data-testid="stHorizontalBlock"] { border-left: 4px solid #6366F1 !important; }

/* Action buttons — text-only */
.element-container:has(.patient-card) + .element-container button,
.element-container:has(.patient-card) + div button {
  background: transparent !important; border: none !important;
  border-radius: 0 !important; box-shadow: none !important;
  min-height: 36px !important; font-size: 12px !important;
  font-weight: 500 !important; color: #6B7280 !important;
  padding: 6px 2px !important; width: 100% !important;
}
.element-container:has(.patient-card) + .element-container button[kind="primary"],
.element-container:has(.patient-card) + div button[kind="primary"] {
  color: #0D9488 !important; font-weight: 600 !important; background: transparent !important;
}
.element-container:has(.patient-card) + .element-container [data-testid="column"]:not(:last-child),
.element-container:has(.patient-card) + div [data-testid="column"]:not(:last-child) {
  border-right: 1px solid #F3F4F6;
}

/* Feedback reason row */
.feedback-row {
  background: #FFFBEB; border: 1px solid #FDE68A;
  border-radius: 0 0 10px 10px; padding: 6px 10px;
  display: flex; gap: 6px; flex-wrap: wrap;
  margin-top: 0; margin-bottom: 12px;
}
.feedback-row-label { font-size: 10px; color: #92400E; font-weight: 600; width: 100%; margin-bottom: 2px; }

/* ── On track / slippage rows ─────────────────── */
.on-track-row {
  background: #ECFDF5; border: 1px solid #A7F3D0;
  border-radius: 8px; padding: 10px 14px;
  display: flex; align-items: center; gap: 10px; margin-bottom: 6px;
}
.on-track-name { font-size: 13px; font-weight: 600; color: #065F46; }
.on-track-sub  { font-size: 11px; color: #047857; margin-top: 2px; }

.slippage-banner {
  background: #FFF7ED; border: 1px solid #FED7AA;
  border-radius: 8px; padding: 10px 14px;
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 6px; font-size: 12px; color: #92400E;
}

/* Reviewed row */
.reviewed-row {
  background: #F9FAFB; border: 1px solid #E5E7EB;
  border-radius: 8px; padding: 8px 14px;
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
  font-size: 12px; color: #6B7280;
}

/* ── Profile page ─────────────────────────────── */
.profile-header {
  background: linear-gradient(135deg, #0D9488 0%, #0F766E 100%);
  border-radius: 12px; padding: 16px 16px 18px; color: white; margin-bottom: 0.8rem;
}
.profile-hero {
  display: flex; align-items: center; gap: 14px;
  background: rgba(255,255,255,0.12); border-radius: 10px; padding: 12px 14px;
  margin-bottom: 12px;
}
.avatar {
  width: 50px; height: 50px; border-radius: 50%;
  background: rgba(255,255,255,0.28);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700; color: white; flex-shrink: 0;
}
.hero-name { font-size: 16px; font-weight: 700; margin-bottom: 3px; }
.hero-meta { font-size: 11px; opacity: 0.85; margin-top: 2px; }
.hero-comorbid { font-size: 10px; opacity: 0.75; margin-top: 3px; font-style: italic; }

/* Profile stat pills */
.profile-stats { display: flex; gap: 8px; flex-wrap: wrap; }
.stat-pill {
  background: rgba(255,255,255,0.15); border-radius: 8px;
  padding: 8px 12px; text-align: center; flex: 1; min-width: 80px;
}
.stat-val { font-size: 16px; font-weight: 700; line-height: 1; }
.stat-lbl { font-size: 10px; opacity: 0.8; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.03em; }
.stat-sub { font-size: 10px; opacity: 0.65; }

/* Signal rows in profile */
.signal-section { margin: 12px 0; }
.signal-section-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: #6B7280; margin-bottom: 8px;
  display: flex; align-items: center; gap: 6px;
}
.profile-signal {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 9px 12px; border-radius: 8px; margin-bottom: 6px;
  border: 1px solid;
}
.profile-signal.clinical { background: #FEF2F2; border-color: #FECACA; }
.profile-signal.behavioral { background: #FFFBEB; border-color: #FDE68A; }
.profile-signal.engagement { background: #FFF7ED; border-color: #FED7AA; }
.signal-dot { font-size: 10px; margin-top: 2px; flex-shrink: 0; }
.signal-main { font-size: 13px; font-weight: 600; color: #111827; }
.signal-detail { font-size: 11px; color: #6B7280; margin-top: 2px; line-height: 1.4; }
.signal-cat {
  margin-left: auto; font-size: 9px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em;
  opacity: 0.6; flex-shrink: 0; padding-top: 3px;
}

/* AI reasoning block */
.reasoning-block {
  background: #F0FDFA; border-left: 4px solid #0D9488;
  border-radius: 0 10px 10px 0; padding: 12px 14px; margin: 12px 0;
}
.reasoning-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: #0D9488; margin-bottom: 6px;
}
.reasoning-text { font-size: 12px; color: #374151; line-height: 1.65; }

/* Today's data rows */
.data-row {
  display: flex; align-items: baseline; padding: 5px 0;
  border-bottom: 1px solid #F9FAFB;
}
.data-label { font-size: 11px; color: #9CA3AF; width: 130px; flex-shrink: 0; }
.data-value { font-size: 13px; font-weight: 600; color: #111827; }
.data-sub   { font-size: 11px; color: #9CA3AF; margin-left: 6px; }
.data-good  { color: #059669; }
.data-warn  { color: #D97706; }
.data-bad   { color: #DC2626; }

/* ── Slippage detail page ─────────────────────── */
.slippage-page-header {
  background: linear-gradient(135deg, #EA580C 0%, #FB923C 100%);
  border-radius: 12px; padding: 18px 20px; color: white; margin-bottom: 1rem;
}
.slippage-page-header h2 { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.slippage-explainer {
  background: rgba(255,255,255,0.15); border-radius: 8px;
  padding: 10px 12px; font-size: 12px; line-height: 1.5;
}
.slip-detail-card {
  background: white; border-radius: 10px;
  border: 1px solid #FED7AA; margin-bottom: 12px; overflow: hidden;
}
.slip-accent { height: 4px; background: linear-gradient(90deg,#F97316,#FCD34D); }
.slip-body { padding: 12px 14px; }
.slip-name { font-size: 14px; font-weight: 700; color: #111827; }
.slip-meta { font-size: 11px; color: #9CA3AF; margin: 3px 0 8px; }
.slip-reason { font-size: 12px; color: #374151; line-height: 1.5; margin-bottom: 10px; }
.risk-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.risk-chip { font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 20px; border: 1px solid; }
.risk-chip.orange { background: #FFEDD5; color: #EA580C; border-color: #FED7AA; }
.risk-chip.yellow { background: #FEF9C3; color: #713F12; border-color: #FEF08A; }

/* ── Coach Notes page ─────────────────────────── */
.notes-header {
  background: #0D9488; border-radius: 12px;
  padding: 18px 20px; color: white; margin-bottom: 1rem;
}
.notes-header h2 { font-size: 18px; font-weight: 700; }
.patient-strip-notes {
  background: rgba(255,255,255,0.15); border-radius: 8px;
  padding: 10px 12px; display: flex; align-items: center; gap: 10px; margin-top: 10px;
}
.avatar-sm {
  width: 36px; height: 36px; border-radius: 50%;
  background: rgba(255,255,255,0.25);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: white;
}
.ps-name { font-size: 14px; font-weight: 700; }
.ps-meta { font-size: 11px; opacity: 0.8; }

/* Note history */
.note-item { padding: 12px 0; border-bottom: 1px solid #F3F4F6; }
.note-tag { display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 20px; margin-right: 6px; }
.tag-called    { background: #EFF6FF; color: #1E40AF; }
.tag-messaged  { background: #F5F3FF; color: #5B21B6; }
.tag-video     { background: #ECFDF5; color: #065F46; }
.tag-escalated { background: #FEF2F2; color: #EF4444; }
.note-date { font-size: 11px; color: #9CA3AF; }
.note-text { font-size: 12px; color: #374151; line-height: 1.55; margin-top: 4px; }
.note-signals  { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px; }
.ns-chip { font-size: 10px; background: #F3F4F6; color: #9CA3AF; padding: 1px 6px; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)


# ── Protocol + threshold cache ────────────────────────────────
@st.cache_resource
def load_protocol():
    return load_protocol_files()

@st.cache_resource
def get_thresholds():
    return load_thresholds()


# ── Session state ─────────────────────────────────────────────
defaults = {
    "results": None,
    "data_loaded": False,
    "demo_mode": False,
    "uploaded_file": None,
    "selected_patient": None,
    "view": "brief",
    "show_wrong": {},
    "show_cooling": {},
    "show_note": {},
    "show_feedback": {},    # note_key → True when 👎 tapped, shows reason chips
    "reviewed_patients": set(),  # patients marked done; filtered from active sections
    "coach_notes": [],
    "snooze_set": set(),
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
        st.session_state.view = "brief"

    if st.session_state.demo_mode and st.session_state.data_loaded:
        try:
            n = len(load_patients("data/sample_patients.json"))
            st.success(f"✓ {n} sample patients loaded")
        except Exception:
            st.success("✓ Sample patients loaded")

    uploaded = st.file_uploader("Or upload CSV / JSON", type=["csv", "json"])
    if uploaded:
        st.session_state.demo_mode = False
        st.session_state.uploaded_file = uploaded
        st.session_state.data_loaded = True
        st.session_state.results = None
        st.session_state.selected_patient = None
        st.session_state.view = "brief"
        st.success(f"✓ {uploaded.name} uploaded")

    st.divider()
    st.markdown("**Step 2 — Run analysis**")
    run_clicked = st.button(
        "▶ Run reasoning loop", type="primary", use_container_width=True,
        disabled=not st.session_state.data_loaded,
        help="Load patient data first" if not st.session_state.data_loaded else ""
    )
    if st.button("⚡ Load demo results", use_container_width=True,
                 help="Replay frozen output — no API call"):
        try:
            with open("frozen_output.json") as _f:
                _frozen = json.load(_f)
            st.session_state.results = _frozen
            st.session_state.data_loaded = True
            st.session_state.demo_mode = True
            st.session_state.view = "brief"
            st.session_state.selected_patient = None
            with open("data/sample_patients.json") as _f:
                _raw = json.load(_f)
            st.session_state["raw_patients"] = {
                p["name"]: p for p in _raw.get("patients", [])
            }
            st.rerun()
        except Exception as _e:
            st.error(f"Could not load frozen output: {_e}")
    if not st.session_state.data_loaded:
        st.caption("⬆ Load patient data first")
    st.caption("⚡ Use demo results for UI testing — saves API costs")

    st.divider()
    if st.session_state.results:
        st.markdown("**Navigate**")
        if st.button("🏠 Morning Brief", use_container_width=True):
            st.session_state.view = "brief"
            st.session_state.selected_patient = None
            st.rerun()
        if st.button("📋 Coach Notes", use_container_width=True):
            st.session_state.view = "notes"
            st.rerun()
        st.divider()

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
        f.seek(0)
        suffix = ".csv" if f.name.endswith(".csv") else ".json"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(f.read())
            filepath = tmp.name

    with st.status("Running MadhuMitra analysis...", expanded=True) as status:
        st.write("📋 Parsing patient logs...")
        parse_results = parse_all(filepath)
        rules  = len(parse_results["rules_alerted"])
        to_llm = len(parse_results["send_to_llm"])
        on_trk = len(parse_results["on_track"])
        st.write(f"✓ {rules} patients flagged by rules (no AI needed)")
        st.write(f"✓ {on_trk} patients on track (skipping AI)")
        st.write(f"🧠 Sending {to_llm} patients to AI reasoning loop...")

        llm_results = run_reasoning(
            parse_results["send_to_llm"],
            alert_guide, thresholds, guardrails, output_schema
        )
        st.write("📊 Ranking results by priority...")
        final = run_ranker(parse_results, llm_results, thresholds_data)
        st.session_state.results = final
        st.session_state.selected_patient = None
        st.session_state.view = "brief"

        raw_patients = {}
        if filepath and filepath.endswith(".json"):
            try:
                with open(filepath) as f:
                    raw_data = json.load(f)
                for p in raw_data.get("patients", []):
                    raw_patients[p["name"]] = p
            except Exception:
                pass
        st.session_state["raw_patients"] = raw_patients

        total_alerts = len(final["auto_list"]) + len(final["queue_list"])
        status.update(label=f"✓ Analysis complete — {total_alerts} alerts generated", state="complete")


# ── Helpers ───────────────────────────────────────────────────
SEV_LABEL = {"High": "Urgent", "Medium": "Watch", "Low": "Routine", "On Track": "On Track"}
SEV_CSS   = {"High": "urgent", "Medium": "watch", "Low": "routine", "On Track": "ontrack"}

def sev_label(s): return SEV_LABEL.get(s, s)
def sev_css(s):   return SEV_CSS.get(s, "queue")

TIER1_KW = ["foamy", "blurry", "chest", "dizziness", "dizzy", "swelling", "numbness", "tingling"]
HIGH_KW  = ["medication missed", "above high threshold", "missed log", "consecutive missed",
            "bp 1", "above 200", "escalat"]

def truncate_words(text, max_chars=160):
    if not text or len(text) <= max_chars:
        return text or ""
    cut = text.rfind(" ", 0, max_chars)
    return text[:(cut if cut > 0 else max_chars)] + "…"

def shorten_signal(s):
    sl = s.lower().strip()
    if "fbs" in sl or "fasting glucose" in sl or "fasting blood" in sl:
        m = re.search(r"(\d+\.?\d*)\s*mg", s)
        return f"FBS {m.group(1)} mg/dL" if m else "High glucose"
    if "blood pressure" in sl or " bp " in sl or "systolic" in sl or "hypertension" in sl:
        m = re.search(r"(\d{2,3})/(\d{2,3})", s)
        if m: return f"BP {m.group(1)}/{m.group(2)}"
        m = re.search(r"(\d{3})", s)
        return f"BP {m.group(1)} mmHg" if m else "High BP"
    if "medication" in sl and any(k in sl for k in ["miss", "not taken", "false", "skip"]):
        return "Medication missed"
    if "exercise" in sl:
        if any(k in sl for k in ["0 min", "no exercise", "zero", ": 0", "= 0"]): return "Exercise 0 min"
        m = re.search(r"(\d+)\s*min", sl)
        return f"Exercise {m.group(1)} min" if m else "No exercise"
    if "sleep" in sl:
        m = re.search(r"(\d+\.?\d*)\s*h", sl)
        return f"Sleep {m.group(1)}h" if m else "Low sleep"
    if "stress" in sl:
        m = re.search(r"(\d)\s*/\s*5", sl)
        return f"Stress {m.group(1)}/5" if m else "High stress"
    if "missed log" in sl or ("log" in sl and "miss" in sl):
        m = re.search(r"(\d+)\s*(?:consecutive|day)", sl)
        return f"{m.group(1)} missed logs" if m else "Missed log"
    for kw, label in [("foamy","Foamy urine"),("blurry","Blurry vision"),
                       ("chest","Chest pain"),("dizz","Dizziness"),
                       ("numb","Numbness"),("swelling","Swelling"),("escalat","Escalate to doctor")]:
        if kw in sl: return label
    if "carb" in sl:
        m = re.search(r"(\d+)g", sl)
        return f"Carbs {m.group(1)}g" if m else "High carbs"
    if "protein" in sl:
        m = re.search(r"(\d+)g", sl)
        return f"Protein {m.group(1)}g" if m else "Low protein"
    words = s.strip().split()
    short = " ".join(words[:4])
    return short[:26] + ("…" if len(short) > 26 else "")

def make_chip_html(signals, max_chips=5):
    html = ""
    for s in signals[:max_chips]:
        sl = s.lower()
        label = shorten_signal(s)
        cls = "chip chip-red" if (any(k in sl for k in TIER1_KW) or any(k in sl for k in HIGH_KW)) else "chip chip-amb"
        html += f'<span class="{cls}">{label}</span>'
    if len(signals) > max_chips:
        html += f'<span class="chip">+{len(signals)-max_chips} more</span>'
    return html

def get_contact_days(name):
    raw = st.session_state.get("raw_patients", {}).get(name, {})
    return raw.get("contact", {}).get("days_since_contact")

def _save_note(name, action_type, note_text, tags):
    st.session_state.coach_notes.append({
        "patient_name": name, "action_type": action_type,
        "note_text": note_text, "tags": tags,
        "created_at": datetime.now().strftime("%b %d, %Y · %I:%M %p")
    })

SAFE_MODIFIERS = ["stable","well controlled","no concern","on target","improvement",
                  "improving","within range","good","normal","not concern","controlled"]

def _categorize_signal(sig):
    sl = sig.lower()
    # If a clinical keyword is present but the signal is qualified as safe, treat as engagement
    has_clinical_kw = any(k in sl for k in ["fbs","glucose","bp","blood pressure","medication","chest","blurry","foamy","escalat","vision"])
    is_safe = any(m in sl for m in SAFE_MODIFIERS)
    if has_clinical_kw and not is_safe:
        return "clinical", "#FEF2F2", "#FECACA", "#DC2626", "🔴"
    elif any(k in sl for k in ["exercise","sleep","stress","carb","protein","food","diet"]):
        return "behavioral", "#FFFBEB", "#FDE68A", "#D97706", "🟡"
    else:
        return "engagement", "#FFF7ED", "#FED7AA", "#EA580C", "🟠"


# ── Inline note form ──────────────────────────────────────────
def render_inline_note(name, note_key):
    st.markdown(
        '<div style="background:#F0FDFA;border:1px solid #99F6E4;border-radius:8px;padding:12px 14px;margin-bottom:12px;">',
        unsafe_allow_html=True
    )
    action_types = {"📞 Called": "called", "💬 Messaged": "messaged",
                    "🎥 Video": "video", "🚨 Escalated": "escalated"}
    sel_type = st.radio("Action type", list(action_types.keys()),
                        horizontal=True, key=f"atype_{note_key}")
    note_text = st.text_area("Note", placeholder="What did you discuss or observe?",
                              key=f"ntext_{note_key}", height=90, label_visibility="collapsed")
    focus_opts = ["Medication", "Food guidance", "Exercise", "Stress", "BP", "Escalation"]
    selected_tags = st.multiselect("Focus", focus_opts, key=f"ntags_{note_key}")
    n1, n2 = st.columns(2)
    with n1:
        if st.button("✓ Save Note", key=f"nsave_{note_key}", type="primary", use_container_width=True):
            if note_text.strip():
                _save_note(name, action_types[sel_type], note_text.strip(), selected_tags)
                st.session_state.show_note[note_key] = False
                st.toast(f"✓ Note saved for {name}")
                st.rerun()
            else:
                st.warning("Please enter a note before saving.")
    with n2:
        if st.button("Cancel", key=f"ncancel_{note_key}", use_container_width=True):
            st.session_state.show_note[note_key] = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ── Patient card (morning brief) ──────────────────────────────
def render_patient_card(patient, idx, section):
    name     = patient.get("name", "")
    severity = patient.get("severity", "")
    label    = sev_label(severity)
    css      = sev_css(severity)
    signals  = patient.get("signals", []) or [d.replace("_", " ") for d in patient.get("deviations", [])]
    reasoning = patient.get("reasoning", "") or patient.get("rules_reasoning", "")
    raw       = st.session_state.get("raw_patients", {}).get(name, {})
    h         = raw.get("program_history", patient.get("program_history", {}))
    week      = h.get("week_number", "?")
    days      = get_contact_days(name)
    note_key  = f"{section}_{idx}"

    reason_short = reasoning or ""
    contact_tag  = f'<span class="meta-tag">· Last contact: {days}d ago</span>' if days is not None else ""

    st.markdown(f"""
<div class="patient-card {css}">
  <div class="card-top">
    <div class="card-row1">
      <div class="patient-name">{name}</div>
      <span class="severity-badge badge-{css}">{label}</span>
    </div>
    <div class="flag-reason">{reason_short}</div>
    <div class="meta-row">
      <span class="meta-tag">Week {week}</span>
      {contact_tag}
    </div>
  </div>
  <div class="signal-chips">{make_chip_html(signals)}</div>
</div>""", unsafe_allow_html=True)

    # 4-button action row: View Profile | Add Note | 👍 | 👎
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("View Profile", key=f"view_{section}_{idx}",
                     use_container_width=True, type="primary"):
            st.session_state.selected_patient = name
            st.session_state.view = "profile"
            st.rerun()
    with c2:
        if st.button("Add Note", key=f"note_{section}_{idx}", use_container_width=True):
            st.session_state.show_note[note_key] = not st.session_state.show_note.get(note_key, False)
            st.session_state.show_feedback[note_key] = False
            st.rerun()
    with c3:
        if st.button("👍 Correct", key=f"up_{section}_{idx}", use_container_width=True):
            record_feedback(name, severity, patient.get("track", "auto"), signals, reasoning, "correct")
            st.session_state.reviewed_patients.add(name)
            st.toast(f"👍 {name} — marked correct, moved to reviewed")
            st.rerun()
    with c4:
        if st.button("👎 Wrong", key=f"dn_{section}_{idx}", use_container_width=True):
            st.session_state.show_feedback[note_key] = not st.session_state.show_feedback.get(note_key, False)
            st.session_state.show_note[note_key] = False
            st.rerun()

    # Inline: wrong-alert reason chips
    if st.session_state.show_feedback.get(note_key):
        st.markdown(
            '<div class="feedback-row">'
            '<div class="feedback-row-label">👎 Why was this wrong? (tap to submit)</div>',
            unsafe_allow_html=True
        )
        reasons = ["False positive", "Severity too high", "Already handled", "Low priority"]
        fb_cols = st.columns(len(reasons))
        for i, (col, reason) in enumerate(zip(fb_cols, reasons)):
            with col:
                if st.button(reason, key=f"fbr_{note_key}_{i}", use_container_width=True):
                    record_feedback(name, severity, patient.get("track", "auto"),
                                    signals, reasoning, "incorrect", reason)
                    st.session_state.reviewed_patients.add(name)
                    st.session_state.show_feedback[note_key] = False
                    st.toast(f"👎 Feedback saved — {reason}")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Inline: note form
    if st.session_state.show_note.get(note_key):
        render_inline_note(name, note_key)

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)


# ── Slippage card (morning brief) ─────────────────────────────
def render_slippage_card(patient, idx):
    name      = patient.get("name", "")
    severity  = patient.get("severity", "")
    reasoning = patient.get("reasoning", "")
    raw       = st.session_state.get("raw_patients", {}).get(name, {})
    h         = raw.get("program_history", patient.get("program_history", {}))
    week      = h.get("week_number", "?")
    days      = get_contact_days(name)
    signals   = patient.get("signals", [])
    note_key  = f"slip_{idx}"

    reason_short = reasoning or ""
    contact_tag  = f'<span class="meta-tag">· Last contact: {days}d ago</span>' if days is not None else ""

    st.markdown(f"""
<div class="patient-card slippage">
  <div class="card-top">
    <div class="card-row1">
      <div class="patient-name">{name}</div>
      <span class="severity-badge badge-slippage">Slippage</span>
    </div>
    <div class="flag-reason">{reason_short}</div>
    <div class="meta-row">
      <span class="meta-tag">Week {week}</span>
      {contact_tag}
    </div>
  </div>
  <div class="signal-chips">{make_chip_html(signals)}</div>
</div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("View Profile", key=f"view_slip_{idx}",
                     use_container_width=True, type="primary"):
            st.session_state.selected_patient = name
            st.session_state.view = "profile"
            st.rerun()
    with c2:
        if st.button("Add Note", key=f"note_slip_{idx}", use_container_width=True):
            st.session_state.show_note[note_key] = not st.session_state.show_note.get(note_key, False)
            st.session_state.show_feedback[note_key] = False
            st.rerun()
    with c3:
        if st.button("👍 Correct", key=f"up_slip_{idx}", use_container_width=True):
            record_feedback(name, severity, "on_track", signals, reasoning, "correct")
            st.session_state.reviewed_patients.add(name)
            st.toast(f"👍 {name} — marked correct")
            st.rerun()
    with c4:
        if st.button("👎 Wrong", key=f"dn_slip_{idx}", use_container_width=True):
            st.session_state.show_feedback[note_key] = not st.session_state.show_feedback.get(note_key, False)
            st.session_state.show_note[note_key] = False
            st.rerun()

    if st.session_state.show_feedback.get(note_key):
        st.markdown('<div class="feedback-row"><div class="feedback-row-label">👎 Why was this wrong?</div>', unsafe_allow_html=True)
        reasons = ["False positive", "Not slippage", "Already handled", "Low priority"]
        fb_cols = st.columns(len(reasons))
        for i, (col, reason) in enumerate(zip(fb_cols, reasons)):
            with col:
                if st.button(reason, key=f"sfbr_{note_key}_{i}", use_container_width=True):
                    record_feedback(name, severity, "on_track", signals, reasoning, "incorrect", reason)
                    st.session_state.reviewed_patients.add(name)
                    st.session_state.show_feedback[note_key] = False
                    st.toast(f"👎 Feedback saved")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.show_note.get(note_key):
        render_inline_note(name, note_key)

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)


# ── Patient Profile — redesigned ──────────────────────────────
def render_patient_profile():
    name = st.session_state.selected_patient
    r    = st.session_state.results

    all_p   = r["auto_list"] + r["queue_list"] + r["nudge_list"] + r["on_track"]
    patient = next((p for p in all_p if p.get("name") == name), None)
    if not patient:
        st.error("Patient not found")
        if st.button("← Back"):
            st.session_state.view = "brief"
            st.rerun()
        return

    raw  = st.session_state.get("raw_patients", {}).get(name, {})
    s    = raw.get("structured", patient.get("structured", {}))
    h    = raw.get("program_history", patient.get("program_history", {}))
    u    = raw.get("unstructured", patient.get("unstructured", {}))

    severity = patient.get("severity", "")
    label    = sev_label(severity)
    css      = sev_css(severity)
    avatar   = name.split()[0][0].upper()
    age      = raw.get("age") or patient.get("age", "—")
    gender   = raw.get("gender") or patient.get("gender", "—")
    week     = h.get("week_number", "?")
    phase    = h.get("phase", "")

    comorbidities = [k.replace("_", " ") for k, v in h.get("comorbidities", {}).items() if v is True]
    comorbid_str  = ", ".join(comorbidities) if comorbidities else "No comorbidities"

    escalate           = patient.get("escalate_to_doctor", False)
    escalation_reasons = patient.get("escalation_reasons", [])
    signals            = patient.get("signals", []) or [d.replace("_", " ") for d in patient.get("deviations", [])]
    reasoning          = patient.get("reasoning", "") or patient.get("rules_reasoning", "")
    targets            = h.get("clinical_targets", {})

    # Key vitals for header pills
    fbs       = s.get("fbs_mgdl")
    bp_sys    = s.get("blood_pressure_systolic")
    bp_dia    = s.get("blood_pressure_diastolic")
    med_taken = s.get("medication_taken")

    fbs_txt  = f"{fbs}" if fbs else "—"
    bp_txt   = f"{bp_sys}/{bp_dia}" if bp_sys else "—"
    med_txt  = "✓ Taken" if med_taken else ("✗ Missed" if med_taken is False else "—")
    med_color = "" if med_taken else ("color:#DC2626" if med_taken is False else "")

    phase_txt = f"Phase {phase}" if phase else ""

    st.markdown(f"""
<div class="profile-header">
  <div class="profile-hero">
    <div class="avatar">{avatar}</div>
    <div style="flex:1;">
      <div class="hero-name">
        {name}
        <span class="severity-badge badge-{css}" style="font-size:9px;vertical-align:middle;margin-left:6px;">{label}</span>
      </div>
      <div class="hero-meta">Age {age} · {gender} · Week {week} {phase_txt}</div>
      <div class="hero-comorbid">{comorbid_str}</div>
    </div>
  </div>
  <div class="profile-stats">
    <div class="stat-pill">
      <div class="stat-val">{fbs_txt}</div>
      <div class="stat-lbl">FBS mg/dL</div>
    </div>
    <div class="stat-pill">
      <div class="stat-val">{bp_txt}</div>
      <div class="stat-lbl">BP mmHg</div>
    </div>
    <div class="stat-pill">
      <div class="stat-val" style="{med_color}">{med_txt}</div>
      <div class="stat-lbl">Medication</div>
    </div>
    <div class="stat-pill">
      <div class="stat-val">{s.get('exercise_minutes','—')}</div>
      <div class="stat-lbl">Exercise min</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    pb1, pb2 = st.columns(2)
    with pb1:
        if st.button("← Morning Brief", use_container_width=True):
            st.session_state.view = "brief"
            st.session_state.selected_patient = None
            st.rerun()
    with pb2:
        if st.button("📋 Add Note", use_container_width=True, type="primary"):
            st.session_state.selected_patient = name
            st.session_state.view = "notes"
            st.rerun()

    # ── Alert banner ──────────────────────────────────────────
    if escalate:
        st.error(f"🚨 **Doctor escalation required** — {', '.join(escalation_reasons)}")
    elif severity == "High":
        st.error("🔴 **Urgent** — Same-day coach contact required")
    elif severity == "Medium":
        st.warning("🟡 **Watch** — Contact within 24 hours")

    contact_status = get_contact_status(name)
    if contact_status:
        days_c    = contact_status["days_since_contact"]
        remaining = contact_status["days_remaining"]
        st.info(f"📞 Contacted {days_c}d ago · Cooling expires in {remaining}d")

    # ── Why this alert was raised ─────────────────────────────
    if signals:
        # Group by category
        clinical, behavioral, engagement = [], [], []
        for sig in signals[:10]:
            cat, *_ = _categorize_signal(sig)
            if cat == "clinical":    clinical.append(sig)
            elif cat == "behavioral": behavioral.append(sig)
            else:                     engagement.append(sig)

        def _signal_rows(sigs):
            html = ""
            for sig in sigs:
                cat, bg, border, txtcolor, dot = _categorize_signal(sig)
                short = shorten_signal(sig)
                # Show shortened as the headline, full text as detail
                detail = sig if sig != short and len(sig) < 200 else ""
                html += f"""
<div class="profile-signal {cat}">
  <div class="signal-dot" style="color:{txtcolor};">{dot}</div>
  <div>
    <div class="signal-main" style="color:{txtcolor};">{short}</div>
    {"<div class='signal-detail'>" + detail + "</div>" if detail else ""}
  </div>
  <div class="signal-cat">{cat}</div>
</div>"""
            return html

        st.markdown('<div class="signal-section">'
                    '<div class="signal-section-title">🚨 Why this alert was raised</div>',
                    unsafe_allow_html=True)

        if clinical:
            st.markdown(
                '<div style="font-size:10px;font-weight:700;color:#DC2626;text-transform:uppercase;'
                'letter-spacing:0.05em;margin-bottom:4px;">Clinical signals</div>'
                + _signal_rows(clinical), unsafe_allow_html=True)
        if behavioral:
            st.markdown(
                '<div style="font-size:10px;font-weight:700;color:#D97706;text-transform:uppercase;'
                'letter-spacing:0.05em;margin-top:8px;margin-bottom:4px;">Behavioral signals</div>'
                + _signal_rows(behavioral), unsafe_allow_html=True)
        if engagement:
            st.markdown(
                '<div style="font-size:10px;font-weight:700;color:#EA580C;text-transform:uppercase;'
                'letter-spacing:0.05em;margin-top:8px;margin-bottom:4px;">Engagement signals</div>'
                + _signal_rows(engagement), unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── AI reasoning block ────────────────────────────────────
    if reasoning:
        st.markdown(f"""
<div class="reasoning-block">
  <div class="reasoning-label">🧠 AI Assessment</div>
  <div class="reasoning-text">{reasoning}</div>
</div>""", unsafe_allow_html=True)

    # ── Today's data ──────────────────────────────────────────
    t_fbs = targets.get("fbs_target_mgdl")

    def _val_color(val, target, lower_is_better=True):
        if not val or not target: return ""
        return "data-good" if (val <= target if lower_is_better else val >= target) else "data-bad"

    med_str = "✓ Taken" if med_taken else ("✗ Missed" if med_taken is False else "—")
    med_cls = "data-good" if med_taken else ("data-bad" if med_taken is False else "")

    with st.expander("📊 Today's full data", expanded=False):
        rows = [
            ("Fasting Glucose", f"{fbs or '—'} mg/dL", f"target {t_fbs}" if t_fbs else "",
             _val_color(fbs, t_fbs) if fbs and t_fbs else ""),
            ("Blood Pressure", f"{bp_txt} mmHg", "target <130/80", ""),
            ("Medication", med_str, "", med_cls),
            ("Exercise", f"{s.get('exercise_minutes','—')} min", "target 30 min",
             _val_color(s.get('exercise_minutes'), 30, lower_is_better=False)),
            ("Sleep", f"{s.get('sleep_hours','—')} hrs", s.get("sleep_quality","") or "", ""),
            ("Stress", f"{s.get('stress_score','—')}/5", "", ""),
            ("Protein", f"{s.get('protein_g','—')}g", f"target {h.get('protein_target_g','—')}g", ""),
            ("Carbs", f"{s.get('carbs_g','—')}g", f"target {h.get('carb_target_g','—')}g", ""),
        ]
        for label_d, val, sub, cls in rows:
            st.markdown(f"""
<div class="data-row">
  <div class="data-label">{label_d}</div>
  <div class="data-value {cls}">{val}</div>
  <div class="data-sub">{sub}</div>
</div>""", unsafe_allow_html=True)
        if u.get("free_text"):
            st.markdown(f'<div style="margin-top:10px;font-size:12px;color:#6B7280;font-style:italic;">💬 &ldquo;{u["free_text"]}&rdquo;</div>', unsafe_allow_html=True)
        if u.get("coach_notes"):
            st.markdown(f'<div style="margin-top:6px;font-size:12px;color:#374151;">📋 {u["coach_notes"]}</div>', unsafe_allow_html=True)

    st.divider()

    # ── Coach actions ─────────────────────────────────────────
    st.markdown("**⚡ Coach actions**")
    ca1, ca2 = st.columns(2)
    with ca1:
        if st.button("👍 Correct alert", use_container_width=True, key=f"prof_up_{name}"):
            record_feedback(name, severity, patient.get("track", "auto"), signals, reasoning, "correct")
            st.session_state.reviewed_patients.add(name)
            st.success("✓ Feedback saved")
            st.rerun()
    with ca2:
        if st.button("👎 Wrong alert", use_container_width=True, key=f"prof_dn_{name}"):
            st.session_state.show_wrong[name] = True
            st.rerun()

    if st.session_state.show_wrong.get(name):
        wr = st.selectbox("Why wrong?",
            ["Select…", "Not urgent / false positive", "Severity too high",
             "Severity too low", "Patient already handled", "Other"],
            key=f"prof_wr_{name}")
        if wr != "Select…":
            if st.button("Submit feedback", key=f"prof_wrsub_{name}", use_container_width=True):
                record_feedback(name, severity, patient.get("track", "auto"),
                                signals, reasoning, "incorrect", wr)
                st.session_state.show_wrong[name] = False
                st.session_state.reviewed_patients.add(name)
                st.rerun()

    if not contact_status:
        if st.button("📞 Mark Contacted", use_container_width=True, key=f"prof_con_{name}"):
            st.session_state.show_cooling[name] = True
            st.rerun()
        if st.session_state.show_cooling.get(name):
            cooling = st.selectbox("Cooling period",
                ["Urgent — 1 day", "Watch — 2 days", "Routine — 3 days"],
                key=f"prof_cl_{name}")
            level = cooling.split(" ")[0]
            if st.button("Confirm", key=f"prof_clconf_{name}", use_container_width=True):
                mark_contacted(name, severity, level, signals)
                st.session_state.show_cooling[name] = False
                st.rerun()
    else:
        ce1, ce2 = st.columns(2)
        with ce1:
            extra = st.number_input("Extend (days)", 1, 7, 1, key=f"ext_{name}")
            if st.button("Extend cooling", key=f"extb_{name}", use_container_width=True):
                extend_cooling(name, extra)
                st.rerun()
        with ce2:
            if st.button("Override → re-alert", key=f"ov_{name}", use_container_width=True):
                mark_contacted(name, severity, "Urgent", signals)
                st.rerun()

    # ── Previous notes ────────────────────────────────────────
    patient_notes = [n for n in st.session_state.coach_notes if n["patient_name"] == name]
    if patient_notes:
        st.divider()
        st.markdown(f"**📋 Notes history** ({len(patient_notes)})")
        TAG_CSS = {"called":"tag-called","messaged":"tag-messaged","video":"tag-video","escalated":"tag-escalated"}
        for note in reversed(patient_notes):
            tag_css   = TAG_CSS.get(note.get("action_type",""), "tag-called")
            tag_label = note.get("action_type","Note").capitalize()
            tags_html = "".join(f'<span class="ns-chip">{t}</span>' for t in note.get("tags",[]))
            st.markdown(f"""
<div class="note-item">
  <div><span class="note-tag {tag_css}">{tag_label}</span><span class="note-date">{note.get('created_at','')}</span></div>
  <div class="note-text">{note.get('note_text','')}</div>
  <div class="note-signals">{tags_html}</div>
</div>""", unsafe_allow_html=True)


# ── Coach Notes page ──────────────────────────────────────────
def render_coach_notes():
    if st.button("← Morning Brief", use_container_width=False):
        st.session_state.view = "brief"
        st.rerun()

    r = st.session_state.results
    all_patients = sorted(set(
        p.get("name","") for p in
        r["auto_list"] + r["queue_list"] + r["nudge_list"] + r["on_track"]
    )) if r else []

    pre_selected = st.session_state.selected_patient
    default_idx  = all_patients.index(pre_selected) if pre_selected in all_patients else 0
    selected_name = st.selectbox("Patient", all_patients, index=default_idx,
                                  key="notes_patient_sel") if all_patients else None

    if selected_name:
        raw  = st.session_state.get("raw_patients", {}).get(selected_name, {})
        h    = raw.get("program_history", {})
        s    = raw.get("structured", {})
        week = h.get("week_number","?")
        fbs  = s.get("fbs_mgdl","")
        fbs_txt  = f"FBS {fbs} mg/dL · " if fbs else ""
        initials = "".join(w[0].upper() for w in selected_name.split()[:2])
        st.markdown(f"""
<div class="notes-header">
  <h2>📋 Coach Note</h2>
  <div class="patient-strip-notes">
    <div class="avatar-sm">{initials}</div>
    <div>
      <div class="ps-name">{selected_name}</div>
      <div class="ps-meta">Week {week} · {fbs_txt}Program active</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("**Log an intervention**")
    action_map = {"📞 Called":"called","💬 Messaged":"messaged","🎥 Video call":"video","🚨 Escalated":"escalated"}
    sel_action = st.radio("Action type", list(action_map.keys()), horizontal=True, key="notes_action")
    note_text  = st.text_area("Note", placeholder="e.g. Called patient — discussed medication adherence...",
                               height=120, key="notes_text")
    st.caption(f"{len(note_text)}/500 characters")

    focus_opts    = ["Medication","Food guidance","Exercise","Stress management","BP monitoring","Doctor escalation","Onboarding"]
    selected_tags = st.multiselect("Intervention focus", focus_opts, key="notes_tags")
    outcome       = st.selectbox("Outcome", [
        "Patient receptive — agreed to action","No answer — left voicemail",
        "Patient acknowledged — no commitment","Escalated to doctor","Referral made",
    ], key="notes_outcome")
    followup = st.date_input("Follow-up reminder (optional)", value=None, key="notes_followup")

    s1, s2 = st.columns(2)
    with s1:
        if st.button("Cancel", use_container_width=True, key="notes_cancel"):
            st.session_state.view = "brief"
            st.rerun()
    with s2:
        if st.button("✓ Save Note", use_container_width=True, type="primary", key="notes_save"):
            if note_text.strip() and selected_name:
                _save_note(selected_name, action_map[sel_action], note_text.strip(), selected_tags)
                st.success(f"✓ Note saved for {selected_name}" + (f" · Follow-up: {followup}" if followup else ""))
                st.session_state.view = "brief"
                st.rerun()
            else:
                st.warning("Please enter a note.")

    patient_notes = [n for n in st.session_state.coach_notes if n.get("patient_name") == selected_name]
    if patient_notes:
        st.divider()
        st.markdown(f"**Previous notes — {selected_name}** ({len(patient_notes)} total)")
        TAG_CSS = {"called":"tag-called","messaged":"tag-messaged","video":"tag-video","escalated":"tag-escalated"}
        for note in reversed(patient_notes):
            tag_css   = TAG_CSS.get(note.get("action_type",""), "tag-called")
            tag_label = note.get("action_type","Note").capitalize()
            tags_html = "".join(f'<span class="ns-chip">{t}</span>' for t in note.get("tags",[]))
            st.markdown(f"""
<div class="note-item">
  <div><span class="note-tag {tag_css}">{tag_label}</span><span class="note-date">{note.get('created_at','')}</span></div>
  <div class="note-text">{note.get('note_text','')}</div>
  <div class="note-signals">{tags_html}</div>
</div>""", unsafe_allow_html=True)
    elif selected_name:
        st.caption("No notes yet for this patient.")


# ── Slippage Alerts page ──────────────────────────────────────
def render_slippage_page(r):
    nudge_raw = r["nudge_list"] + [p for p in r["auto_list"] if p.get("severity") == "Low" and p.get("nudge_risk")]
    seen, slippage = set(), []
    for p in nudge_raw:
        if p.get("name") not in seen:
            slippage.append(p); seen.add(p.get("name"))

    if st.button("← Morning Brief", use_container_width=False):
        st.session_state.view = "brief"
        st.rerun()

    st.markdown(f"""
<div class="slippage-page-header">
  <h2>⚠️ Slippage Alerts</h2>
  <div class="slippage-explainer">
    <strong>Engagement risk, not clinical emergency.</strong>
    These patients show patterns like declining log frequency, missed entries, or motivation drop.
    They need a warm check-in — not urgent clinical action.
  </div>
</div>""", unsafe_allow_html=True)

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Patients at Risk", len(slippage))
    mc2.metric("On Track", len(r["on_track"]))
    mc3.metric("Notes Today", sum(1 for n in st.session_state.coach_notes
                                  if n.get("created_at","").startswith(datetime.now().strftime("%b %d"))))

    if not slippage:
        st.success("✅ No slippage alerts right now.")
        return

    st.divider()
    for i, p in enumerate(slippage):
        name      = p.get("name","")
        reasoning = p.get("reasoning","")
        h         = p.get("program_history",{})
        week      = h.get("week_number","?")
        signals   = p.get("signals",[])
        raw       = st.session_state.get("raw_patients",{}).get(name,{})
        age       = raw.get("age",""); gender = raw.get("gender","")
        snoozed   = name in st.session_state.snooze_set

        if snoozed:
            st.markdown(f"""
<div class="on-track-row">
  <span style="font-size:16px">😴</span>
  <div><div class="on-track-name">{name}</div><div class="on-track-sub">Snoozed — alert paused</div></div>
</div>""", unsafe_allow_html=True)
            continue

        reason_short = reasoning or "No engagement signal captured"
        meta_parts   = [x for x in [f"Age {age}" if age else "", gender, f"Week {week}"] if x]
        risk_chips   = "".join(f'<span class="risk-chip orange">{shorten_signal(s)}</span>' for s in signals[:4]) \
                       or '<span class="risk-chip yellow">Low engagement signals</span>'

        st.markdown(f"""
<div class="slip-detail-card">
  <div class="slip-accent"></div>
  <div class="slip-body">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
      <span class="slip-name">{name}</span>
      <span class="severity-badge badge-slippage">Slippage</span>
    </div>
    <div class="slip-meta">{" · ".join(meta_parts)}</div>
    <div class="slip-reason">{reason_short}</div>
    <div class="risk-chips">{risk_chips}</div>
  </div>
</div>""", unsafe_allow_html=True)

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            if st.button("📞 Check In", key=f"slip_ci_{i}", use_container_width=True, type="primary"):
                st.session_state.selected_patient = name; st.session_state.view = "notes"; st.rerun()
        with sc2:
            if st.button("View Profile", key=f"slip_pr_{i}", use_container_width=True):
                st.session_state.selected_patient = name; st.session_state.view = "profile"; st.rerun()
        with sc3:
            if st.button("😴 Snooze", key=f"slip_sn_{i}", use_container_width=True):
                st.session_state.snooze_set.add(name); st.toast(f"😴 {name} snoozed"); st.rerun()


# ── Morning brief ─────────────────────────────────────────────
def render_morning_brief(r):
    reviewed = st.session_state.reviewed_patients

    urgent  = [p for p in r["auto_list"] if p.get("severity") == "High"   and p.get("name") not in reviewed]
    watch   = [p for p in r["auto_list"] if p.get("severity") == "Medium" and p.get("name") not in reviewed]
    routine = [p for p in r["auto_list"] if p.get("severity") == "Low" and not p.get("nudge_risk") and p.get("name") not in reviewed]

    nudge_raw = r["nudge_list"] + [p for p in r["auto_list"] if p.get("severity") == "Low" and p.get("nudge_risk")]
    seen, slippage = set(), []
    for p in nudge_raw:
        nm = p.get("name")
        if nm not in seen and nm not in reviewed:
            slippage.append(p); seen.add(nm)

    queue    = [p for p in r["queue_list"] if p.get("name") not in reviewed]
    on_track = r["on_track"]

    today     = date.today()
    today_str = f"{today.day} {today.strftime('%b %Y')}"

    # ── Header with anchor-link nav pills ────────────────────
    pills = []
    if urgent:
        pills.append(f'<a href="#section-urgent" class="summary-pill pill-urgent"><div class="num">{len(urgent)}</div><div class="lbl">Urgent</div></a>')
    if watch:
        pills.append(f'<a href="#section-watch" class="summary-pill pill-watch"><div class="num">{len(watch)}</div><div class="lbl">Watch</div></a>')
    if slippage:
        pills.append(f'<a href="#section-slippage" class="summary-pill pill-slip"><div class="num">{len(slippage)}</div><div class="lbl">Slippage</div></a>')
    if routine:
        pills.append(f'<a href="#section-routine" class="summary-pill pill-routine"><div class="num">{len(routine)}</div><div class="lbl">Routine</div></a>')
    if on_track:
        pills.append(f'<a href="#section-ontrack" class="summary-pill pill-routine" style="background:rgba(16,185,129,0.25)"><div class="num">{len(on_track)}</div><div class="lbl">On Track</div></a>')
    if queue:
        pills.append(f'<a href="#section-queue" class="summary-pill pill-queue"><div class="num">{len(queue)}</div><div class="lbl">Review</div></a>')

    st.markdown(f"""
<div id="brief-top"></div>
<div class="brief-header">
  <div class="brief-greeting">Coach Dashboard</div>
  <div class="brief-title-row">
    <span class="brief-title">Morning Brief</span>
    <span class="brief-date">{today_str}</span>
  </div>
  <div class="summary-bar">{"".join(pills)}</div>
</div>""", unsafe_allow_html=True)

    if urgent:
        st.markdown('<div id="section-urgent" class="section-header"><span class="section-label">🔴 Urgent — Act Today</span><a href="#brief-top" class="top-link">↑ top</a></div>', unsafe_allow_html=True)
        for i, p in enumerate(urgent):
            render_patient_card(p, i, "urgent")

    if watch:
        st.markdown('<div id="section-watch" class="section-header"><span class="section-label">🟡 Watch — Within 24h</span><a href="#brief-top" class="top-link">↑ top</a></div>', unsafe_allow_html=True)
        for i, p in enumerate(watch):
            render_patient_card(p, i, "watch")

    if slippage:
        count = len(slippage)
        st.markdown(f"""
<div id="section-slippage" class="slippage-banner">
  <span style="font-size:18px">⚠️</span>
  <span><strong>{count} patient{"s" if count>1 else ""}</strong> showing engagement drop — warm check-in recommended</span>
  <a href="#brief-top" class="top-link" style="margin-left:auto">↑ top</a>
</div>""", unsafe_allow_html=True)
        for i, p in enumerate(slippage):
            render_slippage_card(p, i)

    if routine:
        st.markdown('<div id="section-routine" class="section-header"><span class="section-label">🟢 Routine — Next Check-in</span><a href="#brief-top" class="top-link">↑ top</a></div>', unsafe_allow_html=True)
        for i, p in enumerate(routine):
            render_patient_card(p, i, "routine")

    if on_track:
        st.markdown('<div id="section-ontrack" class="section-header"><span class="section-label">✅ On Track</span><a href="#brief-top" class="top-link">↑ top</a></div>', unsafe_allow_html=True)
        for i, p in enumerate(on_track):
            render_patient_card(p, i, "ontrack")

    if queue:
        st.markdown(f'<div id="section-queue" class="section-header"><span class="section-label">🔵 Manual Review ({len(queue)})</span><a href="#brief-top" class="top-link">↑ top</a></div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:11px;color:#9CA3AF;margin:-4px 0 10px;">AI confidence was low — apply clinical judgement before acting.</p>', unsafe_allow_html=True)
        for i, p in enumerate(queue):
            render_patient_card(p, i, "queue")

    # ── Reviewed this session ─────────────────────────────────
    all_p_flat = r["auto_list"] + r["queue_list"] + r["nudge_list"]
    reviewed_list = [p for p in all_p_flat if p.get("name") in reviewed]
    if reviewed_list:
        with st.expander(f"✓ Reviewed this session ({len(reviewed_list)})"):
            for p in reviewed_list:
                n   = p.get("name","")
                sev = sev_label(p.get("severity",""))
                fb  = get_feedback_summary()
                st.markdown(f"""
<div class="reviewed-row">
  <span>✓</span>
  <span style="font-weight:600;color:#374151;">{n}</span>
  <span style="color:#9CA3AF;">·</span>
  <span>{sev}</span>
  <span style="margin-left:auto;font-size:10px;color:#9CA3AF;">Reviewed</span>
</div>""", unsafe_allow_html=True)

    # ── Feedback precision ────────────────────────────────────
    fb = get_feedback_summary()
    if fb["total"] > 0:
        with st.expander("📈 Feedback log"):
            m1, m2, m3 = st.columns(3)
            m1.metric("Reviewed", fb["total"])
            m2.metric("Correct 👍", fb["correct"])
            m3.metric("Precision", f"{fb['precision']}%")
            all_fb = get_all_feedback()
            if all_fb:
                for eid, entry in list(all_fb.items())[-6:]:
                    emoji  = "👍" if entry["reaction"] == "correct" else "👎"
                    reason = f" — {entry['wrong_reason']}" if entry.get("wrong_reason") else ""
                    st.caption(f"{emoji} **{entry['patient_name']}** | {sev_label(entry['severity'])} | {entry['date']}{reason}")


# ── Main render ───────────────────────────────────────────────
if st.session_state.results:
    v = st.session_state.view
    if v == "profile" and st.session_state.selected_patient:
        render_patient_profile()
    elif v == "notes":
        render_coach_notes()
    else:
        render_morning_brief(st.session_state.results)

elif st.session_state.data_loaded:
    st.markdown("## 🩺 MadhuMitra")
    st.divider()
    st.markdown("### Patient panel")
    try:
        preview_patients = None
        if st.session_state.demo_mode:
            preview_patients = load_patients("data/sample_patients.json")
        elif st.session_state.uploaded_file:
            import tempfile
            uf = st.session_state.uploaded_file
            uf.seek(0)
            suffix = ".csv" if uf.name.endswith(".csv") else ".json"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uf.read())
                _tmp_path = tmp.name
            preview_patients = load_patients(_tmp_path)
        if preview_patients:
            import pandas as pd
            rows = []
            for p in preview_patients:
                ph = p.get("program_history", {})
                ps = p.get("structured", {})
                comorbidities = [k.replace("_"," ") for k,v in ph.get("comorbidities",{}).items() if v]
                rows.append({
                    "Name": p.get("name",""), "Age": p.get("age",""),
                    "Week": ph.get("week_number","") or "—",
                    "FBS": f"{ps.get('fbs_mgdl','—')} mg/dL" if ps.get("fbs_mgdl") else "No log",
                    "Comorbidities": ", ".join(comorbidities[:2]) if comorbidities else "None",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(f"{len(preview_patients)} patients loaded · Click **Run reasoning loop** to analyse")
    except Exception:
        pass

else:
    st.markdown("""
<div style="text-align:center;padding:80px 20px;color:#9B9B94;">
  <div style="font-size:56px;margin-bottom:16px;">🩺</div>
  <p style="font-size:16px;margin-bottom:6px;color:#6B6B65;">Ready to analyse your patient panel</p>
  <p style="font-size:13px;">Load sample patients or upload a file,<br>then click <strong>Run reasoning loop</strong></p>
</div>
""", unsafe_allow_html=True)
