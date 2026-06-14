-- MadhuMitra — migration v2: coach_notes table
-- Run this in Supabase SQL Editor AFTER migration.sql has already been run.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS coach_notes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id        UUID        REFERENCES alerts(id) ON DELETE SET NULL,
    patient_token   TEXT        NOT NULL,
    note_date       DATE        NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    action_type     TEXT        CHECK (action_type IN ('called','messaged','video','escalated')),
    note_text       TEXT        NOT NULL,
    tags            JSONB       NOT NULL DEFAULT '[]',
    outcome         TEXT,
    followup_date   DATE
);

COMMENT ON TABLE coach_notes IS
    'Coach-authored intervention notes. note_text is coach language, not patient free-text.';
COMMENT ON COLUMN coach_notes.patient_token IS
    'sha256(patient_name)[:16] — same token used in alerts and coach_feedback.';
COMMENT ON COLUMN coach_notes.tags IS
    'Focus area tags e.g. ["Medication","Exercise"]. Stored as JSONB array.';

CREATE INDEX IF NOT EXISTS idx_coach_notes_patient ON coach_notes(patient_token);
CREATE INDEX IF NOT EXISTS idx_coach_notes_date    ON coach_notes(note_date);

ALTER TABLE coach_notes ENABLE ROW LEVEL SECURITY;
