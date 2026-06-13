# Troubleshooting — Filestore

## Error Codes

| gRPC/HTTP | Meaning | Agent Action |
|-----------|---------|--------------|
| INVALID_ARGUMENT / 400 | Request validation failed | Fix parameter per API (tier, capacity, network) |
| PERMISSION_DENIED / 403 | Insufficient IAM | Grant roles/filestore.admin or roles/filestore.editor |
| NOT_FOUND / 404 | Resource not found | Verify instance name, backup ID, zone/region |
| ALREADY_EXISTS / 409 | Duplicate instance name | Choose unique instance name |
| QUOTA_EXCEEDED / 429 | Quota limit | Request increase via Cloud Console |
| INTERNAL / 500 | Server error | Retry, then escalate |
| UNAVAILABLE / 503 | Service unavailable | Retry with backoff |
| FAILED_PRECONDITION / 400 | Wrong instance state | Wait for READY state |
| ABORTED / 409 | Operation conflict | Retry after completion |
| RESOURCE_EXHAUSTED / 429 | Too many concurrent ops | Reduce concurrency |
| BILLING_NOT_ENABLED | Billing inactive | Enable in Cloud Console |
| INVALID_TIER | Tier not available | Check available tiers for region |
| CAPACITY_EXCEEDED | Capacity out of range | Check tier capacity limits |
| NETWORK_NOT_FOUND | VPC network not found | Verify network name exists |
| STORAGE_FULL | Instance storage exhausted | Resize or free space |
| BACKUP_FAILED | Backup operation failed | Check quota, retry |
| RESTORE_FAILED | Restore from backup failed | Verify backup integrity, retry |
| SNAPSHOT_FAILED | Snapshot creation failed | Check capacity, retry |
| REPLICATION_FAILED | Replication broken | Check logs, verify connectivity |
| MOUNT_FAILED | NFS mount error | Check firewall, IP-based access |

## Diagnostic Order

1. Describe instance: `gcloud filestore instances describe NAME --zone=ZONE --format=json`
2. List operations: `gcloud filestore operations list --zone=ZONE --format=json`
3. Check instance state: `gcloud filestore instances describe NAME --zone=ZONE --format="json" | jq '.state'`
4. Check capacity: `gcloud filestore instances describe NAME --zone=ZONE --format="json" | jq '.fileShares[0].capacityGb'`
5. Check network config: `gcloud filestore instances describe NAME --zone=ZONE --format="json" | jq '.networks'`
6. Check Cloud Logging: `resource.type="filestore_instance"`
7. Test NFS mount: `showmount -e INSTANCE_IP`

## Common Issues

### Instance Won't Create

- **Invalid tier**: Check tier availability in region
- **Network not found**: Verify VPC network exists
- **Quota exhausted**: Request increase
- **Reserved IP range**: Check --reserved-ip-range flag
- **Firewall blocking**: Ensure NFS ports (111, 2049) are open

### Can't Mount NFS Share

```bash
# Check instance IP and export path
gcloud filestore instances describe NAME --zone=ZONE --format="json" \
| jq '{ipAddresses: [.networks[].ipAddresses[]], fileShares: [.fileShares[].name]}'

# Verify NFS ports open on client
sudo iptables -L | grep -E "111|2049"

# Check IP-based access control
gcloud filestore instances describe NAME --zone=ZONE --format="json" \
| jq '.networks[].ipAddresses'

# Mount manually
sudo mount -t nfs INSTANCE_IP:/SHARE LOCAL_MOUNT_POINT
```

### Storage Full

```bash
# Check current capacity
gcloud filestore instances describe NAME --zone=ZONE --format="json" \
| jq '{name, state, fileShares: [.fileShares[] | {name, capacityGb}]}'

# Resize capacity (scale up only for BASIC tiers)
gcloud filestore instances update NAME --zone=ZONE \
  --file-share=name=SHARE,capacity=NEW_CAPACITY_TiB
```

### Backup Failed

- **Quota exceeded**: Check backup quota per region
- **Instance not READY**: Wait for instance to be ready
- **Concurrent backup**: Wait for running backup to complete
- **Rate limit**: Max 1 backup op per 10 minutes (burst: 6 in 60 min)

### Performance Issues

```bash
# Check instance performance metrics
gcloud alpha monitoring metrics list --filter="filestore"

# View metrics in Cloud Console
# Monitoring > Metrics Explorer > Filestore Instance
# Select: Used space percent, Free disk space percent, Average read/write latency
```

### Replication Issues

```bash
# Check replica status
gcloud filestore instances describe REPLICA --zone=ZONE --format=json \
| jq '.replication'

# Promote replica if needed
gcloud filestore instances promote-replica REPLICA --zone=ZONE
```

### Snapshot Creation Failed

- **Tier not supported**: Snapshots only supported on Zonal, Regional, Enterprise
- **Too many snapshots**: Max 240 snapshots per instance
- **Capacity full**: Free up space before creating snapshot

### Network Connectivity Issues

```bash
# Verify VPC network peering
gcloud compute networks peerings list --network=NETWORK

# Check firewall rules
gcloud compute firewall-rules list --network=NETWORK

# Allow NFS traffic
gcloud compute firewall-rules create allow-nfs \
  --network=NETWORK \
  --allow=tcp:111,tcp:2049,udp:111,udp:2049 \
  --source-ranges=CLIENT_CIDR
```
