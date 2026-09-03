-- build_analysis_table.sql
-- Transforms raw users/assignments/events into one row per user with the
-- exact metrics defined in reports/hypothesis.md:
--   - day7_activated (primary metric)
--   - retained_30d (guardrail)
--   - had_support_ticket (guardrail)
-- Excludes bot accounts, since those should never enter the real analysis.

DROP TABLE IF EXISTS analysis_ready;

CREATE TABLE analysis_ready AS
WITH signup_info AS (
    SELECT
        u.user_id,
        u.signup_date,
        a.variant,
        a.assigned_at,
        e_signup.event_timestamp AS signup_ts
    FROM users u
    JOIN assignments a ON a.user_id = u.user_id
    JOIN events e_signup
        ON e_signup.user_id = u.user_id
        AND e_signup.event_name = 'signup_complete'
    WHERE u.is_bot = 0
),

key_actions AS (
    -- Count distinct key onboarding actions completed within 7 days of signup
    SELECT
        s.user_id,
        COUNT(DISTINCT e.event_name) AS key_actions_within_7d
    FROM signup_info s
    JOIN events e
        ON e.user_id = s.user_id
        AND e.event_name IN ('add_payment_method', 'create_project', 'invite_teammate')
        AND julianday(e.event_timestamp) <= julianday(s.signup_ts) + 7
    GROUP BY s.user_id
),

retention AS (
    -- Retained if there's an 'active_day' event around day 30
    SELECT
        s.user_id,
        MAX(CASE
            WHEN e.event_name = 'active_day'
                 AND julianday(e.event_timestamp) BETWEEN
                     julianday(s.signup_ts) + 25 AND julianday(s.signup_ts) + 35
            THEN 1 ELSE 0
        END) AS retained_30d
    FROM signup_info s
    LEFT JOIN events e ON e.user_id = s.user_id
    GROUP BY s.user_id
),

tickets AS (
    SELECT
        s.user_id,
        COUNT(CASE
            WHEN e.event_name = 'support_ticket'
                 AND julianday(e.event_timestamp) <= julianday(s.signup_ts) + 7
            THEN 1
        END) AS support_tickets_7d
    FROM signup_info s
    LEFT JOIN events e ON e.user_id = s.user_id
    GROUP BY s.user_id
)

SELECT
    s.user_id,
    s.signup_date,
    s.variant,
    COALESCE(k.key_actions_within_7d, 0) AS key_actions_within_7d,
    CASE WHEN COALESCE(k.key_actions_within_7d, 0) = 3 THEN 1 ELSE 0 END AS day7_activated,
    COALESCE(r.retained_30d, 0) AS retained_30d,
    CASE WHEN COALESCE(t.support_tickets_7d, 0) > 0 THEN 1 ELSE 0 END AS had_support_ticket
FROM signup_info s
LEFT JOIN key_actions k ON k.user_id = s.user_id
LEFT JOIN retention r ON r.user_id = s.user_id
LEFT JOIN tickets t ON t.user_id = s.user_id;

-- Quick sanity check query (run separately, not part of table build):
-- SELECT variant,
--        COUNT(*) AS n_users,
--        AVG(day7_activated) AS activation_rate,
--        AVG(retained_30d) AS retention_rate,
--        AVG(had_support_ticket) AS ticket_rate
-- FROM analysis_ready
-- GROUP BY variant;
