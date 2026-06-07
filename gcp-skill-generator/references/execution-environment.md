# Execution Environment Setup

> **Purpose:** Detailed environment setup for executing `gcloud` CLI and JIT SDK (Python primary, Go secondary) operations. This file provides progressive depth for the [gcp-skill-generator](../SKILL.md) meta-skill.
> **Version:** 3.0.0
> **Last Updated:** 2026-06-07
> **Note:** gcloud CLI is **Python-based** (not a static Go binary like aliyun). It bundles a Python runtime, `gsutil`, and `bq`. Install size ~200MB.
> **SDK preference: Python SDK (primary) > Go SDK (secondary).** Python SDK requires no extra runtime (gcloud provides Python 3.8+); Go SDK needs ~150MB JIT download.

---

## Table of Contents

1. [CLI-First with JIT SDK Fallback (Python > Go)](#1-cli-first-with-jit-sdk-fallback-python--go)
2. [Phase 1: Probe — Detect Existing gcloud](#2-phase-1-probe--detect-existing-gcloud)
3. [Phase 2: Install — Idempotent Multi-Path Install](#3-phase-2-install--idempotent-multi-path-install)
4. [Phase 3: Verify — Post-Install Validation](#4-phase-3-verify--post-install-validation)
5. [Phase 4: Auth — Idempotent Auth Setup](#5-phase-4-auth--idempotent-auth-setup)
6. [Phase 5: Components — Idempotent Component Management](#6-phase-5-components--idempotent-component-management)
7. [Docker gcloud (Zero-Install Fallback)](#7-docker-gcloud-zero-install-fallback)
8. [Cloud Shell (Zero-Install Fallback)](#8-cloud-shell-zero-install-fallback)
9. [JIT Python SDK (Primary) & Go SDK (Secondary)](#9-jit-python-sdk-primary--go-sdk-secondary)
10. [Credential Configuration](#10-credential-configuration)
11. [Credential Security (Mandatory)](#11-credential-security-mandatory)
12. [Full Idempotent Bootstrap Script](#12-full-idempotent-bootstrap-script)
13. [Environment Variable Sources](#13-environment-variable-sources)

---

## 1. CLI-First with JIT SDK Fallback (Python > Go)

The execution environment follows a **CLI-first with JIT SDK fallback** strategy, using **Python SDK as primary fallback**, Go SDK as secondary:

1. **Primary path:** `gcloud` CLI (Google Cloud SDK, Python-based, covers 90%+ APIs)
2. **Fallback path 1:** Python SDK (`google-cloud-*`) — zero extra runtime (Python 3.8+ already required by gcloud)
3. **Fallback path 2:** Go SDK (`cloud.google.com/go/...`) — JIT download if Python unavailable or user prefers Go
4. **Ultimate fallback:** Docker `google/cloud-sdk` image or Cloud Shell

### Why Python SDK First?

| Aspect | Python SDK | Go SDK |
|--------|-----------|--------|
| Runtime dep | Python 3.8+ (already required by gcloud) | Go (~150MB JIT download) |
| Cold start | `pip install` ~3-8s | `go mod tidy + go build` ~15-30s |
| Code size | ~5-15 lines per snippet | ~30-50 lines (imports, types, errcheck) |
| Readability | `client.list(...)` direct | `resp, err := client.List(ctx, req)` verbose |
| gcloud CLI alignment | Same language, same patterns | Different language |
| Type safety | Runtime | Compile-time |

**Decision rule:**
- Python 3.8+ available → use Python SDK (default)
- Python unavailable or operation requires compile-time type safety → use Go SDK
- Neither available → Docker gcloud or Cloud Shell

### Additional Tools

| Tool | Purpose | Install Method |
|------|---------|----------------|
| `gsutil` | Cloud Storage operations | Bundled with gcloud SDK |
| `bq` | BigQuery operations | Bundled with gcloud SDK |
| `kubectl` | GKE operations | `gcloud components install kubectl` |
| `jq` | JSON path extraction | `apt-get install jq` or `brew install jq` |

---

## 2. Idempotent Install Philosophy

> **Core pattern:** Probe → Install (if missing) → Verify — never install unconditionally.

```bash
# ── Idempotent install pattern ──
# 1. Probe
[HH:MM:SS] [DIAG] gcloud_path=$(which gcloud 2>/dev/null)  → found or not
[HH:MM:SS] [DIAG] gcloud_version=$(gcloud version --format="json" 2>/dev/null) → version or empty

# 2. Install (only if probe found nothing)
if [ -z "$gcloud_path" ]; then
    [HH:MM:SS] [INSTALL] method=apt  # or brew / docker / manual
    ...
fi

# 3. Verify
[HH:MM:SS] [RESULT] gcloud="$(gcloud version 2>&1 | head -1)"
```

### Structured Diagnostic Log Format (MANDATORY for all remote scripts)

All install scripts MUST use `[HH:MM:SS] [PHASE] key=value` format:

| PHASE | Meaning | Example |
|-------|---------|---------|
| `DIAG` | Probe / environment snapshot | `[DIAG] gcloud_path=/usr/bin/gcloud` |
| `INSTALL` | Installation action | `[INSTALL] method=apt source=cloud-sdk` |
| `EXEC` | Command being run | `[EXEC] gcloud components install kubectl --quiet` |
| `RESULT` | Key outcome | `[RESULT] GCLOUD_INSTALL=SUCCESS` |
| `WARN` | Warning | `[WARN] gcloud found at /snap/bin but not in PATH` |
| `ERROR` | Error with TYPE + FIX | `[ERROR] TYPE=DOWNLOAD_FAILED FIX=Switch to Docker` |
| `SUMMARY` | Final result | `[SUMMARY] Method=apt Version=487.0.0 Status=READY` |

Error format: `[ERROR] TYPE={category} FIX={one-line action}`

---

## 3. Phase 1: Probe — Detect Existing gcloud

> **Probe before install.** Run this before any install attempt. Never install unconditionally.

```bash
[HH:MM:SS] [DIAG] PHASE=gcloud-probe
```

### 2.1 Check PATH

```bash
GCLOUD_PATH=$(command -v gcloud 2>/dev/null || true)
if [ -n "$GCLOUD_PATH" ]; then
    [HH:MM:SS] [DIAG] gcloud_path=$GCLOUD_PATH
    GCLOUD_VER=$(gcloud version --format="json" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Google Cloud SDK','unknown'))" 2>/dev/null || echo "unknown")
    [HH:MM:SS] [DIAG] gcloud_version=$GCLOUD_VER
else
    [HH:MM:SS] [DIAG] gcloud_path=NOT_FOUND
fi
```

### 2.2 Check alternative install locations

```bash
# Check common non-PATH locations
for loc in \
    "/snap/bin/gcloud" \
    "/usr/lib/google-cloud-sdk/bin/gcloud" \
    "/opt/google-cloud-sdk/bin/gcloud" \
    "$HOME/google-cloud-sdk/bin/gcloud" \
    "$HOME/.local/google-cloud-sdk/bin/gcloud"; do
    if [ -x "$loc" ]; then
        [HH:MM:SS] [DIAG] gcloud_alt=$loc
    fi
done
```

### 2.3 Check Docker

```bash
if command -v docker &>/dev/null; then
    DOCKER_GCLOUD=$(docker images google/cloud-sdk -q 2>/dev/null | head -1)
    [HH:MM:SS] [DIAG] docker_gcloud_available=$([ -n "$DOCKER_GCLOUD" ] && echo YES || echo NO)
fi
```

### 2.4 Check Python (gcloud SDK requires Python 3.8+)

```bash
if command -v python3 &>/dev/null; then
    PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}')
    [HH:MM:SS] [DIAG] python_version=$PYTHON_VER
    # gcloud SDK requires Python 3.8+
    if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
        [HH:MM:SS] [DIAG] python_compatible=YES
    else
        [HH:MM:SS] [WARN] python_version=$PYTHON_VER requires>=3.8
    fi
else
    [HH:MM:SS] [DIAG] python3=NOT_FOUND
fi
```

### 2.5 Check CLOUDSDK_CORE_PROJECT

GCP 项目可以来自环境变量或 gcloud 配置，必须二选一，不能两者皆空。这是使用 `gcloud` 的前提条件。

```bash
PROJECT="${CLOUDSDK_CORE_PROJECT:-$(gcloud config get-value core/project 2>/dev/null || true)}"
if [ -z "$PROJECT" ]; then
    [HH:MM:SS] [ERROR] TYPE=PROJECT_NOT_SET FIX="export CLOUDSDK_CORE_PROJECT=<project-id> or gcloud config set project <project-id>"
fi
```

### Probe Result Decision Table

| gcloud found | Python 3.8+ | Docker avail | Recommended Path |
|:---:|:---:|:---:|-----------------|
| ✅ | ✅ | — | Use existing gcloud |
| ❌ | ❌ | ✅ | Docker gcloud |
| ❌ | ✅ | — | Install SDK (non-interactive) |
| ❌ | ❌ | ❌ | Cloud Shell or JIT Go SDK |
| ✅ | ❌ | — | Docker gcloud (Python too old) |

---

## 4. Phase 2: Install — Idempotent Multi-Path Install

> Priority order: ① existing gcloud → ② apt/snap → ③ brew → ④ SDK manual → ⑤ Docker → ⑥ Cloud Shell

### Path A: Linux — apt (Debian/Ubuntu)

**Idempotent**: `apt-get install -y` is idempotent — if installed, it's a no-op.

```bash
install_gcloud_apt() {
    [HH:MM:SS] [INSTALL] method=apt source=cloud-sdk
    # 1. Ensure apt-transport-https
    sudo apt-get update -qq && sudo apt-get install -y -qq apt-transport-https ca-certificates gnupg curl

    # 2. Add Google Cloud GPG key (idempotent: check before download)
    if [ ! -f /usr/share/keyrings/cloud.google.gpg ]; then
        curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
            sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
    fi

    # 3. Add Google Cloud SDK repo (idempotent: check before append)
    REPO_FILE="/etc/apt/sources.list.d/google-cloud-sdk.list"
    REPO_LINE="deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main"
    if [ ! -f "$REPO_FILE" ] || ! grep -q "cloud-sdk" "$REPO_FILE" 2>/dev/null; then
        echo "$REPO_LINE" | sudo tee "$REPO_FILE" >/dev/null
    fi

    # 4. Install (idempotent)
    sudo apt-get update -qq && sudo apt-get install -y -qq google-cloud-sdk
}
```

### Path B: Linux — snap (Ubuntu, no apt repo needed)

```bash
install_gcloud_snap() {
    [HH:MM:SS] [INSTALL] method=snap
    if command -v snap &>/dev/null; then
        sudo snap install google-cloud-sdk --classic --quiet 2>/dev/null || \
            sudo snap refresh google-cloud-sdk --quiet 2>/dev/null
    fi
}
```

### Path C: macOS — Homebrew

**Idempotent**: `brew install` is idempotent.

```bash
install_gcloud_brew() {
    [HH:MM:SS] [INSTALL] method=brew
    if ! command -v brew &>/dev/null; then
        [HH:MM:SS] [ERROR] TYPE=BREW_NOT_FOUND FIX=Install Homebrew or use Docker
        return 1
    fi
    # brew install is idempotent — if installed, it's a no-op
    brew install --quiet google-cloud-sdk 2>/dev/null
    # Ensure brew binary links
    brew link --overwrite google-cloud-sdk 2>/dev/null || true
}
```

### Path D: Manual — Download SDK Archive

**Idempotent**: Check directory existence before download.

```bash
install_gcloud_manual() {
    local INSTALL_DIR="${1:-/tmp/google-cloud-sdk}"
    [HH:MM:SS] [INSTALL] method=manual target=$INSTALL_DIR

    # Idempotent check: skip if already installed at target
    if [ -x "$INSTALL_DIR/bin/gcloud" ]; then
        [HH:MM:SS] [DIAG] gcloud_already_installed_at=$INSTALL_DIR
        export PATH="$INSTALL_DIR/bin:$PATH"
        return 0
    fi

    # Detect OS/ARCH
    local OS ARCH
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64) ARCH="x86_64" ;;
        aarch64|arm64) ARCH="arm" ;;
        *) [HH:MM:SS] [ERROR] TYPE=UNSUPPORTED_ARCH FIX="Use Docker gcloud instead"; return 1 ;;
    esac

    # Map OS to gcloud archive name
    local GCLOUD_OS
    case "$OS" in
        linux) GCLOUD_OS="linux" ;;
        darwin) GCLOUD_OS="darwin" ;;
        *) [HH:MM:SS] [ERROR] TYPE=UNSUPPORTED_OS FIX="Use Docker gcloud instead"; return 1 ;;
    esac

    # Download latest stable SDK (with retry)
    local SDK_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${GCLOUD_OS}-${ARCH}.tar.gz"
    local TMP_FILE="/tmp/gcloud-sdk.tar.gz"

    [HH:MM:SS] [INSTALL] downloading=$SDK_URL
    for i in 1 2 3; do
        if curl -fsSL --connect-timeout 30 --max-time 120 "$SDK_URL" -o "$TMP_FILE" 2>/dev/null; then
            break
        fi
        [HH:MM:SS] [WARN] download_attempt=$i status=FAILED retrying=true
        sleep 3
    done

    if [ ! -f "$TMP_FILE" ] || [ ! -s "$TMP_FILE" ]; then
        [HH:MM:SS] [ERROR] TYPE=DOWNLOAD_FAILED FIX="Use Docker gcloud instead"
        return 1
    fi

    # Extract
    mkdir -p "$INSTALL_DIR"
    tar -xzf "$TMP_FILE" -C "$INSTALL_DIR" 2>/dev/null
    rm -f "$TMP_FILE"

    # Run installer in quiet non-interactive mode
    if [ -x "$INSTALL_DIR/google-cloud-sdk/install.sh" ]; then
        "$INSTALL_DIR/google-cloud-sdk/install.sh" --quiet --usage-reporting false --additional-components "" 2>/dev/null
    fi

    export PATH="$INSTALL_DIR/google-cloud-sdk/bin:$PATH"
    [HH:MM:SS] [RESULT] GCLOUD_INSTALL=SUCCESS
}
```

### Path E: Docker gcloud (Zero-Install)

gcloud SDK is Python-based (~200MB), making it heavy to download. Docker is the **fastest zero-install path**:

```bash
install_gcloud_docker() {
    [HH:MM:SS] [INSTALL] method=docker
    if ! command -v docker &>/dev/null; then
        [HH:MM:SS] [ERROR] TYPE=DOCKER_NOT_FOUND FIX="Install Docker or use Cloud Shell"
        return 1
    fi
    # Idempotent: pull is idempotent
    docker pull google/cloud-sdk:latest --quiet 2>/dev/null
    [HH:MM:SS] [RESULT] DOCKER_IMAGE_READY=YES
}
```

Usage (alias):
```bash
gcloud() {
    docker run --rm -i \
        -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/sa.json:ro" \
        -e CLOUDSDK_CORE_PROJECT \
        -e CLOUDSDK_COMPUTE_ZONE \
        google/cloud-sdk:latest \
        gcloud "$@"
}
```

### Install Decision Tree

```
[Probe: gcloud found?]
  ├── YES → [Verify version ≥ min] → SKIP INSTALL
  │            ├── YES → READY
  │            └── NO  → [Python 3.8+ available?]
  │                         ├── YES → upgrade: gcloud components update --quiet
  │                         └── NO  → Docker gcloud (recommended)
  └── NO  → [Docker available?]
              ├── YES → docker pull google/cloud-sdk + alias
              └── NO  → [apt/snap/brew available?]
                          ├── YES → install via package manager
                          └── NO  → [Python 3.8+ available?]
                                      ├── YES → manual SDK download
                                      └── NO  → Cloud Shell / JIT Go SDK fallback
```

---

## 5. Phase 3: Verify — Post-Install Validation

```bash
verify_gcloud() {
    [HH:MM:SS] [DIAG] PHASE=post-install-verify

    # 1. Binary check
    if ! command -v gcloud &>/dev/null; then
        [HH:MM:SS] [ERROR] TYPE=GCLOUD_NOT_IN_PATH FIX="export PATH to include gcloud binary"
        return 1
    fi
    [HH:MM:SS] [RESULT] gcloud_binary=PRESENT

    # 2. Version check
    GCLOUD_VER=$(gcloud version --format="json" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Google Cloud SDK','unknown'))" 2>/dev/null || echo "unknown")
    [HH:MM:SS] [RESULT] gcloud_version=$GCLOUD_VER

    # 3. Python check (gcloud bundles its own Python, but verify it works)
    if gcloud version 2>&1 | grep -qi "python"; then
        [HH:MM:SS] [WARN] gcloud_python_check=see-output-above
    fi

    # 4. Components (core)
    if gcloud components list --format="json" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('gcloud' in [c['id'] for c in d.get('components',[])])" 2>/dev/null | grep -q True; then
        [HH:MM:SS] [RESULT] gcloud_core_component=PRESENT
    else
        [HH:MM:SS] [ERROR] TYPE=CORE_COMPONENT_MISSING FIX="gcloud components install core --quiet"
    fi

    [HH:MM:SS] [SUMMARY] install_method=$METHOD gcloud_version=$GCLOUD_VER status=$(command -v gcloud &>/dev/null && echo READY || echo FAILED)
}
```

### Exit Code Convention

| ExitCode | Meaning | Agent Action | Human Intervention |
|:--------:|---------|-------------|:------------------:|
| 0 | gcloud ready | Proceed with target operation | No |
| 10 | gcloud not found | Auto-install (preferred path) | No |
| 11 | Python 3.8+ missing | Fallback to Docker gcloud | No |
| 12 | Download failed | Retry with mirror / switch to Docker | No |
| 20 | All install paths failed | HALT — suggest Cloud Shell | Yes |
| 21 | Auth not configured | Guide user through auth | Yes |

---

## 6. Phase 4: Auth — Idempotent Auth Setup

> **Pattern:** Check → Configure (if missing) → Verify.

```bash
setup_auth_idempotent() {
    [HH:MM:SS] [DIAG] PHASE=auth-setup

    # 1. Check existing auth
    if gcloud auth application-default print-access-token --quiet &>/dev/null; then
        [HH:MM:SS] [RESULT] ADC=ALREADY_CONFIGURED
        return 0
    fi

    # 2. Check SA key env
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        [HH:MM:SS] [INSTALL] auth_method=SA_KEY
        gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" --quiet 2>/dev/null
        gcloud config set project "${CLOUDSDK_CORE_PROJECT:-$(gcloud config get-value project 2>/dev/null)}" --quiet 2>/dev/null
        [HH:MM:SS] [RESULT] ADC=CONFIGURED
        return 0
    fi

    # 3. Check access token
    if [ -n "$CLOUDSDK_AUTH_ACCESS_TOKEN" ]; then
        [HH:MM:SS] [INSTALL] auth_method=ACCESS_TOKEN
        gcloud config set auth/access_token "$CLOUDSDK_AUTH_ACCESS_TOKEN" --quiet 2>/dev/null
        [HH:MM:SS] [RESULT] ADC=CONFIGURED
        return 0
    fi

    # 4. No auth found
    [HH:MM:SS] [ERROR] TYPE=AUTH_NOT_CONFIGURED FIX="export GOOGLE_APPLICATION_CREDENTIALS=<path-to-sa-key>"
    return 1
}
```

### Auth Decision Priority

| Priority | Method | Detection | Env Var |
|:--------:|--------|-----------|---------|
| 1 | SA Key | `test -f "$GOOGLE_APPLICATION_CREDENTIALS"` | `GOOGLE_APPLICATION_CREDENTIALS` |
| 2 | Access Token | `test -n "$CLOUDSDK_AUTH_ACCESS_TOKEN"` | `CLOUDSDK_AUTH_ACCESS_TOKEN` |
| 3 | ADC (gcloud) | `gcloud auth application-default print-access-token` | — |
| 4 | Interactive | Fallback | — |

---

## 7. Phase 5: Components — Idempotent Component Management

> gcloud uses a component model. `gcloud components install` is **idempotent** with `--quiet`.

```bash
install_component_idempotent() {
    local COMPONENT="$1"
    [HH:MM:SS] [INSTALL] component=$COMPONENT

    # Idempotent check: is it already installed?
    local STATUS
    STATUS=$(gcloud components list --format="json" 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); cs=[c for c in d.get('components',[]) if c['id']=='$COMPONENT']; print(cs[0]['state']['name'] if cs else 'NOT_INSTALLED')" 2>/dev/null)

    if [ "$STATUS" = "INSTALLED" ] || [ "$STATUS" = "UPDATED" ]; then
        [HH:MM:SS] [DIAG] component=$COMPONENT state=ALREADY_INSTALLED
        return 0
    fi

    # Install only if missing
    [HH:MM:SS] [INSTALL] component=$COMPONENT action=INSTALL
    gcloud components install "$COMPONENT" --quiet 2>/dev/null
}
```

### Common Components

| Component | Purpose | Install Command |
|-----------|---------|-----------------|
| `kubectl` | GKE | `gcloud components install kubectl --quiet` |
| `gke-gcloud-auth-plugin` | GKE auth | `gcloud components install gke-gcloud-auth-plugin --quiet` |
| `alpha` | Alpha commands | `gcloud components install alpha --quiet` |
| `beta` | Beta commands | `gcloud components install beta --quiet` |
| `cloud-run-proxy` | Cloud Run TCP | `gcloud components install cloud-run-proxy --quiet` |
| `minikube` | Local K8s | `gcloud components install minikube --quiet` |

---

## 8. Docker gcloud (Zero-Install Fallback)

> Since gcloud SDK is Python-based (~200MB), the Docker image is the **fastest zero-install path** for sandbox/CI environments.

### Why Docker gcloud?

| Aspect | Manual SDK Install | Docker |
|--------|-------------------|--------|
| Size | ~200MB download + disk | ~300MB image (pulled once, cached) |
| Python dep | Requires Python 3.8+ on host | Bundled in image |
| Cleanup | Leaves files on host | `--rm` = no trace |
| Idempotent | Complex multi-step | `docker pull` is idempotent |
| Version | Manual upgrade | `docker pull google/cloud-sdk:latest` |

### Docker Wrapper Script

```bash
# ~/bin/gcloud-docker (or alias)
docker_gcloud() {
    local SA_MOUNT=""
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        SA_MOUNT="-v $GOOGLE_APPLICATION_CREDENTIALS:/tmp/sa.json:ro"
        # Also set CLOUDSDK_AUTH_ACCESS_TOKEN if ADC not available in Docker
    fi

    docker run --rm -i \
        $SA_MOUNT \
        -e CLOUDSDK_CORE_PROJECT="${CLOUDSDK_CORE_PROJECT:-}" \
        -e CLOUDSDK_COMPUTE_ZONE="${CLOUDSDK_COMPUTE_ZONE:-}" \
        -e CLOUDSDK_COMPUTE_REGION="${CLOUDSDK_COMPUTE_REGION:-}" \
        -e GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:+ /tmp/sa.json}" \
        google/cloud-sdk:latest \
        gcloud "$@"
}
```

### Docker gcloud Alias (Idempotent Setup)

```bash
setup_gcloud_docker_alias() {
    # Idempotent: pull only if missing
    if ! docker images google/cloud-sdk -q 2>/dev/null | head -1 | grep -q .; then
        docker pull google/cloud-sdk:latest --quiet
    fi

    # Define alias (idempotent: just define, no side effects)
    alias gcloud='docker run --rm -i \
        -v "${GOOGLE_APPLICATION_CREDENTIALS:-/dev/null}:/tmp/sa.json:ro" \
        -e CLOUDSDK_CORE_PROJECT \
        -e CLOUDSDK_COMPUTE_ZONE \
        -e CLOUDSDK_COMPUTE_REGION \
        google/cloud-sdk:latest gcloud'

    [HH:MM:SS] [RESULT] gcloud=via-docker
}
```

### Docker + SA Key Auth

```bash
# One-time auth inside Docker (idempotent: only if not yet configured)
docker run --rm \
    -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/sa.json:ro" \
    google/cloud-sdk:latest \
    gcloud auth activate-service-account --key-file=/tmp/sa.json

# Then run commands
gcloud() {
    docker run --rm -i \
        -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/sa.json:ro" \
        -e CLOUDSDK_CORE_PROJECT \
        google/cloud-sdk:latest \
        gcloud "$@"
}
```

---

## 9. Cloud Shell (Zero-Install Fallback)

> [Cloud Shell](https://shell.cloud.google.com) comes with gcloud pre-installed and pre-authenticated. This is the **ultimate fallback** — zero install, zero config.

### Using Cloud Shell CLI (via curl)

```bash
# Execute a gcloud command in Cloud Shell without any local gcloud install
# Requires: OAuth 2.0 token with cloud-shell scope
curl -s -X POST \
    -H "Authorization: Bearer $(gcloud auth print-access-token 2>/dev/null)" \
    -H "Content-Type: application/json" \
    "https://cloudshell.googleapis.com/v1/users/me/environments/default:start" \
    -d '{}'
```

### Cloud Shell Documentation

| Resource | Link |
|----------|------|
| Cloud Shell | `https://shell.cloud.google.com` |
| Cloud Shell API | `https://cloud.google.com/shell/docs/reference/rest` |
| Pre-installed tools | gcloud, gsutil, bq, kubectl, docker, python3, go, java, node |

### When to Use Cloud Shell

| Scenario | Recommendation |
|----------|---------------|
| Agent runtime without Docker | ✅ Cloud Shell (web or API) |
| Interactive debugging | ✅ Cloud Shell (web UI) |
| Automated CI/CD | ❌ Use SA key + gcloud/Docker |
| Low-latency operations | ❌ Use local gcloud or Docker |

---

## 10. JIT Python SDK (Primary) & Go SDK (Secondary)

When `gcloud` CLI is unavailable or does not support a specific API, fall back to the **Python SDK first**. Only use Go SDK if Python 3.8+ is unavailable.

---

### 10.1 Python SDK (Primary Fallback)

> **Prerequisite:** Python 3.8+ (already required by gcloud CLI). If Python is available, this is the primary fallback.

#### Step 10.1.1: Check Python

```bash
python3 --version
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Step 10.1.2: Install Python SDK (idempotent)

```bash
# Idempotent: pip install is a no-op if already installed
pip install --quiet --user google-cloud-[product] 2>/dev/null || \
    pip3 install --quiet --user google-cloud-[product] 2>/dev/null
```

For Compute Engine:
```bash
pip install --quiet --user google-cloud-compute 2>/dev/null
```

For Cloud SQL:
```bash
pip install --quiet --user google-cloud-sql 2>/dev/null
```

For Cloud Storage:
```bash
pip install --quiet --user google-cloud-storage 2>/dev/null
```

**Pip mirror fallback (for China/restricted networks):**
```bash
pip install --quiet --user -i https://pypi.tuna.tsinghua.edu.cn/simple google-cloud-[product]
```

#### Step 10.1.3: Generate and Run Python Script

```python
# list_instances.py (generated dynamically by Agent)
# REST API equivalent: GET /v1/projects/{project}/zones/{zone}/instances
import os
from google.cloud import compute_v1

def list_instances(project_id: str, zone: str) -> list:
    """List all Compute Engine instances in a zone."""
    client = compute_v1.InstancesClient()
    request = compute_v1.ListInstancesRequest(
        project=project_id,
        zone=zone,
    )
    return list(client.list(request=request))

if __name__ == "__main__":
    project = os.environ["CLOUDSDK_CORE_PROJECT"]
    zone = os.environ.get("CLOUDSDK_COMPUTE_ZONE", "us-central1-a")
    instances = list_instances(project, zone)
    for inst in instances:
        print(f"Instance: {inst.name} (status: {inst.status})")
```

Execute:
```bash
python3 list_instances.py
```

#### Available Python SDK Packages

| GCP Product | Python Package | Import Path |
|-------------|---------------|-------------|
| Compute Engine | `google-cloud-compute` | `google.cloud.compute_v1` |
| Cloud SQL | `google-cloud-sql` | `google.cloud.sql_v1` |
| Cloud Storage | `google-cloud-storage` | `google.cloud.storage` |
| Cloud Run | `google-cloud-run` | `google.cloud.run_v2` |
| GKE | `google-cloud-container` | `google.cloud.container_v1` |
| BigQuery | `google-cloud-bigquery` | `google.cloud.bigquery` |
| Cloud Pub/Sub | `google-cloud-pubsub` | `google.cloud.pubsub_v1` |
| Cloud KMS | `google-cloud-kms` | `google.cloud.kms_v1` |
| Cloud IAM | `google-cloud-iam` | `google.cloud.iam_credentials_v1` |
| VPC / Networking | `google-cloud-compute` | `google.cloud.compute_v1` |
| Cloud Monitoring | `google-cloud-monitoring` | `google.cloud.monitoring_v3` |
| Cloud Logging | `google-cloud-logging` | `google.cloud.logging_v2` |
| Cloud Spanner | `google-cloud-spanner` | `google.cloud.spanner_v1` |
| Bigtable | `google-cloud-bigtable` | `google.cloud.bigtable_v2` |
| Secret Manager | `google-cloud-secret-manager` | `google.cloud.secretmanager_v1` |
| Cloud Functions | `google-cloud-functions` | `google.cloud.functions_v1` |
| Cloud Scheduler | `google-cloud-scheduler` | `google.cloud.scheduler_v1` |
| Cloud DNS | `google-cloud-dns` | `google.cloud.dns_v1` |

> Find all packages at: https://pypi.org/search/?q=google-cloud-

#### Python SDK Script Template (Full)

```python
#!/usr/bin/env python3
# Generated by gcp-skill-generator
# REST API: GET /v1/projects/{project}/...
"""[Product Name] — [Operation] using Python SDK."""

import os
from google.cloud import [product]  # e.g., compute_v1


def run():
    """Execute the operation."""
    # Credentials auto-resolved via GOOGLE_APPLICATION_CREDENTIALS
    client = [product].[ClientClass]()
    project = os.environ["CLOUDSDK_CORE_PROJECT"]
    request = [request_class](project=project)
    response = client.[operation](request=request)
    for item in response:
        print(f"Item: {item.name} (status: {item.status})")


if __name__ == "__main__":
    run()
```

#### Python SDK Execution Time Estimate

| Step | First Run | Subsequent Runs |
|------|-----------|-----------------|
| `pip install` | ~3-8s | ~0.5s (cached) |
| `python3 script.py` | ~1-2s | ~1-2s |
| **Total** | **~5-10s** | **~1-2s** |

---

### 10.2 Go SDK (Secondary Fallback)

> **Use only when:** Python 3.8+ is not available, or the operation requires compile-time type safety for complex request building.

#### Step 10.2.1: Bootstrap Go Runtime

```bash
if command -v go &> /dev/null; then
    GO_VERSION=$(go version | awk '{print $3}')
    GO_MAJOR=$(echo "$GO_VERSION" | sed 's/go//' | cut -d. -f1)
    GO_MINOR=$(echo "$GO_VERSION" | sed 's/go//' | cut -d. -f2)
    if [ "$GO_MAJOR" -ge 1 ] && [ "$GO_MINOR" -ge 21 ]; then
        echo "Compatible Go runtime: $GO_VERSION"
    fi
fi

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
mkdir -p /tmp/go-runtime
curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
export PATH="/tmp/go-runtime/go/bin:$PATH"
export GOPATH="/tmp/go-workspace"
export GOCACHE="/tmp/go-cache"
export GOMODCACHE="/tmp/go-modcache"
export GOPROXY="https://proxy.golang.org,direct"
```

#### Step 10.2.2: Generate and Run Go SDK Script

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "google.golang.org/api/option"
    compute "cloud.google.com/go/compute/apiv1"
    computepb "cloud.google.com/go/compute/apiv1/computepb"
)

func main() {
    ctx := context.Background()
    client, err := compute.NewInstancesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()

    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    zone := os.Getenv("CLOUDSDK_COMPUTE_ZONE")

    req := &computepb.ListInstancesRequest{
        Project: project,
        Zone:    zone,
    }

    resp, err := client.List(ctx, req)
    if err != nil {
        log.Fatalf("Failed to list instances: %v", err)
    }

    for _, instance := range resp.Items {
        fmt.Printf("Instance: %s (status: %s)\n", instance.GetName(), instance.GetStatus())
    }
}
```

Execute:
```bash
cd /tmp/gcp-sdk-workspace
go run ./main.go
```

#### Go SDK Execution Time Estimate

| Step | First Run | Subsequent Runs |
|------|-----------|-----------------|
| Download Go runtime | ~30s | 0s (cached) |
| `go get` dependencies | ~15s | ~3s (cached) |
| `go run` | ~5s | ~3s |
| **Total** | **~50s** | **~6s** |

#### SDK Decision Matrix

| Python 3.8+ | Go | Recommended | Rationale |
|:-----------:|:--:|:-----------:|-----------|
| ✅ | — | **Python SDK** | Zero extra runtime, fastest path |
| ❌ | ✅ | **Go SDK** | Only option if Python unavailable |
| ❌ | ❌ | Docker gcloud | No SDK options → use CLI via Docker |
| ✅ | ✅ | **Python SDK** | Faster cold start, simpler code |

---

## 11. Credential Configuration

### Service Account Key File (Recommended for Agent Execution)

```bash
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### gcloud Auth as Service Account

```bash
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gcloud config set project "$CLOUDSDK_CORE_PROJECT"
```

### User Credentials (Interactive)

```bash
gcloud auth application-default login
```

### Access Token (Short-Lived)

```bash
export CLOUDSDK_AUTH_ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
```

### `.env` File Support

For local development convenience:

```ini
# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
CLOUDSDK_COMPUTE_ZONE=us-central1-f
```

**Safety rules:**
- **NEVER** commit `.env` files or service account key JSON to version control
- **NEVER** write `.env` values into generated skill documents
- Generated skills continue using `{{env.*}}` placeholders
- Shell environment variables **MUST** override `.env` values

---

## 12. Credential Security (Mandatory)

All generated skills MUST enforce these credential security rules across **every** execution path (CLI, Python SDK, Go SDK, verification scripts, debugging output):

| Context | Required Behavior | Example |
|---------|------------------|---------|
| **Console output** (stdout/stderr) | SA key content MUST be replaced with `<masked>` or `***` | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` |
| **Log files** | Same masking rule | `[INFO] SA key path: ***` |
| **Error messages** | Sanitize before display | `Error: Authentication failed (credential omitted)` |
| **Debug/verbose mode** | Warn user | `⚠️ --log-http may expose credential values in output` |
| **JIT SDK scripts** | SDK reads from env vars (safe); struct/config never printed | `client = compute_v1.InstancesClient()` via env |
| **Template generation** | Use `{{env.*}}` placeholders only | `export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"` |
| **Credential verification** | Check existence only; never `cat` the key file | `✅ GOOGLE_APPLICATION_CREDENTIALS is set` |

**Non-compliance consequence:** Any skill that outputs un-masked credential values in console or logs SHALL be treated as a **security incident** and blocked from merge.

---

## 13. Full Idempotent Bootstrap Script

---

## 10. Credential Configuration

### Service Account Key File (Recommended for Agent Execution)

```bash
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### gcloud Auth as Service Account

```bash
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gcloud config set project "$CLOUDSDK_CORE_PROJECT"
```

### User Credentials (Interactive)

```bash
gcloud auth application-default login
```

### Access Token (Short-Lived)

```bash
export CLOUDSDK_AUTH_ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
```

### `.env` File Support

For local development convenience:

```ini
# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
CLOUDSDK_COMPUTE_ZONE=us-central1-f
```

**Safety rules:**
- **NEVER** commit `.env` files or service account key JSON to version control
- **NEVER** write `.env` values into generated skill documents
- Generated skills continue using `{{env.*}}` placeholders
- Shell environment variables **MUST** override `.env` values

---

## 11. Credential Security (Mandatory)

All generated skills MUST enforce these credential security rules across **every** execution path (CLI, JIT Go SDK, verification scripts, debugging output):

| Context | Required Behavior | Example |
|---------|------------------|---------|
| **Console output** (stdout/stderr) | SA key content MUST be replaced with `<masked>` or `***` | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` |
| **Log files** | Same masking rule | `[INFO] SA key path: ***` |
| **Error messages** | Sanitize before display | `Error: Authentication failed (credential omitted)` |
| **Debug/verbose mode** | Warn user | `⚠️ --log-http may expose credential values in output` |
| **JIT Go SDK scripts** | SDK reads from env vars (safe); struct never printed | `option.WithCredentialsFile(os.Getenv(...))` |
| **Template generation** | Use `{{env.*}}` placeholders only | `export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"` |
| **Credential verification** | Check existence only; never `cat` the key file | `✅ GOOGLE_APPLICATION_CREDENTIALS is set` |

**Non-compliance consequence:** Any skill that outputs un-masked credential values in console or logs SHALL be treated as a **security incident** and blocked from merge.

---

## 12. Full Idempotent Bootstrap Script

> A single idempotent script that probes → installs → verifies → configures auth.

```bash
#!/bin/bash
# ── gcloud idempotent bootstrap ──
# Run this anytime. Safe to re-run. No side effects on subsequent runs.
# Usage: source ./bootstrap-gcloud.sh

BOOTSTRAP_LOG="/tmp/gcloud-bootstrap.log"

log() {
    local PHASE="$1" MSG="$2"
    echo "$(date '+%H:%M:%S') [$PHASE] $MSG" | tee -a "$BOOTSTRAP_LOG"
}

# ── Phase 1: Probe ──
log "DIAG" "PHASE=probe"

GCLOUD_PATH=$(command -v gcloud 2>/dev/null || true)
log "DIAG" "gcloud_path=${GCLOUD_PATH:-NOT_FOUND}"

if [ -n "$GCLOUD_PATH" ]; then
    GCLOUD_VER=$(gcloud version --format="json" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Google Cloud SDK','unknown'))" 2>/dev/null || echo "unknown")
    log "DIAG" "gcloud_version=$GCLOUD_VER"
fi

DOCKER_AVAIL=$(command -v docker &>/dev/null && echo YES || echo NO)
log "DIAG" "docker_available=$DOCKER_AVAIL"

PYTHON_OK="NO"
if command -v python3 &>/dev/null; then
    python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null && PYTHON_OK="YES"
fi
log "DIAG" "python3_compatible=$PYTHON_OK"

# ── Phase 2: Install (only if missing) ──
if [ -z "$GCLOUD_PATH" ]; then
    log "INSTALL" "action=install_gcloud"

    if [ "$DOCKER_AVAIL" = "YES" ]; then
        log "INSTALL" "method=docker"
        docker pull google/cloud-sdk:latest --quiet 2>/dev/null
        alias gcloud='docker run --rm -i \
            -v "${GOOGLE_APPLICATION_CREDENTIALS:-/dev/null}:/tmp/sa.json:ro" \
            -e CLOUDSDK_CORE_PROJECT \
            google/cloud-sdk:latest gcloud'
        log "RESULT" "gcloud=via-docker"
    elif command -v apt-get &>/dev/null; then
        log "INSTALL" "method=apt"
        sudo apt-get update -qq && sudo apt-get install -y -qq google-cloud-cli 2>/dev/null || \
        sudo snap install google-cloud-sdk --classic --quiet 2>/dev/null || {
            # Manual SDK download
            OS=$(uname -s | tr '[:upper:]' '[:lower:]')
            ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="x86_64"
            mkdir -p /tmp/gcloud-sdk
            curl -fsSL "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/gcloud-sdk
            /tmp/gcloud-sdk/google-cloud-sdk/install.sh --quiet --usage-reporting false
            export PATH="/tmp/gcloud-sdk/google-cloud-sdk/bin:$PATH"
        }
        log "RESULT" "gcloud=via-package-manager"
    elif command -v brew &>/dev/null; then
        log "INSTALL" "method=brew"
        brew install --quiet google-cloud-sdk 2>/dev/null
        log "RESULT" "gcloud=via-brew"
    else
        log "ERROR" "TYPE=NO_INSTALL_PATH FIX=Use Cloud Shell at https://shell.cloud.google.com"
        return 1
    fi
else
    log "DIAG" "gcloud_already_installed=YES version=$GCLOUD_VER"
fi

# ── Phase 3: Verify ──
log "DIAG" "PHASE=verify"
if command -v gcloud &>/dev/null; then
    log "RESULT" "gcloud=$(gcloud version 2>&1 | head -1)"
else
    log "ERROR" "TYPE=GCLOUD_NOT_IN_PATH FIX=export PATH"
    return 1
fi

# ── Phase 4: Auth (only if not configured) ──
log "DIAG" "PHASE=auth"
if gcloud auth application-default print-access-token --quiet &>/dev/null; then
    log "RESULT" "ADC=ALREADY_CONFIGURED"
else
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" --quiet 2>/dev/null
        log "RESULT" "ADC=CONFIGURED_VIA_SA"
    elif [ -n "$CLOUDSDK_AUTH_ACCESS_TOKEN" ]; then
        log "RESULT" "ADC=CONFIGURED_VIA_TOKEN"
    else
        log "ERROR" "TYPE=AUTH_MISSING FIX=export GOOGLE_APPLICATION_CREDENTIALS"
        return 1
    fi
fi

# ── Phase 5: Project (only if not set) ──
log "DIAG" "PHASE=project"
PROJECT=$(gcloud config get-value core/project 2>/dev/null || echo "")
if [ -z "$PROJECT" ] && [ -n "$CLOUDSDK_CORE_PROJECT" ]; then
    gcloud config set project "$CLOUDSDK_CORE_PROJECT" --quiet 2>/dev/null
    log "RESULT" "project=SET"
elif [ -n "$PROJECT" ]; then
    log "RESULT" "project=$PROJECT"
else
    log "ERROR" "TYPE=PROJECT_MISSING FIX=export CLOUDSDK_CORE_PROJECT or gcloud config set project"
    return 1
fi

log "SUMMARY" "status=READY method=$(command -v gcloud 2>/dev/null | grep -q docker && echo docker || echo native)"
```

---

## 13. Environment Variable Sources

| Priority | Source | Description |
|----------|--------|-------------|
| 1 (highest) | Shell environment | `GOOGLE_APPLICATION_CREDENTIALS`, `CLOUDSDK_CORE_PROJECT` |
| 2 | gcloud config | `~/.config/gcloud/configurations/config_default` |
| 3 | Service account key file | Path set via env var or `gcloud auth` |

### Supported Environment Variables

| Variable | Purpose | Required |
|----------|---------|:--------:|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key JSON | ✅ |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | ✅ |
| `CLOUDSDK_COMPUTE_ZONE` | Default compute zone | Optional |
| `CLOUDSDK_COMPUTE_REGION` | Default compute region | Optional |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Pre-existing access token | Alternative to SA |

---

## Appendix: Install Method Comparison

| Method | Idempotent? | Python Dep? | Size | Speed (first) | Cleanup |
|--------|:-----------:|:-----------:|:----:|:-------------:|:-------:|
| **apt** | ✅ (`install -y`) | ❌ (system Python) | ~200MB | ~60s | `apt-get remove` |
| **snap** | ✅ (`snap install`/`snap refresh`) | ❌ (bundled) | ~280MB | ~45s | `snap remove` |
| **brew** | ✅ (`brew install`) | ❌ (system Python) | ~200MB | ~90s | `brew uninstall` |
| **Manual** | ⚠️ (check dir exists) | ❌ (system Python) | ~200MB | ~120s | `rm -rf` |
| **Docker** | ✅ (`docker pull`) | ✅ (bundled) | ~300MB image | ~30s (pulled) | `docker rmi` |
| **Cloud Shell** | ✅ (zero install) | ✅ (bundled) | 0 | 0s | None |

**Recommendation by context:**

| Context | Recommended Method |
|---------|--------------------|
| Developer laptop | brew (macOS) / apt (Linux) |
| CI/CD (GitHub Actions) | Docker `google/cloud-sdk` or `google-github-actions/setup-gcloud` |
| Agent sandbox | Docker (fastest, cleanest) |
| No Docker + No Python 3.8+ | Cloud Shell |
| JIT fallback | Go SDK (`cloud.google.com/go/...`) |