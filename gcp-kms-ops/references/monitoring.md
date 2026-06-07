# Monitoring & Alerts — Cloud KMS

## Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `cloudkms.googleapis.com/crypto_key_version_count` | gauge | Number of key versions per key |
| `cloudkms.googleapis.com/encrypt_requests` | counter | Encrypt requests |
| `cloudkms.googleapis.com/decrypt_requests` | counter | Decrypt requests |
| `cloudkms.googleapis.com/operation_latencies` | distribution | Operation latency |
| `cloudkms.googleapis.com/key_operation_count` | counter | Total key operations |

## Alert Policy Example

### Key Version Scheduled for Destruction

```yaml
conditions:
- conditionMatchedLog:
    filter: 'protoPayload.methodName="DestroyCryptoKeyVersion"'
    logFilter: severity>=NOTICE
displayName: "KMS key version destroyed"
documentation:
  content: |-
    A key version was scheduled for destruction.
    Within 24 hours it can be restored.
```

## Anomaly Patterns

| Pattern | Possible Cause | Recommended Action |
|---------|---------------|-------------------|
| High encrypt/decrypt latency | HSM throttling or external key delay | Check protection level usage |
| Key version destruction | Accidental or malicious action | Restore within 24h |
| Permission denied spikes | IAM misconfiguration | Verify IAM bindings |
| Rate limit exceeded | Request rate too high | Implement client-side throttling |