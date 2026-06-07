# Idempotency Checklist — Google Cloud VPC

> **Purpose:** Document idempotent behavior for VPC operations. Critical for automation/repeated execution.

## Idempotent Operations

| Operation | Idempotent? | Behavior on Re-execution |
|-----------|------------|--------------------------|
| Create Network | **No** | Returns `ALREADY_EXISTS` / 409 |
| Create Subnet | **No** | Returns `ALREADY_EXISTS` / 409 |
| Create Firewall Rule | **No** | Returns `ALREADY_EXISTS` / 409 |
| Create Route | **No** | Returns `ALREADY_EXISTS` / 409 |
| Delete Network | **Yes** | Returns success or `NOT_FOUND` (already deleted) |
| Delete Subnet | **Yes** | Returns success or `NOT_FOUND` |
| Delete Firewall Rule | **Yes** | Returns success or `NOT_FOUND` |
| Describe Network | **Yes** | Same result every time (until resource changes) |
| List Networks | **Yes** | Consistent list (may change between calls due to other ops) |
| Update Firewall Rule | **Yes** (partial) | Same update reapplies; no side effect |
| Expand Subnet CIDR | **No** | Returns error — CIDR already expanded |

## Idempotent Create Pattern

For idempotent behavior, use a create-if-not-exists pattern:

```bash
# Check if network exists first
if ! gcloud compute networks describe "{{user.network_name}}" --format="json" 2>/dev/null; then
  echo "Network does not exist, creating..."
  gcloud compute networks create "{{user.network_name}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --subnet-mode=custom \
    --format="json"
else
  echo "Network already exists, verifying configuration..."
  gcloud compute networks describe "{{user.network_name}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format="json" | jq '{name, subnetMode, routingConfig}'
fi
```

## Create-or-Reuse Pattern (Recommended for Automation)

```python
# create_network_idempotent.py
import os
import subprocess
import json

project = os.environ["CLOUDSDK_CORE_PROJECT"]
network_name = "my-network"

# Check existence
result = subprocess.run(
    ["gcloud", "compute", "networks", "describe", network_name,
     "--project", project, "--format", "json"],
    capture_output=True, text=True
)

if result.returncode == 0:
    network = json.loads(result.stdout)
    print(f"Network already exists: {network['selfLink']}")
else:
    # Create
    subprocess.run([
        "gcloud", "compute", "networks", "create", network_name,
        "--project", project, "--subnet-mode=custom", "--format", "json"
    ], check=True)
    print(f"Network created: {network_name}")
```