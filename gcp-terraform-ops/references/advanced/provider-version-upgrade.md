# Provider Version Upgrade Runbook

> Provider version upgrade procedures: `terraform init -upgrade`, state migration, breaking change detection, and rollback procedures.

## Table of Contents

1. [Overview](#overview)
2. [Pre-upgrade Checklist](#pre-upgrade-checklist)
3. [Upgrade Process](#upgrade-process)
4. [Breaking Change Detection](#breaking-change-detection)
5. [State Migration](#state-migration)
6. [Rollback Procedures](#rollback-procedures)
7. [GCP Provider Version Reference](#gcp-provider-version-reference)
8. [Common Issues](#common-issues)
9. [See Also](#see-also)

## Overview

Provider upgrades require careful planning to avoid breaking existing infrastructure. This runbook covers the complete lifecycle of upgrading the `hashicorp/google` provider while maintaining infrastructure stability.

### When to Upgrade

| Trigger | Rationale |
|---------|-----------|
| Security advisory | CVE in current provider version |
| New GCP feature needed | Required resource/resource attribute |
| GCP API deprecation | Old provider doesn't support current API |
| Terraform version upgrade | New Terraform requires newer provider |

## Pre-upgrade Checklist

```bash
# 1. Record current state
terraform version
terraform providers
terraform state list > state-before-upgrade.txt

# 2. Backup state
terraform state pull > backup-state-$(date +%Y%m%d-%H%M%S).json

# 3. Document current configuration
grep -r "required_providers" environments/

# 4. Check for custom provider configurations
grep -r "provider " environments/ modules/
```

### Required Access

```bash
# Verify GCP credentials are current
gcloud auth list
gcloud auth application-default login

# Verify project access
gcloud projects describe $CLOUDSDK_CORE_PROJECT
```

## Upgrade Process

### Step 1: Update Provider Version

```hcl
# versions.tf
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"  # Update this version
    }
  }
}
```

### Step 2: Run terraform init with Upgrade

```bash
# Upgrade providers
terraform init -upgrade

# Expected output:
# Upgrading modules...
# - google provider
# Downloading google provider 5.x.x...
```

### Step 3: Validate Configuration

```bash
# Re-validate all environments
for env in dev staging prod; do
  echo "Validating $env..."
  terraform -chdir="environments/$env" validate
done
```

### Step 4: Plan with New Provider

```bash
# Plan each environment (no apply yet)
cd environments/dev/
terraform plan -out=new-provider.tfplan

# Review plan output for:
# - Expected resource changes
# - Any unexpected destroys
# - Provider-level changes
```

## Breaking Change Detection

### Automated Detection with tfproviderlint

```bash
# Install tfproviderlint
go install github.com/bflad/tfproviderlint/cmd/tfproviderlint@latest

# Run breaking change detection
tfproviderlint ./...

# Check for specific version upgrades
tfproviderlint -set . -ignore服务商=hashicorp/google
```

### Compare Plan Outputs

```bash
#!/bin/bash
# compare-plans.sh — Compare plans before/after upgrade

set -euo pipefail

OLD_PROVIDER_VERSION="4.0.0"
NEW_PROVIDER_VERSION="5.0.0"

echo "Comparing provider plans: $OLD_PROVIDER_VERSION -> $NEW_PROVIDER_VERSION"

# Generate plan with old provider
git checkout v$OLD_PROVIDER_VERSION
terraform init -upgrade
terraform plan -out=old-plan.tfplan

# Generate plan with new provider
git checkout v$NEW_PROVIDER_VERSION
terraform init -upgrade
terraform plan -out=new-plan.tfplan

# Diff plans
diff old-plan.tfplan new-plan.tfplan || true
```

### Common Breaking Changes in GCP Provider v5

| Change | Impact | Mitigation |
|--------|--------|------------|
| Default value changes | May trigger updates | Review plan output |
| Removed deprecated attributes | Requires HCL update | Update configuration |
| Validation stricter | May fail validation | Fix validation rules |
| Resource schema changes | State migration | Follow migration guide |

### Check Provider Changelog

```bash
# View provider changelog
# https://github.com/hashicorp/terraform-provider-google/blob/main/CHANGELOG.md

# Or via GitHub API
curl -s https://api.github.com/repos/hashicorp/terraform-provider-google/releases \
  | jq '.[] | {tag_name, body}'
```

## State Migration

### Automatic State Migration

Terraform handles most state migrations automatically during `terraform init`. The provider reads the existing state and updates its internal representation to match the new schema.

```bash
# State migration is automatic during init
terraform init -upgrade

# Verify state after migration
terraform state list
terraform state pull | jq '.resources[] | {type, name}'
```

### Manual State Surgery (if needed)

```bash
# Inspect current state
terraform state pull | jq '.resources[] | select(.type == "google_sql_database_instance")'

# Rename resource in state (if resource type changed)
terraform state mv \
  google_sql_database_instance.old_type \
  google_sql_database_instance.new_type

# Remove orphaned state (resource no longer exists)
terraform state rm google_deleted_resource.instance_name
```

### State Version Compatibility

```bash
# Check Terraform state version
terraform state pull | jq '.terraform_version'

# State format version by Terraform version
# Terraform 1.6+ uses state format version 4
```

## Rollback Procedures

### Rollback Provider Version

```bash
# Option 1: Use version constraint
# versions.tf
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"  # Revert to old version
    }
  }
}

# Option 2: Pin exact version
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.85.0"  # Pin exact version
    }
  }
}

# Re-initialize
terraform init -upgrade
```

### Restore State from Backup

```bash
# List backup files
ls -la backup-state-*.json

# Restore from backup
terraform state push backup-state-20240115-103000.json

# Verify restored state
terraform state list
terraform plan
```

### Rollback Script

```bash
#!/bin/bash
# rollback-provider.sh

set -euo pipefail

BACKUP_FILE="${1:-}"
PROVIDER_VERSION="${2:-4.85.0}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file> <provider-version>"
    exit 1
fi

echo "Rolling back provider to $PROVIDER_VERSION"
echo "Using backup: $BACKUP_FILE"

# Update versions.tf
sed -i.bak "s/version = \".*\"/version = \"$PROVIDER_VERSION\"/" versions.tf

# Restore state
terraform state push "$BACKUP_FILE"

# Re-init
terraform init -upgrade

# Verify
terraform version
terraform providers

# Plan to verify
terraform plan
```

## GCP Provider Version Reference

### Version Compatibility Matrix

| Terraform | GCP Provider |
|-----------|--------------|
| 1.6+ | 5.0+ |
| 1.5+ | 4.0+ |
| 1.0+ | 3.0+ |

### Recommended Versions (as of 2026)

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.36"  # Latest stable
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.36"
    }
  }
}
```

### Beta Provider

```hcl
# Use beta provider for preview features
provider "google-beta" {
  project = var.project_id
}
```

## Common Issues

### Issue: Provider version conflict

```
Error: Provider requirement conflict
```

**Solution**: Ensure only one version constraint exists per provider

```bash
# Check for duplicate provider definitions
grep -r "required_providers" environments/ modules/
```

### Issue: Locked provider download

```
Error: Failed to query provider
```

**Solution**: Clear provider cache

```bash
rm -rf .terraform
terraform init
```

### Issue: State schema mismatch

```
Error: Provider produced inconsistent result
```

**Solution**: Re-import affected resources

```bash
# Identify affected resources
terraform plan 2>&1 | grep "inconsistent"

# Re-import each affected resource
terraform import google_resource.type/name resource-id
```

### Issue: Validation errors after upgrade

```
Error: Expected value for attribute
```

**Solution**: Update HCL to match new validation rules

```bash
# Identify validation failures
terraform validate

# Fix each validation error
# (often due to stricter type checking in new provider)
```

## See Also

- [GCP Provider Releases](https://github.com/hashicorp/terraform-provider-google/releases)
- [Terraform Provider Versioning](https://developer.hashicorp.com/terraform/language/providers/versioning)
- [State Management](../execution-flows.md#operation-terraform-state)
- [Troubleshooting](../troubleshooting.md)
