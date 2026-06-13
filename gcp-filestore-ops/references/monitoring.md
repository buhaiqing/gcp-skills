# Monitoring — Filestore

## Key Metrics

| Metric | Type | Threshold |
|--------|------|-----------|
| filestore.googleapis.com/instance/used_bytes | Gauge | Monitor >80% capacity |
| filestore.googleapis.com/instance/free_bytes | Gauge | Alert <20% free |
| filestore.googleapis.com/instance/used_space_percent | Gauge | Alert >80% |
| filestore.googleapis.com/instance/free_disk_space_percent | Gauge | Basic tiers: alert <20% |
| filestore.googleapis.com/instance/free_raw_capacity_percent | Gauge | Zonal/Regional/Enterprise: alert <20% |
| filestore.googleapis.com/instance/disk_read_ops_count | Counter | Baseline — monitor IOPS |
| filestore.googleapis.com/instance/disk_write_ops_count | Counter | Baseline — monitor IOPS |
| filestore.googleapis.com/instance/avg_read_latency | Gauge | Alert >10ms |
| filestore.googleapis.com/instance/avg_write_latency | Gauge | Alert >10ms |
| filestore.googleapis.com/instance/snapshots_used_bytes | Gauge | Monitor snapshot storage |

## Metric Descriptions

### Free Raw Capacity Percent (Zonal/Regional/Enterprise)

Represents capacity available to users after replication. If this metric reaches 0%, new data cannot be written.

Use this metric (not free disk space percent) for Zonal, Regional, and Enterprise tiers.

### Free Disk Space Percent (Basic Tiers)

Represents free disk space for Basic HDD and Basic SSD tiers.

### Used Space Percent

Percentage of used disk bytes. Monitor to prevent capacity exhaustion.

### Snapshots Used Bytes

Space used by all snapshots (internal or external). Allocated per share, not per instance.

## Alert Policy Examples

### Low Disk Space (Basic Tiers)

```bash
gcloud alpha monitoring policies create \
  --display-name="Filestore-Low-Disk-Space-Basic" \
  --condition-filter='resource.type="filestore_instance" AND metric.type="filestore.googleapis.com/instance/free_disk_space_percent" AND metric.labels.instance_name="INSTANCE_NAME"' \
  --condition-threshold-value=20 \
  --condition-trigger-type=any \
  --condition-duration=600s
```

### Low Raw Capacity (Zonal/Regional/Enterprise)

```bash
gcloud alpha monitoring policies create \
  --display-name="Filestore-Low-Raw-Capacity" \
  --condition-filter='resource.type="filestore_instance" AND metric.type="filestore.googleapis.com/instance/free_raw_capacity_percent" AND metric.labels.instance_name="INSTANCE_NAME"' \
  --condition-threshold-value=20 \
  --condition-trigger-type=any \
  --condition-duration=600s
```

### Low Backups Quota

```bash
gcloud alpha monitoring policies create \
  --display-name="Filestore-Low-Backups-Quota" \
  --condition-filter='resource.type="consumer_quota" AND metric.type="serviceruntime.googleapis.com/quota/allocation/usage" AND metric.labels.quota_metric="file.googleapis.com/backups-per-region"' \
  --condition-threshold-value=10 \
  --condition-trigger-type=any
```

## Anomaly Patterns

| Pattern | Likely Cause |
|---------|--------------|
| Used space % spike | Bulk data write / data migration |
| Read/Write latency >10ms | Performance degradation / insufficient IOPS |
| Free space % rapid drop | App writing excessive data / missing cleanup |
| Snapshots used bytes spike | Too many snapshots / large data changes |

## Dashboard Query (Cloud Monitoring MQL)

```
fetch filestore_instance
| metric 'filestore.googleapis.com/instance/used_space_percent'
| group_by [resource.instance_name], mean()
| every 1h
```

```
fetch filestore_instance
| metric 'filestore.googleapis.com/instance/disk_read_ops_count'
| group_by [resource.instance_name], rate()
| every 1m
```
