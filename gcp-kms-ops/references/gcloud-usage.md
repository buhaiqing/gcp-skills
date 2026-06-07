# gcloud Usage — Cloud KMS

## Overview

`gcloud kms` is the primary CLI interface for Cloud KMS. All commands support `--format=json` for machine parsing.

## Conventions

| Convention | Rule |
|--------|------|
| Output | Always use `--format=json` |
| Project | Set via `CLOUDSDK_CORE_PROJECT` or `--project` |
| Location | `global` by default; use `--location` for region-specific keys |
| Resource hierarchy | Project → Location → KeyRing → CryptoKey → CryptoKeyVersion |

## Command Map

### Key Rings

| Operation | Command |
|----------|---------|
| Create | `gcloud kms keyrings create NAME --location=LOC` |
| Describe | `gcloud kms keyrings describe NAME --location=LOC` |
| List | `gcloud kms keyrings list --location=LOC` |
| IAM Get | `gcloud kms keyrings get-iam-policy NAME --location=LOC` |
| IAM Set | `gcloud kms keyrings set-iam-policy NAME POLICY --location=LOC` |

### Crypto Keys

| Operation | Command |
|----------|---------|
| Create | `gcloud kms keys create NAME --keyring=KR --location=LOC --purpose=PURPOSE` |
| Describe | `gcloud kms keys describe NAME --keyring=KR --location=LOC` |
| List | `gcloud kms keys list --keyring=KR --location=LOC` |
| Update | `gcloud kms keys update NAME --keyring=KR --location=LOC --rotation-period=PERIOD` |
| Add IAM | `gcloud kms keys add-iam-policy-binding NAME --keyring=KR --location=LOC` |
| Remove IAM | `gcloud kms keys remove-iam-policy-binding NAME --keyring=KR --location=LOC` |

### Key Versions

| Operation | Command |
|----------|---------|
| List | `gcloud kms keys versions list --key=KEY --keyring=KR --location=LOC` |
| Describe | `gcloud kms keys versions describe VERSION --key=KEY --keyring=KR --location=LOC` |
| Create | `gcloud kms keys versions create --key=KEY --keyring=KR --location=LOC` |
| Destroy | `gcloud kms keys versions destroy VERSION --key=KEY --keyring=KR --location=LOC` |
| Restore | `gcloud kms keys versions restore VERSION --key=KEY --keyring=KR --location=LOC` |
| Enable | `gcloud kms keys versions enable VERSION --key=KEY --keyring=KR --location=LOC` |
| Disable | `gcloud kms keys versions disable VERSION --key=KEY --keyring=KR --location=LOC` |

### Crypto Operations

| Operation | Command |
|----------|---------|
| Encrypt | `gcloud kms encrypt --key=KEY --keyring=KR --location=LOC --plaintext-file=IN --ciphertext-file=OUT` |
| Decrypt | `gcloud kms decrypt --key=KEY --keyring=KR --location=LOC --ciphertext-file=IN --plaintext-file=OUT` |
| Sign | `gcloud kms sign --key=KEY --keyring=KR --location=LOC --message-file=FILE --digest-algorithm=ALGO` |
| Verify | `gcloud kms verify --key=KEY --keyring=KR --location=LOC --signature-file=FILE --message-file=FILE` |

### Import

| Operation | Command |
|----------|---------|
| Create import job | `gcloud kms import-jobs create NAME --keyring=KR --location=LOC --import-method=METHOD --protection-level=LEVEL` |
| List import jobs | `gcloud kms import-jobs list --keyring=KR --location=LOC` |
| Import key version | `gcloud kms keys versions import --key=KEY --keyring=KR --location=LOC --import-job=JOB` |

## CLI vs API Coverage

| Resource | gcloud Coverage | Notes |
|----------|----------------|-------|
| Key Rings | Full | create, describe, list, IAM |
| Crypto Keys | Full | create, describe, list, update, IAM |
| Key Versions | Full | create, list, describe, destroy, restore, enable, disable, import |
| Encrypt/Decrypt | Full | encrypt, decrypt, sign, verify |
| Import | Full | import-jobs create/list, key import |