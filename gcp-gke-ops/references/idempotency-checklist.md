# Idempotency Checklist — GKE

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Cluster | name (location-unique) | ALREADY_EXISTS / 409 |
| Node Pool | name (cluster-unique) | ALREADY_EXISTS / 409 |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Upgrade control plane | Yes (same version = no-op) |
| Upgrade node pool | Yes (same version = no-op) |
| Enable autoscaling | Yes (same params = no-op) |
| Update labels | Yes (same key:value = no-op) |
| Enable Workload Identity | Yes (same pool = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Cluster | Safe — NOT_FOUND on second attempt |
| Node pool | Safe — NOT_FOUND on second attempt |

## Safe Retry Pattern

```bash
if ! gcloud container clusters describe my-cluster --zone=Z --quiet 2>/dev/null; then
    gcloud container clusters create my-cluster --zone=Z --num-nodes=3
else
    echo "Already exists — no action needed"
fi
```

## Label De-Duplication

```bash
gcloud container clusters create my-cluster \
  --zone=us-central1 \
  --labels=deployment-id=deploy-20260607-001,created-by=automation
```

## Wait Operation Safely

All long-running GKE operations return an operation name. Poll with:
```bash
gcloud container operations describe OP_NAME --zone=Z --format="json" | jq -r '.status'
# Wait until status == "DONE"
while [[ "$(gcloud container operations describe OP_NAME --zone=Z --format='value(status)')" != "DONE" ]]; do
    sleep 10
done
```