# Docker gcloud (Zero-Install Fallback)

> **When to use**: Target machine has Docker but no `gcloud` CLI. Provides isolated, version-pinned `gcloud` without host installation.

---

## Why Docker gcloud?

| Advantage | Detail |
|-----------|--------|
| **Zero-install** | No host SDK needed — Docker image bundles everything |
| **Version-pinned** | `gcr.io/google.com/cloudsdktool/google-cloud-cli:CHANNEL` — stable, beta, latest |
| **Isolated** | Credentials mounted via volume — no host config pollution |
| **CI-friendly** | Ephemeral containers — ideal for GitHub Actions, Cloud Build |

---

## Docker Wrapper Script

Save as `gcloud-docker.sh` (idempotent, self-healing):

```bash
#!/usr/bin/env bash
# gcloud-docker.sh — run gcloud inside Docker (zero-install fallback)
set -euo pipefail

GCLOUD_IMAGE="gcr.io/google.com/cloudsdktool/google-cloud-cli:stable"
LOCAL_PROJECT="${CLOUDSDK_CORE_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo)}"
LOCAL_CREDS="${GOOGLE_APPLICATION_CREDENTIALS:-}"

die() { echo "[ERROR] $*" >&2; exit 1; }

# ── Pre-flight ──────────────────────────────────────────────────────────────────
[ -z "${LOCAL_PROJECT}" ] && die "CLOUDSDK_CORE_PROJECT not set"
[ -z "${LOCAL_CREDS}" ] && die "GOOGLE_APPLICATION_CREDENTIALS not set"
command -v docker &>/dev/null || die "Docker not found (install: https://docs.docker.com/get-docker/)"

# ── Mount credential ───────────────────────────────────────────────────────────
CREDS_MOUNT=""
if [ -f "${LOCAL_CREDS}" ]; then
  CREDS_MOUNT="-v ${LOCAL_CREDS}:/tmp/keys/sa.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/sa.json"
fi

# ── Run ─────────────────────────────────────────────────────────────────────────
echo "[EXEC] docker run --rm ${GCLOUD_IMAGE} gcloud $*"
docker run --rm \
  -v "${HOME}/.config/gcloud:/root/.config/gcloud:cached" \
  ${CREDS_MOUNT} \
  -e CLOUDSDK_CORE_PROJECT="${LOCAL_PROJECT}" \
  "${GCLOUD_IMAGE}" \
  gcloud "$@"
```

**Usage** (replace `gcloud` with `./gcloud-docker.sh`):

```bash
./gcloud-docker.sh compute instances list --project=my-project
./gcloud-docker.sh auth login  # interactive — mounts ~/.config/gcloud
```

---

## Docker gcloud Alias (Idempotent Setup)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Fallback: use Docker gcloud if local gcloud missing
alias gcloud-docker='docker run --rm -v ${HOME}/.config/gcloud:/root/.config/gcloud -v ${GOOGLE_APPLICATION_CREDENTIALS:-/dev/null}:/tmp/keys/sa.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/sa.json -e CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT:-} gcr.io/google.com/cloudsdktool/google-cloud-cli:stable gcloud'

# Verify
gcloud-docker compute instances list --project="${CLOUDSDK_CORE_PROJECT:-}"
```

---

## Credential Mount Options

| Scenario | Mount Command |
|-----------|----------------|
| **Service account JSON** | `-v ${GOOGLE_APPLICATION_CREDENTIALS}:/tmp/keys/sa.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/sa.json` |
| **Application default** | `-v ${HOME}/.config/gcloud:/root/.config/gcloud:cached` |
| **Both** | Mount both volumes (ADCs take precedence) |

---

## Troubleshooting

| Error | Fix |
|--------|-----|
| `docker: command not found` | Install Docker — [docs](https://docs.docker.com/get-docker/) |
| `permission denied` | Add user to `docker` group — `sudo usermod -aG docker ${USER}` |
| `quota exceeded` | Increase Docker disk limit — `Preferences → Resources → Disk` |
| ` credential file not found` | Check `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON key |

---

## When NOT to Use Docker gcloud

- **Production VMs** — install `gcloud` SDK directly (performance)
- **Windows without WSL2** — Docker Desktop volume mount quirks
- **Behind strict firewall** — Docker Hub pull may be blocked (use proxy)

> **Fallback**: Use `gcloud` binary directly — [Phase 2: Install](#4-phase-2-install--idempotent-multi-path-install)
