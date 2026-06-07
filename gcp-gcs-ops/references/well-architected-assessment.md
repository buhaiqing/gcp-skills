# Well-Architected Assessment — Cloud Storage

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/storage.admin | Full GCS API — production |
| roles/storage.objectAdmin | Object CRUD operations |
| roles/storage.objectViewer | Read-only object access |
| roles/storage.legacyBucketOwner | Bucket-level management (legacy) |

**Credentials**: Never log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`
**Encryption**: Use CMEK for sensitive data; CSEK for additional control; default encryption at rest always active.
**Public Access Prevention**: Enforce to block public access by default.
**Uniform Bucket-Level Access**: Enable to simplify permission management.
**VPC Service Controls**: Restrict data exfiltration by limiting access to approved VPCs.
**Signed URLs**: Always set expiration (max 7 days for service accounts; default 1 hour).
**Retention Policies**: Set for compliance; lock only when absolutely certain.

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| Object versioning | Preserve all object versions; recover from accidental deletion |
| Retention policies | Minimum duration objects must be kept |
| Object holds | Prevent deletion/replacement during legal hold |
| Multi-region storage | 99.999999999% durability across multiple geographic regions |
| Lifecycle policies | Automated transition to lower-cost storage or deletion |

DR Runbook:
1. Confirm bucket region is unavailable
2. Access data from multi-region or dual-region bucket (multi-region automatically handles this)
3. If bucket is in single region and unavailable:
    - Restore objects from cross-region backup
    - Create new bucket in healthy region
    - Copy backup data to new bucket
4. Update application endpoints

## §3 Cost

| Storage Class | Cost (per GB/month) | Best For |
|---------------|---------------------|----------|
| STANDARD | Standard | Active, frequently accessed data |
| NEARLINE | ~40% less than STANDARD | Data accessed <1x/month |
| COLDLINE | ~60% less than STANDARD | Data accessed <1x/quarter |
| ARCHIVE | ~75% less than STANDARD | Data accessed <1x/year |

**Cost Optimization:**
- Enable Autoclass for automatic storage class transitions
- Use lifecycle rules to transition old objects to lower-cost storage
- Delete stale objects with lifecycle rules
- Use Requester Pays for shared datasets
- Monitor storage costs with bucket labels

## §4 Efficiency

- **Bucket naming**: Globally unique, DNS-compliant names (3-63 chars, lowercase)
- **Object prefix**: Use folder-like prefixes (`logs/2026/06/07/app.log`) for organization
- **Batch operations**: Use parallel composite uploads for large files; use rsync for directory sync
- **Lifecycle rules**: Automate storage class transitions and deletion
- **Autoclass**: Let GCS automatically manage storage class transitions
- **Labels**: Cost tracking (`env`, `app`, `team`, `project`)

## §5 Performance

| Location Type | Read SLA | Write SLA | Use Case |
|---------------|----------|-----------|----------|
| Multi-region | 99.95% | 99.95% | Global access, highest availability |
| Dual-region | 99.95% | 99.95% | Regional redundancy |
| Regional | 99.90% | 99.90% | Compute co-location, lowest latency |

**Performance optimization:**
- Co-locate storage with compute (same region)
- Use parallel downloads for large objects
- Use gRPC API for higher throughput (Python SDK supports)
- Use CDN integration for frequently accessed public data
- Monitor request rates to avoid throttling