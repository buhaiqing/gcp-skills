# Private Cloud Composer Environment Setup

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [VPC-Native Configuration](#vpc-native-configuration)
- [Private Service Connect](#private-service-connect)
- [Web Server Ingress Control](#web-server-ingress-control)
- [DMZ Architecture](#dmz-architecture)
- [DNS Configuration](#dns-configuration)
- [Composer Private Setup Commands](#composer-private-setup-commands)
- [Troubleshooting](#troubleshooting)

---

## Overview

Private Cloud Composer environments isolate Airflow web servers and workers from the public internet. This guide covers VPC-native configuration, Private Service Connect, ingress control, and DMZ architecture.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Private Composer Architecture                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                         Google Cloud VPC                          │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │              Private Subnet (10.0.0.0/24)                   │ │ │
│  │  │  ┌─────────────────┐  ┌─────────────────┐                  │ │ │
│  │  │  │ Composer Web    │  │ Composer        │                  │ │ │
│  │  │  │ Server          │  │ Workers         │                  │ │ │
│  │  │  │ (Private IP)    │  │ (Private IP)    │                  │ │ │
│  │  │  └─────────────────┘  └─────────────────┘                  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                            │                                      │ │
│  │                            ▼                                      │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │              Private Services Access                        │ │ │
│  │  │              (Private Google Access)                        │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─────────────┐                                                       │
│  │  Bastion    │  → Private Service Connect → Composer Web UI         │
│  │  Host       │                                                       │
│  └─────────────┘                                                       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Private Service Connect                       │   │
│  │   Composer API → Composer Web UI → Airflow REST API              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Enable required APIs
gcloud services enable composer.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable servicenetworking.googleapis.com
gcloud services enable privateca.googleapis.com

# Required IAM roles
# - roles/composer.admin
# - roles/compute.admin
# - roles/vpcaccess.admin (for serverless VPC access)
```

## VPC-Native Configuration

### Create VPC with Private Google Access

```bash
# Create dedicated VPC for Composer
gcloud compute networks create composer-vpc \
  --subnet-mode=custom

# Create subnet with private Google Access
gcloud compute networks subnets create composer-subnet \
  --network=composer-vpc \
  --region=us-central1 \
  --range=10.0.0.0/24 \
  --enable-private-ip-google-access \
  --secondary-range=composer-workers=10.0.1.0/24
```

### Create VPC Connector for Serverless

```bash
# Create Serverless VPC Access connector
gcloud compute networks vpc-access connectors create composer-connector \
  --network=composer-vpc \
  --region=us-central1 \
  --range=10.0.2.0/28 \
  --min-instances=2 \
  --max-instances=10
```

### Private Environment Creation

```bash
# Create private Composer environment
gcloud composer environments create composer-private \
  --location=us-central1 \
  --network=composer-vpc \
  --subnetwork=composer-subnet \
  --enable-private-environment \
  --web-server-private \
  --web-server-enable-private-google-access \
  --use-labels=env=private
```

---

## Private Service Connect

### Configure Private Service Connect

```bash
# Enable Private Service Connect for Composer API
gcloud compute addresses create composer-psc-ip \
  --global \
  --purpose=PRIVATE_SERVICE_CONNECT \
  --network=composer-vpc \
  --prefix-length=24

# Create PSC endpoint
gcloud compute forwarding-rules create composer-psc-endpoint \
  --global \
  --address=composer-psc-ip \
  --target-google-apis \
  --network=composer-vpc \
  --description="Composer PSC endpoint"
```

### Verify PSC Configuration

```bash
# List PSC endpoints
gcloud compute forwarding-rules list \
  --filter="purpose=PRIVATE_SERVICE_CONNECT"

# Check API connectivity from private network
curl -s -o /dev/null -w "%{http_code}" \
  --connect-to composer-psc-endpoint.internal:443 \
  https://composer.googleapis.com
```

---

## Web Server Ingress Control

### Configure Web Server Ingress

```bash
# Create firewall rule for web server access (from bastion only)
gcloud compute firewall-rules create allow-bastion-to-composer-web \
  --network=composer-vpc \
  --allow=tcp:80,tcp:443,tcp:8080 \
  --source-tags=bastion-host \
  --description="Allow bastion to Composer web server"

# Restrict web server to internal only
gcloud composer environments update composer-private \
  --location=us-central1 \
  --web-server-private
```

### Access Web Server via Bastion

```bash
# SSH to bastion with port forwarding
gcloud compute ssh BASTION_HOST \
  --zone=us-central1-a \
  --ssh-flag="-L" \
  --ssh-flag="8080:localhost:8080"

# Or use IAP tunneling
gcloud compute start-iap-tunnel BASTION_HOST 8080 \
  --zone=us-central1-a \
  --local-host-port=localhost:8080
```

### Ingress Control Options

| Mode | Description | Use Case |
|------|-------------|----------|
| `public` | Web server accessible from internet | Development only |
| `private` | Web server only on private network | Production default |
| `private-with-gcp-managed-components` | Private + managed service access | Restricted environments |

---

## DMZ Architecture

### DMZ Setup for Composer

```
┌─────────────────────────────────────────────────────────────────┐
│                         DMZ Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────────────────────────────┐   │
│  │   Internet  │     │           composer-vpc (main)        │   │
│  └──────┬──────┘     │  ┌────────────────────────────────┐  │   │
│         │            │  │    dmz-subnet (10.0.10.0/28)   │  │   │
│         │            │  │  ┌──────────────────────────┐  │  │   │
│         ▼            │  │  │   Cloud Armor / IAP      │  │  │   │
│  ┌─────────────┐     │  │  │   (Ingress Firewall)     │  │  │   │
│  │ Cloud Armor │     │  │  └──────────────────────────┘  │  │   │
│  │   Policy    │     │  └────────────────────────────────┘  │   │
│  └──────┬──────┘     │                                      │   │
│         │            │  ┌────────────────────────────────┐  │   │
│         │            │  │  composer-subnet (10.0.0.0/24) │  │   │
│         │            │  │  - Web Server (10.0.0.5)       │  │   │
│         │            │  │  - Workers (10.0.0.10-15)      │  │   │
│         │            │  └────────────────────────────────┘  │   │
│         │            └──────────────────────────────────────┘   │
│         │                                                       │
│  ┌──────┴──────┐                                               │
│  │  Global     │                                               │
│  │  External   │                                               │
│  │  Load Balancer│                                              │
│  └─────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Cloud Armor Security Policy

```bash
# Create security policy
gcloud compute security-policies create composer-security-policy \
  --description="Security policy for Composer DMZ"

# Add rule: allow health checks
gcloud compute security-policies rules create 1000 \
  --security-policy=composer-security-policy \
  --description="Allow Google health checks" \
  --src-ip-ranges=130.211.0.0/22,35.191.0.0/16 \
  --action=allow

# Add rule: block all other traffic to web server
gcloud compute security-policies rules create 2000 \
  --security-policy=composer-security-policy \
  --description="Block non-bastion traffic" \
  --src-ip-ranges=* \
  --action=deny-404

# Attach to backend service (if using global load balancer)
gcloud compute backend-services update composer-web-backend \
  --security-policy=composer-security-policy \
  --global
```

### Bastion Host Setup

```bash
# Create bastion host
gcloud compute instances create composer-bastion \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --network=composer-vpc \
  --subnet=dmz-subnet \
  --no-address \
  --tags=bastion-host

# Create firewall rule to allow IAP access
gcloud compute firewall-rules create allow-iap-to-bastion \
  --network=composer-vpc \
  --allow=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --description="Allow IAP SSH access to bastion"
```

---

## DNS Configuration

### Cloud DNS Setup for Private Environment

```bash
# Create private DNS zone
gcloud dns managed-zones create composer-private-zone \
  --dns-name="composer.internal." \
  --description="Private DNS for Composer environment" \
  --visibility=private

# Add A record for web server
gcloud dns record-sets transaction start --zone=composer-private-zone

gcloud dns record-sets transaction add 10.0.0.5 \
  --name="airflow.composer.internal." \
  --ttl=300 \
  --type=A \
  --zone=composer-private-zone

gcloud dns record-sets transaction add 10.0.0.5 \
  --name="composer.composer.internal." \
  --ttl=300 \
  --type=A \
  --zone=composer-private-zone

gcloud dns record-sets transaction execute --zone=composer-private-zone
```

### DNS Forwarding

```bash
# Create DNS policy for conditional forwarding to Google APIs
gcloud dns policies create composer-dns-policy \
  --network=composer-vpc \
  --description="DNS policy for Composer private environment" \
  --enable-private-zoning

# Alternative: Use Cloud DNS for on-premises forwarding
gcloud dns managed-zones create composer-onprem-forwarder \
  --dns-name="composer.company.internal." \
  --visibility=private

# Add forwarding rules
gcloud dns policies update composer-dns-policy \
  --network=composer-vpc \
  --forwarding-targets=10.0.0.1
```

### Verify DNS Resolution

```bash
# From bastion or VM in VPC
nslookup airflow.composer.internal

# Test internal resolution
gcloud compute ssh composer-bastion --zone=us-central1-a -- \
  nslookup composer.us-central1.internal
```

---

## Composer Private Setup Commands

### Full Private Environment Creation

```bash
# Step 1: Create VPC
gcloud compute networks create composer-vpc --subnet-mode=custom

# Step 2: Create subnet with private Google Access
gcloud compute networks subnets create composer-subnet \
  --network=composer-vpc \
  --region=us-central1 \
  --range=10.0.0.0/24 \
  --enable-private-ip-google-access

# Step 3: Create VPC connector
gcloud compute networks vpc-access connectors create composer-connector \
  --network=composer-vpc \
  --region=us-central1 \
  --range=10.0.2.0/28

# Step 4: Create private Composer environment
gcloud composer environments create composer-private \
  --location=us-central1 \
  --network=composer-vpc \
  --subnetwork=composer-subnet \
  --enable-private-environment \
  --web-server-private \
  --web-server-enable-private-google-access

# Step 5: Verify environment
gcloud composer environments describe composer-private \
  --location=us-central1 \
  --format="value(config.privateEnvironmentConfig.webServerPrivateIp)"
```

### Update Existing Environment to Private

```bash
# Cannot convert public to private environment
# Must create new environment and migrate DAGs

# For environment upgrades with private config
gcloud composer environments update composer-private \
  --location=us-central1 \
  --network=composer-vpc \
  --subnetwork=composer-subnet \
  --enable-private-environment
```

### Verify Private Configuration

```bash
# Check private environment config
gcloud composer environments describe composer-environment \
  --location=us-central1 \
  --format=json | jq '.config.privateEnvironmentConfig'

# List environments with private status
gcloud composer environments list \
  --locations=us-central1 \
  --format="table(name,config.privateEnvironmentConfig)"

# Verify web server is not publicly accessible
gcloud composer environments describe composer-environment \
  --location=us-central1 \
  --format="value(config.webServerNetwork)"
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Cannot reach web server | Private endpoint not configured | Verify `--enable-private-environment` |
| DAGs not syncing | VPC connector missing | Create serverless VPC connector |
| Cannot access Google APIs | Private Google Access disabled | Enable on subnet |
| DNS resolution fails | Cloud DNS not configured | Set up private DNS zone |
| Workers cannot start | Firewall rules block Google APIs | Allow egress to Google APIs |

### Verification Commands

```bash
# Check Composer environment details
gcloud composer environments describe ENVIRONMENT_NAME \
  --location=REGION

# Verify private environment config
gcloud composer environments describe ENVIRONMENT_NAME \
  --location=REGION \
  --format="json" | jq '.config.privateEnvironmentConfig'

# Test connectivity from worker
gcloud composer environments run ENVIRONMENT_NAME \
  --location=REGION \
  --no-user-output-enabled \
  -- bash -c "curl -s -o /dev/null -w '%{http_code}' https://www.googleapis.com/composer/v1/projects"

# Check web server logs
gcloud composer environments logs ENVIRONMENT_NAME \
  --location=REGION \
  --吸 --limit=100
```

### Access Private Web Server

```bash
# Method 1: IAP tunneling (recommended)
gcloud compute start-iap-tunnel INSTANCE_NAME 8080 \
  --zone=ZONE \
  --local-host-port=localhost:8080

# Method 2: SSH port forwarding via bastion
gcloud compute ssh BASTION_HOST --zone=ZONE -- -L 8080:localhost:8080

# Method 3: Use Cloud Shell with IAP
gcloud cloud-shell ssh --authorize-session
gcloud cloud-shell ssh --tunnel-through-iap -- -L 8080:localhost:8080 BASTION_HOST
```

---

## See Also

- [Cloud Composer Private Environments](https://cloud.google.com/composer/docs/concepts/private-environments)
- [Private Service Connect](https://cloud.google.com/vpc/docs/private-service-connect)
- [Serverless VPC Access](https://cloud.google.com/vpc/docs/serverless-vpc-access)
- [Cloud DNS Private Zones](https://cloud.google.com/dns/docs/private-zones)
