-- MadhuMitra — Supabase schema migration
-- Run this in the Supabase SQL editor (Database → SQL Editor → New query).
-- Safe to re-run: all statements use IF NOT EXISTS / CREATE OR REPLACE.
-- ─────────────────────────────────────────────────────────────────────────────

-- Enable pgcrypto for gen_random_uuid() if not already active
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ── 1. triage_runs ────────────────────────────────────────────────────────────
-- One row per time the analysis pipeline is run.
-- Provides the time-series anchor for all alerts produced in that run.

CREATE TABLE IF NOT EXISTS triage_runs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at          TIMESTAMPTZ NOT NULL    DEFAULT now(),
    data_date       DATE,                  -- the log date of the patient data
    patient_count   INT,
    high_count      INT,
    medium_count    INT,
    low_count       INT,
    queue_count     INT,
    on_track_count  INT,
    data_source     TEXT        CHECK (data_source IN ('sample', 'upload'))
);

COMMENT ON TABLE triage_runs IS
    'One row per pipeline execution. Parent of all alerts produced in that run.';
COMMENT ON COLUMN triage_runs.data_date IS
    'Date of the patient logs analysed — not the run timestamp.';


-- ── 2. alerts ─────────────────────────────────────────────────────────────────
-- One row per patient per triage run.
-- Stores only derived clinical signals — never raw patient free-text.
-- patient_token is a one-way hash of the patient name (sha256[:16]).

CREATE TABLE IF NOT EXISTS alerts (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID        NOT NULL REFERENCES triage_runs(id) ON DELETE CASCADE,
    patient_token       TEXT        NOT NULL,
    severity            TEXT        CHECK (severity IN ('High', 'Medium', 'Low', 'On Track', 'Unknown')),
    track               TEXT        CHECK (track IN ('auto', 'queue', 'on_track', 'nudge')),
    confidence          TEXT        CHECK (confidence IN ('high', 'low')),
    source              TEXT        CHECK (source IN ('rules', 'llm')),
    signal_set          JSONB       NOT NULL DEFAULT '[]',
    priority_score      INT,
    escalate_to_doctor  BOOLEAN     NOT NULL DEFAULT false,
    has_tier1_symptom   BOOLEAN     NOT NULL DEFAULT false,
    medication_missed   BOOLEAN     NOT NULL DEFAULT false,
    glucose_trend       TEXT,
    verified            BOOLEAN     NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (run_id, patient_token)  -- one alert per patient per run
);

COMMENT ON TABLE alerts IS
    'One alert row per patient per triage run. signal_set stores clinical labels only — no raw patient text.';
COMMENT ON COLUMN alerts.patient_token IS
    'sha256(patient_name)[:16] — deterministic one-way hash. Raw name is never stored.';
COMMENT ON COLUMN alerts.signal_set IS
    'Array of clinical signal strings produced by the rules engine or LLM. '
    'Joined to coach_feedback to form the eval ground-truth dataset.';

CREATE INDEX IF NOT EXISTS idx_alerts_run_id        ON alerts(run_id);
CREATE INDEX IF NOT EXISTS idx_alerts_patient_token ON alerts(patient_token);
CREATE INDEX IF NOT EXISTS idx_alerts_severity       ON alerts(severity);


-- ── 3. coach_feedback ─────────────────────────────────────────────────────────
-- One row per 👍/👎 tap by a coach in the Morning Brief UI.
-- Doubles as the eval ground-truth set:
--   SELECT cf.reaction, cf.wrong_reason, cf.signal_set
--   FROM coach_feedback cf
--   JOIN alerts a ON cf.alert_id = a.id
--   WHERE cf.reaction = 'incorrect';
--
-- signal_set is denormalized here so the eval query works even when
-- alert_id is NULL (feedback recorded before alerts were saved to DB).

CREATE TABLE IF NOT EXISTS coach_feedback (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id        UUID        REFERENCES alerts(id) ON DELETE SET NULL,  -- nullable: best-effort FK
    patient_token   TEXT        NOT NULL,
    feedback_date   DATE        NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    severity        TEXT        NOT NULL,
    track           TEXT,
    signal_set      JSONB       NOT NULL DEFAULT '[]',   -- denormalized from alerts.signal_set
    reaction        TEXT        NOT NULL CHECK (reaction IN ('correct', 'incorrect')),
    wrong_reason    TEXT                                  -- NULL when reaction = 'correct'
);

COMMENT ON TABLE coach_feedback IS
    '👍/👎 coach reactions. signal_set is denormalized so it is queryable as '
    'eval ground truth even without the alerts JOIN.';
COMMENT ON COLUMN coach_feedback.alert_id IS
    'FK to alerts — nullable. Populated when a matching alert row exists for this patient+date.';
COMMENT ON COLUMN coach_feedback.signal_set IS
    'Copy of the clinical signals shown to the coach when they gave feedback. '
    'Use this column (or the JOIN to alerts.signal_set) for calibration queries.';
COMMENT ON COLUMN coach_feedback.wrong_reason IS
    'One of: "False positive", "Severity too high", "Already handled", "Low priority". '
    'NULL when reaction = ''correct''.';

CREATE INDEX IF NOT EXISTS idx_coach_feedback_patient  ON coach_feedback(patient_token);
CREATE INDEX IF NOT EXISTS idx_coach_feedback_reaction ON coach_feedback(reaction);
CREATE INDEX IF NOT EXISTS idx_coach_feedback_date     ON coach_feedback(feedback_date);
CREATE INDEX IF NOT EXISTS idx_coach_feedback_alert    ON coach_feedback(alert_id);


-- ── Row Level Security ───────────────────────────────────────────────────────
-- RLS is enabled on all tables. No anon/authenticated policies are added here
-- because the app authenticates as the service_role (server-side Streamlit —
-- the key never reaches a browser). Service role bypasses RLS automatically.
--
-- When you add per-clinic auth later, add policies here, e.g.:
--   CREATE POLICY "clinic can read own alerts"
--     ON alerts FOR SELECT
--     USING (auth.jwt() ->> 'clinic_id' = clinic_id);

ALTER TABLE triage_runs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE coach_feedback ENABLE ROW LEVEL SECURITY;


-- ── Eval ground-truth view ────────────────────────────────────────────────────
-- Ready-to-query view for calibration: which signal sets were wrong?

CREATE OR REPLACE VIEW eval_ground_truth AS
SELECT
    cf.id                               AS feedback_id,
    cf.patient_token,
    cf.feedback_date,
    cf.severity                         AS alerted_severity,
    cf.track                            AS alerted_track,
    cf.signal_set                       AS coach_feedback_signals,
    a.signal_set                        AS alert_signals,       -- NULL if alert_id is NULL
    cf.reaction,
    cf.wrong_reason,
    cf.created_at
FROM coach_feedback cf
LEFT JOIN alerts a ON cf.alert_id = a.id
ORDER BY cf.created_at DESC;

COMMENT ON VIEW eval_ground_truth IS
    'Coach feedback joined to alert signal sets. '
    'Filter on reaction = ''incorrect'' for false-positive analysis.';
