# Validation Scripts for CI/CD

> Standalone validation scripts for Terraform CI/CD pipelines: format checking, validation, security scanning, and unit testing.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Validation Script Suite](#validation-script-suite)
4. [terraform fmt Check](#terraform-fmt-check)
5. [terraform validate](#terraform-validate)
6. [Checkov Security Scanning](#checkov-security-scanning)
7. [Terratest Unit Testing](#terratest-unit-testing)
8. [CI/CD Integration Examples](#cicd-integration-examples)
9. [See Also](#see-also)

## Overview

This runbook provides a comprehensive validation suite for Terraform configurations in CI/CD pipelines. Each validation step is independent and can be run standalone or as part of a pipeline.

## Prerequisites

```bash
# Install tools
brew install checkov terraform terratest          # macOS
# or: pip install checkov
# terraform and go for terratest

# Verify installations
terraform version
checkov --version
go version
```

## Validation Script Suite

### Unified Validation Runner

```bash
#!/bin/bash
# validate-terraform.sh — Run all validations

set -euo pipefail

TERRAFORM_DIR="${1:-.}"
EXIT_CODE=0

echo "=== Terraform Validation Suite ==="

# 1. Format check
echo ""
echo "[1/4] Running terraform fmt check..."
if ! terraform fmt -check -recursive "$TERRAFORM_DIR"; then
    echo "WARN: Format issues found. Run 'terraform fmt -recursive' to fix."
    EXIT_CODE=1
fi

# 2. Validation
echo ""
echo "[2/4] Running terraform validate..."
if ! terraform -chdir="$TERRAFORM_DIR" validate; then
    echo "ERROR: Terraform validation failed."
    EXIT_CODE=1
fi

# 3. Security scan
echo ""
echo "[3/4] Running Checkov security scan..."
if ! checkov -d "$TERRAFORM_DIR" --soft-fail; then
    echo "WARN: Security issues found."
    EXIT_CODE=1
fi

# 4. Unit tests (if Terratest is configured)
echo ""
echo "[4/4] Running Terratest..."
if [ -d "tests/" ]; then
    if ! go test -v ./tests/... 2>/dev/null; then
        echo "WARN: Some tests failed."
        EXIT_CODE=1
    fi
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "=== All validations passed ==="
else
    echo "=== Some validations had warnings ==="
fi

exit $EXIT_CODE
```

## terraform fmt Check

### Format Check Script

```bash
#!/bin/bash
# check-terraform-format.sh

set -euo pipefail

TARGET_DIR="${1:-.}"

echo "Checking Terraform format in: $TARGET_DIR"

# Check if files need formatting
if terraform fmt -check -recursive -diff "$TARGET_DIR"; then
    echo "All files are properly formatted."
    exit 0
else
    echo "Formatting issues found. To fix, run:"
    echo "  terraform fmt -recursive $TARGET_DIR"
    exit 1
fi
```

### GitHub Actions

```yaml
# .github/workflows/terraform-format.yml
name: Terraform Format Check

on:
  pull_request:
    paths:
      - '**.tf'
      - '**.tfvars'

jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0
      - name: Check Format
        run: |
          if terraform fmt -check -recursive; then
            echo "All files properly formatted."
          else
            echo "Formatting issues found."
            terraform fmt -recursive -write=false
            exit 1
          fi
```

## terraform validate

### Validation Script

```bash
#!/bin/bash
# validate-terraform.sh

set -euo pipefail

TERRAFORM_DIR="${1:-.}"

echo "Validating Terraform configuration in: $TERRAFORM_DIR"

# Initialize (skip backend to avoid state operations)
terraform -chdir="$TERRAFORM_DIR" init -backend=false

# Validate
if terraform -chdir="$TERRAFORM_DIR" validate; then
    echo "Validation successful."
    exit 0
else
    echo "Validation failed."
    exit 1
fi
```

### Validate with Variables

```bash
#!/bin/bash
# validate-with-vars.sh

set -euo pipefail

TERRAFORM_DIR="${1:-.}"
TFVARS_FILE="${2:-terraform.tfvars}"

cd "$TERRAFORM_DIR"

# Create override for validation (mock sensitive values)
cat > validate.tfvars <<EOF
project_id = "validate-project"
environment = "validation"
EOF

terraform init -backend=false
terraform validate -var-file="validate.tfvars"

rm -f validate.tfvars
```

## Checkov Security Scanning

### Basic Security Scan

```bash
#!/bin/bash
# security-scan.sh

set -euo pipefail

TARGET_DIR="${1:-.}"

echo "Running Checkov security scan on: $TARGET_DIR"

# Run checkov with output formats
checkov -d "$TARGET_DIR" \
    --output markdown \
    --output-file-path /tmp/checkov-report.md \
    --output json \
    --output-file-path /tmp/checkov-report.json

# Check for BLOCKER/CRITICAL issues
CRITICAL_COUNT=$(jq '[.results.passed_checks[], .results.failed_checks[] | select(.severity == "CRITICAL")] | length' /tmp/checkov-report.json || echo 0)

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "ERROR: Found $CRITICAL_COUNT critical security issues."
    cat /tmp/checkov-report.md | grep -A5 "FAILED"
    exit 1
fi

echo "Security scan passed."
```

### Checkov Configuration

```yaml
# .checkov.yaml
framework:
  - terraform

checks:
  # Disable specific checks if needed
  - CKV_GCP_1: skip
  - CKV_GCP_2: skip

skip_paths:
  - "modules/**/skip.tf"
  - "**/vendor/**"

severity:
  - CRITICAL
  - HIGH
```

### GitHub Actions Security Scan

```yaml
# .github/workflows/security-scan.yml
name: Terraform Security Scan

on:
  pull_request:
    paths:
      - '**.tf'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Checkov
        uses: bridgecrewio/checkov-action@master
        with:
          directory: .
          framework: terraform
          output_format: sarif
          output_path: results.sarif
          soft_fail: true

      - name: Upload results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: results.sarif
```

## Terratest Unit Testing

### Test Structure

```go
// environments/dev/tests/instance_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestTerraformInstance(t *testing.T) {
    terraformOptions := &terraform.Options{
        TerraformDir: "../dev",
        VarFiles:     []string{"terraform.tfvars"},
    }

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    // Get instance details
    instanceName := terraform.Output(t, terraformOptions, "instance_name")
    assert.NotEmpty(t, instanceName)

    // Verify instance exists
    instanceType := terraform.Output(t, terraformOptions, "instance_type")
    assert.Equal(t, "n2-standard-2", instanceType)
}
```

### Running Tests

```bash
# Run all tests
go test -v ./tests/...

# Run specific test
go test -v -run TestTerraformInstance ./tests/...

# Run with coverage
go test -v -cover ./tests/...
```

### Terratest Makefile

```makefile
# Makefile
.PHONY: test test-unit test-integration

test: test-unit test-integration

test-unit:
    go test -v -short ./tests/...

test-integration:
    go test -v ./tests/... -timeout 30m

test-coverage:
    go test -v -coverprofile=coverage.out ./tests/...
    go tool cover -html=coverage.out -o coverage.html
```

## CI/CD Integration Examples

### GitHub Actions (Complete Pipeline)

```yaml
# .github/workflows/terraform-ci.yml
name: Terraform CI

on:
  pull_request:
    paths:
      - 'environments/**'
      - 'modules/**'
      - '**.tf'
      - '**.tfvars'

env:
  TF_VERSION: 1.6.0

jobs:
  validate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        dir: [environments/dev, environments/staging, modules/networking]
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Format
        run: terraform fmt -check -recursive ${{ matrix.dir }}

      - name: Terraform Init
        run: terraform init -backend=false
        working-directory: ${{ matrix.dir }}

      - name: Terraform Validate
        run: terraform validate
        working-directory: ${{ matrix.dir }}

      - name: Security Scan
        uses: bridgecrewio/checkov-action@master
        with:
          directory: ${{ matrix.dir }}
          soft_fail: true

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'

      - name: Run Terratest
        run: go test -v ./tests/...
        working-directory: environments/dev
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - test
  - scan

terraform:validate:
  stage: validate
  image:
    name: hashicorp/terraform:1.6.0
    entrypoint: [""]
  script:
    - terraform init -backend=false
    - terraform validate
    - terraform fmt -check -recursive
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

terratest:
  stage: test
  image:
    name: golang:1.21
    entrypoint: [""]
  script:
    - go mod download
    - go test -v ./tests/...
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

checkov:
  stage: scan
  image:
    name: bridgecrewio/checkov:latest
    entrypoint: [""]
  script:
    - checkov -d . --soft-fail
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## See Also

- [terraform fmt documentation](https://developer.hashicorp.com/terraform/cli/commands/fmt)
- [terraform validate documentation](https://developer.hashicorp.com/terraform/cli/commands/validate)
- [Checkov Terraform scanning](https://www.checkov.io/1.Introduction/Variables.html)
- [Terratest documentation](https://terratest.gruntwork.io/docs/)
- [Execution Flows](../execution-flows.md)
