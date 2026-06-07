# Idempotency Checklist — Cloud Load Balancing

## Overview

LB operations are generally idempotent by nature because they are configuration-only (no data mutation). However, certain operations require care for retry safety.

## Create Operations

| Resource | Idempotency Key | Behavior on Retry | Safe to Retry? |
|----------|----------------|-------------------|----------------|
| Forwarding Rule | Name (project-unique) | `ALREADY_EXISTS` / 409 | Safe — verify name uniqueness first |
| Backend Service | Name (project-unique) | `ALREADY_EXISTS` / 409 | Safe — verify name uniqueness first |
| URL Map | Name (project-unique) | `ALREADY_EXISTS` / 409 | Safe — verify name uniqueness first |
| Health Check | Name (project-unique) | `ALREADY_EXISTS` / 409 | Safe — verify name uniqueness first |
| SSL Certificate | Name (project-unique) | `ALREADY_EXISTS` / 409 | Safe — verify name uniqueness first |
| NEG | Name (zone-unique) | `ALREADY_EXISTS` / 409 | Safe — verify name uniqueness first |

## Update Operations

| Operation | Idempotent? | Notes |
|-----------|-------------|-------|
| Add backend to service | Yes | Adding same backend twice → duplicate (patching may fail if already present) |
| Remove backend from service | Yes | Removing non-existent backend → `NOT_FOUND` or no-op |
| Update URL map path matcher | Yes | Full PATCH replaces entire path matchers array |
| Update SSL policy | Yes | Idempotent — same policy applied twice has same effect |
| Update backend service timeout | Yes | Same value idempotent |

## Delete Operations

| Resource | Retry Safe? | Notes |
|----------|-------------|-------|
| Forwarding Rule | Safe — `NOT_FOUND` on second attempt | HALT if in use by target proxy |
| Backend Service | Safe — `NOT_FOUND` on second attempt | Check no URL map references it first |
| URL Map | Safe — `NOT_FOUND` on second attempt | Check no target proxy references it first |
| Health Check | Safe — `NOT_FOUND` on second attempt | Check no backend service references it first |
| SSL Certificate | Safe — `NOT_FOUND` on second attempt | Check no target proxy references it first |
| NEG | Safe — `NOT_FOUND` on second attempt | Check no backend service references it first |

## Retry Logic

```bash
# Safe retry pattern for create (verify first)
if ! gcloud compute forwarding-rules describe "my-rule" --global --quiet 2>/dev/null; then
    gcloud compute forwarding-rules create "my-rule" \
      --load-balancing-scheme=EXTERNAL_MANAGED \
      --target-https-proxy="my-proxy" \
      --ports=443 \
      --global
else
    echo "Forwarding rule already exists — no action needed"
fi
```

## Label-Based De-duplication

Use labels for automation to track which resources were created by which operation:

```bash
gcloud compute forwarding-rules create "my-rule" \
  --labels="deployment-id=deploy-20260607-001,created-by=automation" \
  --target-https-proxy="my-proxy" \
  --ports=443 \
  --global
```