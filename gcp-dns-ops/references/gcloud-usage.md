# gcloud — Cloud DNS CLI

## Install and Config

- Install: See [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- **CRITICAL Credentials:** Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth login`
- Verify DNS subcommands: `gcloud dns --help`

## Conventions (Agent Execution)

- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- Long-running operations complete synchronously for zone create/delete
- Record-set changes via transaction API are atomic

## CLI vs API Coverage Gap

| Operation (REST API) | Available via `gcloud`? | Notes |
|----------------------|------------------------|-------|
| Create zone | yes | `gcloud dns managed-zones create` |
| Describe zone | yes | `gcloud dns managed-zones describe` |
| List zones | yes | `gcloud dns managed-zones list` |
| Update zone | yes | `gcloud dns managed-zones update` |
| Delete zone | yes | `gcloud dns managed-zones delete` |
| List zone operations | yes | `gcloud dns managed-zone operations list` |
| Create change (records) | yes (via transaction) | `gcloud dns record-sets transaction` |
| List records | yes | `gcloud dns record-sets list` |
| Describe record | yes | `gcloud dns record-sets describe` |
| List policies | yes | `gcloud dns policies list` |
| Describe policy | yes | `gcloud dns policies describe` |
| DNSSEC key management | partial | `gcloud dns dns-keys list` |
| Response policies | yes | `gcloud dns response-policies` |
| Import/export zone files | yes | `gcloud dns record-sets import/export` |

## Command Map

| Goal | Example `gcloud` invocation | Notes |
|------|---------------------------|-------|
| Create public zone | `gcloud dns managed-zones create NAME --dns-name=DOMAIN --description=DESC --visibility=public --project=PROJECT --format=json` | JSON output |
| Create private zone | `gcloud dns managed-zones create NAME --dns-name=DOMAIN --visibility=private --networks=NETWORK --project=PROJECT --format=json` | Requires VPC |
| Describe zone | `gcloud dns managed-zones describe NAME --project=PROJECT --format=json` | JSON output |
| List zones | `gcloud dns managed-zones list --project=PROJECT --format=json` | JSON output |
| Filter zones | `gcloud dns managed-zones list --project=PROJECT --filter="visibility=public" --format=json` | Filter by visibility |
| Update zone | `gcloud dns managed-zones update NAME --description=NEW_DESC --project=PROJECT --format=json` | JSON output |
| Delete zone | `gcloud dns managed-zones delete NAME --project=PROJECT` | Interactive confirmation |
| Start transaction | `gcloud dns record-sets transaction start --zone=ZONE` | Creates transaction.yaml |
| Add record | `gcloud dns record-sets transaction add NAME --type=TYPE --ttl=TTL --rrdatas=DATA --zone=ZONE` | To transaction |
| Remove record | `gcloud dns record-sets transaction remove NAME --type=TYPE --ttl=TTL --rrdatas=DATA --zone=ZONE` | From transaction |
| Describe transaction | `gcloud dns record-sets transaction describe --zone=ZONE` | View pending changes |
| Execute transaction | `gcloud dns record-sets transaction execute --zone=ZONE --project=PROJECT --format=json` | Apply changes |
| List records | `gcloud dns record-sets list --zone=ZONE --project=PROJECT --format=json` | JSON output |
| Describe record | `gcloud dns record-sets describe NAME --type=TYPE --zone=ZONE --project=PROJECT --format=json` | JSON output |
| List zone ops | `gcloud dns managed-zone operations list --zone=ZONE --project=PROJECT --format=json` | JSON output |
| List policies | `gcloud dns policies list --project=PROJECT --format=json` | JSON output |
| Describe policy | `gcloud dns policies describe POLICY_NAME --project=PROJECT --format=json` | JSON output |
| Import zone file | `gcloud dns record-sets import ZONE_FILE --zone=ZONE --project=PROJECT` | BIND format |
| Export zone file | `gcloud dns record-sets export ZONE_FILE --zone=ZONE --project=PROJECT` | BIND format |

## Record-Set Transaction Workflow

The transaction API ensures atomic record-set changes:

```bash
# 1. Start transaction (creates transaction.yaml in current directory)
gcloud dns record-sets transaction start --zone="{{user.zone_name}}"

# 2. Add/remove records (modifies transaction.yaml)
gcloud dns record-sets transaction add "www.{{user.dns_name}}" \
  --type="A" --ttl="300" --rrdatas="192.0.2.1" \
  --zone="{{user.zone_name}}"

# 3. Review pending changes
gcloud dns record-sets transaction describe --zone="{{user.zone_name}}"

# 4. Execute (applies atomically)
gcloud dns record-sets transaction execute \
  --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Important:** Only one active transaction per directory. Aborted transactions require cleanup:
```bash
rm -f transaction.yaml
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (API failure, invalid input) |
| 2 | Invalid arguments or missing required flags |
| 130 | Interrupted (Ctrl+C) |

## Diagnostic Logging

All gcloud commands support verbose output:
```bash
gcloud dns managed-zones list --verbosity=debug --log-http
```

> **Warning:** `--log-http` may expose credential values. Do not use in production logs.
