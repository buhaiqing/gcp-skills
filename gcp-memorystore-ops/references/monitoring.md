# Monitoring & Alerts — Memorystore for Redis

## Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `redis.googleapis.com/instance/memory_usage_ratio` | gauge | Memory usage as fraction of max |
| `redis.googleapis.com/instance/connections` | gauge | Active client connections |
| `redis.googleapis.com/instance/cpu_utilization` | gauge | CPU usage percentage |
| `redis.googleapis.com/instance/keyspace_hit_rate` | gauge | Cache hit ratio |
| `redis.googleapis.com/instance/expired_keys` | counter | Keys expired |
| `redis.googleapis.com/instance/replication_lag` | gauge | Replica lag in seconds |
| `redis.googleapis.com/instance/commands_total` | counter | Total Redis commands executed |

## Alert Policy Example

### High Memory Usage

```yaml
conditions:
- conditionThreshold:
    filter: metric.type="redis.googleapis.com/instance/memory_usage_ratio"
    duration: 300s
    comparison: COMPARISON_GT
    thresholdValue: 0.85
displayName: "Redis memory > 85%"
documentation:
  content: |-
    Redis instance {{user.instance_name}} is using >85% of max memory.
    Consider scaling up or optimizing data retention.
```

## Anomaly Patterns

| Pattern | Possible Cause | Recommended Action |
|---------|---------------|-------------------|
| Memory ratio > 90% | Data growth, evictions starting | Scale up or optimize keys |
| Connection spike | Application misconfiguration | Check connection pool |
| Replication lag increasing | Network or primary overload | Check network, scale primary |
| Keyspace hit rate dropping | Cache inefficiency | Review caching strategy |