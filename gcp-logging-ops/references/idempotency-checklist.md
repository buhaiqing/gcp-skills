# Idempotency Checklist — Cloud Logging

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Log bucket | name (location-unique) | ALREADY_EXISTS / 409 |
| Log view | name (bucket-unique) | ALREADY_EXISTS / 409 |
| Log sink | name (project-unique) | ALREADY_EXISTS / 409 |
| Log metric | name (project-unique) | ALREADY_EXISTS / 409 |
| Log exclusion | name (project-unique) | ALREADY_EXISTS / 409 |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Update bucket retention | Yes (same value = no-op) |
| Update bucket description | Yes (same value = no-op) |
| Update sink destination/filter | Yes (same value = no-op) |
| Update exclusion filter | Yes (same value = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Log bucket | Safe — NOT_FOUND on second attempt |
| Log view | Safe — NOT_FOUND on second attempt |
| Log sink | Safe — NOT_FOUND on second attempt |
| Log metric | Safe — NOT_FOUND on second attempt |
| Log exclusion | Safe — NOT_FOUND on second attempt |

## Safe Retry Pattern

```bash
if ! gcloud logging metrics describe "my-metric" --project=P --quiet 2>/dev/null; then
    gcloud logging metrics create "my-metric" --log-filter="severity>=ERROR" --description="Error metric"
else
    echo "Already exists — no action needed"
fi
```

## Label De-Duplication

Not applicable — Cloud Logging resources do not use labels. Use descriptive resource names instead: