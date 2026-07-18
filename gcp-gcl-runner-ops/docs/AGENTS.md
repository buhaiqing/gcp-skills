# GCP-Skills Agent Architecture

> **Version:** 2.0.0 (Level 3)
> **Last Updated:** 2026-07-18

---

## Overview

This document describes the agent architecture for GCP-Skills, organized by Gartner Agentic AI Maturity Model levels.

| Level | Name | Description |
|-------|------|-------------|
| **L1** | Task-Based Copilots | Single-turn skill execution |
| **L2** | Coordinated Multi-Agent | Sequential multi-skill orchestration |
| **L3** | Autonomous Orchestration | Adversarial quality gate with observability |
| **L4** | Self-Learning Ecosystems | Adaptive optimization from historical data |

---

## Level 3: Autonomous Orchestration (Current)

Level 3 introduces the **Generator-Critic-Loop (GCL)** adversarial quality gate with full observability.

### Enhanced GCL Runner (EGR)

The EGR extends the base GCL Runner with autonomous capabilities:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Enhanced GCL Runner                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │ Pre-flight   │───▶│ GCL Runner  │───▶│ Trace       │    │
│  │ State Snap   │    │ Core        │    │ Collector    │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│         │                   │                    │             │
│         │                   ▼                    ▼             │
│         │            ┌──────────────┐    ┌──────────────┐    │
│         │            │ Autonomy    │    │ BigQuery     │    │
│         │            │ Engine      │    │ Writer       │    │
│         │            └──────────────┘    └──────────────┘    │
│         │                   │                    │             │
│         ▼                   ▼                    ▼             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Cloud Logging                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### EGR Components

| Component | Responsibility | EGR Feature |
|-----------|---------------|--------------|
| **GCL Runner Core** | Generator-Critic-Loop execution | Enhanced with EGR-1, EGR-2 |
| **Trace Collector** | Aggregates traces from all iterations | EGR-3 |
| **BigQuery Writer** | Persists traces for analytics | EGR-3 |
| **Cloud Logging** | Structured error/decision logging | EGR-3 |
| **Autonomy Engine** | Tracks failures, calculates ratio, degrades | EGR-4 |
| **State Snapshot Diff** | Captures pre/post resource state | EGR-5 |

### EGR Features (EGR-1 through EGR-5)

| Feature | Description |
|---------|-------------|
| **EGR-1: Auto-retry** | Exponential backoff retry on transient errors (timeout, rate limit, internal) |
| **EGR-2: Safety=0 Termination** | Force termination when PERMISSION_DENIED detected |
| **EGR-3: BigQuery Trace** | Automatic trace upload to BigQuery for analytics |
| **EGR-4: Auto-degrade** | Human handoff after consecutive failures exceed threshold |
| **EGR-5: State Snapshot** | Pre/post execution state diff for audit trail |

### Level 3 Data Flow

```
User Request → GCL Runner → Generator → Command Execution
                                   ↓
                              Critic (Safety Check)
                                   ↓
                         Autonomy Engine (Decision)
                                   ↓
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
               Cloud Logging   BigQuery      Local Trace
```

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `gcl_error_rate` | Error rate per minute | < 10/min |
| `gcl_execution_latency` | P95 execution time | < 30s |
| `gcl_safety_failures` | Safety=0 events | 0 |
| `gcl_autonomy_ratio` | Autonomous execution ratio | > 0.5 |

---

## Level 2: Coordinated Multi-Agent (Sequential)

Level 2 chains multiple skills in sequence:

```
User Request → Skill A → Skill B → Skill C → Result
                    ↓         ↓
               [Logging]  [Logging]
```

### Skills Catalog

| Skill | Operations |
|-------|------------|
| `gcp-gce-ops` | CreateInstance, DeleteInstance, StopInstance, StartInstance |
| `gcp-gcs-ops` | CreateBucket, DeleteBucket, SetBucketLifecycle |
| `gcp-iam-ops` | AddIAMMember, RemoveIAMMember, CreateServiceAccount |
| `gcp-monitoring-ops` | CreateAlertPolicy, CreateNotificationChannel |
| `gcp-securitycenter-ops` | ListFindings, ListSources |

---

## Level 1: Task-Based Copilots (Single-Turn)

Level 1 executes single-turn commands with basic error handling:

```python
# Example: Single skill execution
result = skill.execute(command="gcloud compute instances list")
return result
```

---

## Comparison: Level 2 vs Level 3

| Aspect | Level 2 | Level 3 |
|--------|---------|---------|
| Quality Gate | None | Adversarial GCL |
| Observability | Basic logs | Full trace + metrics |
| Error Handling | Retry once | Exponential backoff |
| Autonomy | Always full | Ratio-based |
| Traceability | Command-level | Full state diff |

---

## Architecture Files

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed EGR architecture
- [EGR_HANDBOOK.md](EGR_HANDBOOK.md) - Operational guide
- [LOGGING.md](LOGGING.md) - Structured logging guide
- [LOG_METRICS.md](LOG_METRICS.md) - Cloud Monitoring metrics
