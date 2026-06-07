# Core Concepts — Memorystore for Redis

## Architecture

Cloud Memorystore for Redis provides fully managed in-memory data store with support for high availability, persistence, scaling, and security.

### Key Components

| Component | Description | Options |
|-----------|-------------|---------|
| **Basic Tier** | Standalone Redis instance (no replication) | 1-300 GB |
| **Standard Tier (HA)** | Primary + replica in different zones, auto-failover | 1-300 GB |
| **Read Replicas** | Additional read-only replicas for read-heavy workloads (Standard tier only) | 0-5 replicas |
| **Persistence** | RDB snapshots or AOF for data durability | RDB, AOF, or disabled |
| **Auth String** | Password authentication for Redis connections | Optional |
| **In-transit Encryption** | TLS encryption for data in transit | Optional |

### Redis Versions

| Version | Supported | Notes |
|---------|-----------|-------|
| redis_6_x | Yes (less common) | Limited feature set |
| redis_7_0 | Yes (recommended) | Latest stable, ACL support |
| redis_7_2 | Yes | Latest with additional features |

### Persistence Modes

| Mode | Description | RPO | Impact |
|------|-------------|-----|--------|
| Disabled | No persistence | N/A | Data lost on failover |
| RDB | Point-in-time snapshots | Configurable (1h default) | Minor latency during snapshot |
| AOF | Append-only file | Near-real-time | Slight latency overhead |

## Quotas

| Resource | Default Limit |
|----------|--------------|
| Redis instances per region per project | 10 |
| Total memory per region per project | 300 GB |
| Read replicas per instance | 5 (Standard tier only) |
| Network throughput | Proportional to memory size |

## Dependencies

| Depend On | Reason |
|-----------|--------|
| VPC Network | Redis instances require VPC for connectivity |
| Private Services Access | Required for VPC-private Redis connectivity |
| Cloud Storage | Export/import destination |
| Service Networking API | Required for VPC peering |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Zone failure (Basic tier) | Full outage | Use Standard tier (HA) |
| Instance deletion | Complete data loss | Export to GCS before deletion |
| Memory exhaustion | Redis OOM kill connections | Set memory limit, monitor usage |
| Network partition | No connectivity | Multi-region Redis (cross-region replication not supported natively) |