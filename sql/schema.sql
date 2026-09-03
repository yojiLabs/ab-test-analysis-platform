-- schema.sql
-- Defines the raw data model for the onboarding A/B test.
-- Three tables, mirroring how a real event-tracking system is structured:
-- users (who), assignments (which variant), events (what they did, when).

CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    signup_date    TEXT NOT NULL,      -- ISO date string 'YYYY-MM-DD'
    is_bot         INTEGER NOT NULL DEFAULT 0  -- 1 = synthetic outlier/bot account
);

CREATE TABLE IF NOT EXISTS assignments (
    user_id        INTEGER PRIMARY KEY REFERENCES users(user_id),
    variant        TEXT NOT NULL CHECK (variant IN ('control', 'treatment')),
    assigned_at    TEXT NOT NULL       -- ISO datetime string
);

CREATE TABLE IF NOT EXISTS events (
    event_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(user_id),
    event_name     TEXT NOT NULL,      -- e.g. 'signup_complete', 'add_payment_method',
                                        -- 'create_project', 'invite_teammate',
                                        -- 'support_ticket', 'active_day'
    event_timestamp TEXT NOT NULL      -- ISO datetime string
);

CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(event_name);
