-- GCL Trace Schema for BigQuery
-- Version: 1.0.0
-- Updated: 2026-07-18

CREATE SCHEMA IF NOT EXISTS gcp_skills_gcl_audit;

CREATE TABLE IF NOT EXISTS gcp_skills_gcl_audit.gcl_traces (
    -- Trace identification
    trace_id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,

    -- Operation context
    skill STRING NOT NULL,
    op STRING NOT NULL,
    user_request STRING,

    -- Execution result
    result STRING NOT NULL,  -- PASS | MAX_ITER | SAFETY_FAIL | ERROR
    exit_code INT64,

    -- Performance metrics
    latency_ms INT64,
    iterations_count INT64,
    autonomy_ratio FLOAT64,  -- 0.0 - 1.0

    -- Safety scoring
    safety_score FLOAT64,  -- 0.0 - 1.0
    safety_failures INT64,

    -- Error classification
    error_type STRING,  -- INVALID_ARGUMENT | PERMISSION_DENIED | NOT_FOUND | TIMEOUT | INTERNAL | ...

    -- Decision tracking
    autonomy_decisions JSON,
    degraded_to_human BOOL,
    degradation_reason STRING,

    -- Iteration details (JSON array)
    iterations JSON,

    -- GCP context
    gcp_project STRING,
    gcp_region STRING,

    -- Environment
    environment STRING,  -- production | staging | development

    -- Metadata
    trace_version STRING DEFAULT "1.0.0",
    runner_version STRING,
)
PARTITION BY DATE(timestamp)
CLUSTER BY skill, op, result
OPTIONS (
    description = "GCL Generator-Critic-Loop execution traces for observability",
    labels = [("team", "platform"), ("product", "gcp-skills")]
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_gcl_traces_skill_op
ON gcp_skills_gcl_audit.gcl_traces (skill, op);

CREATE INDEX IF NOT EXISTS idx_gcl_traces_result
ON gcp_skills_gcl_audit.gcl_traces (result);

CREATE INDEX IF NOT EXISTS idx_gcl_traces_timestamp
ON gcp_skills_gcl_audit.gcl_traces (timestamp);
