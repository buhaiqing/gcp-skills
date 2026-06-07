# Monitoring & Alerts — Google Cloud VPC

## Key Metrics (Cloud Monitoring)

| Metric | Type | Description |
|--------|------|-------------|
| `compute.googleapis.com/vpn/established_tunnels` | GAUGE | Number of established VPN tunnels |
| `compute.googleapis.com/vpn/sent_packets_count` | COUNTER | Packets sent through VPN tunnels |
| `compute.googleapis.com/vpn/received_packets_count` | COUNTER | Packets received through VPN tunnels |
| `compute.googleapis.com/vpc/flow_logs_bytes` | COUNTER | Bytes ingested by VPC Flow Logs |
| `compute.googleapis.com/nat/nat_connections_used` | GAUGE | Active NAT connections |
| `compute.googleapis.com/nat/nat_connections_egress_rate` | GAUGE | NAT egress connection rate |
| `compute.googleapis.com/nat/nat_allocated_ports` | GAUGE | NAT ports allocated |

## Recommended Alert Policies

| Alert | Condition | Severity | Notification |
|-------|-----------|----------|-------------|
| VPN tunnel down | `established_tunnels < expected_count` for 5min | Critical | Pager/email |
| NAT port exhaustion | `(nat_allocated_ports / total_ports) > 0.8` for 5min | Warning | Email |
| High flow log cost | `flow_logs_bytes > threshold` per day | Warning | Email |

## VPC Flow Logs

Enable flow logs to capture traffic metadata:
```bash
gcloud compute networks subnets update "{{user.subnet_name}}" \
  --region="{{user.region}}" \
  --enable-flow-logs \
  --logging-aggregation-interval=INTERVAL_5_SEC \
  --logging-flow-sampling=0.5 \
  --logging-metadata=INCLUDE_ALL_METADATA
```

Query flow logs:
```bash
gcloud logging read 'resource.type="gce_subnetwork" \
  AND logName:"compute.googleapis.com/vpc_flows"' \
  --limit=20 \
  --format="json" | jq '.[] | {src_ip: .jsonPayload.connection.src_ip, dest_ip: .jsonPayload.connection.dest_ip, bytes_sent: .jsonPayload.connection.bytes_sent}'
```