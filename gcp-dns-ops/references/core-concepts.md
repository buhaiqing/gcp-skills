# Core Concepts — Cloud DNS

## Architecture

Google Cloud DNS is a scalable, reliable, and managed DNS service running on Google's global infrastructure. It provides authoritative DNS resolution for domains hosted on Google Cloud.

### Key Components

| Component | Description |
|-----------|-------------|
| **Managed Zone** | A container for DNS records for a specific domain (e.g., example.com) |
| **Record-Set** | A collection of DNS records sharing the same name and type (e.g., A records for www.example.com) |
| **Name Servers** | Four Google-assigned name servers for public zones (delegated at registrar) |
| **DNS Policy** | Rules for DNS forwarding, logging, and response handling |
| **DNSSEC** | Domain Name System Security Extensions for cryptographic validation |

### Zone Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Public Zone** | Visible on the public internet | External-facing domains, websites, APIs |
| **Private Zone** | Visible only within specified VPC networks | Internal service discovery, private APIs |
| **Peering Zone** | Forwards DNS queries to another VPC's private zone | Cross-VPC DNS resolution |
| **Forwarding Zone** | Forwards queries to external name servers | Hybrid cloud DNS, on-prem resolution |

### Record Types

Cloud DNS supports all standard DNS record types:

| Type | Description | Example Data |
|------|-------------|--------------|
| **A** | IPv4 address | `192.0.2.1` |
| **AAAA** | IPv6 address | `2001:db8::1` |
| **CNAME** | Canonical name (alias) | `lb.example.com.` |
| **MX** | Mail exchange | `10 mail.example.com.` |
| **TXT** | Text data (SPF, DKIM, verification) | `"v=spf1 include:_spf.google.com ~all"` |
| **NS** | Name server delegation | `ns-cloud-a1.googledomains.com.` |
| **SOA** | Start of authority (auto-managed) | Managed by Cloud DNS |
| **SRV** | Service location | `10 60 5060 sipserver.example.com.` |
| **PTR** | Reverse DNS | `host.example.com.` |
| **NAPTR** | Naming authority pointer | DNS-based service discovery |
| **SPF** | Sender Policy Framework (legacy, use TXT) | `"v=spf1 -all"` |

### Resource Limits and Quotas

Use `gcloud` to query current quotas (TE-1):

```bash
# List DNS service quotas
gcloud services quotas list --service=dns.googleapis.com --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Count current zones
gcloud dns managed-zones list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq 'length'
```

Default quotas (verify via API, do not hardcode):
- Managed zones per project: ~1,000
- Record-sets per zone: ~10,000
- DNS queries: Unlimited (pay per query)

### Dependencies

| Dependency | Description | Verification |
|------------|-------------|--------------|
| **VPC Network** | Required for private zone binding | `gcloud compute networks list` |
| **Domain Registrar** | Required for public zone (NS delegation) | External to GCP |
| **IAM Permissions** | roles/dns.admin or roles/dns.reader | `gcloud projects get-iam-policy` |

## DNS Propagation

| Aspect | Detail |
|--------|--------|
| **Internal propagation** | Changes appear on Cloud DNS name servers within ~60s |
| **External propagation** | Depends on TTL and downstream resolver caching |
| **TTL strategy** | Lower TTL before migrations, raise after stability confirmed |
| **SOA minimum TTL** | Default negative cache TTL for the zone |

## DNSSEC

| State | Description |
|-------|-------------|
| **off** | DNSSEC disabled (default) |
| **on** | DNSSEC enabled, keys generated and active |
| **transfer** | Zone is being transferred between DNSSEC states |

Enable DNSSEC:
```bash
gcloud dns managed-zones update "{{user.zone_name}}" \
  --dnssec-state="on" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Private Zone Architecture

Private zones resolve DNS queries only from VMs in bound VPC networks:

```
VPC Network A ─┐
               ├── Private Zone (internal.example.com)
VPC Network B ─┘
```

- Queries from unbound VPCs receive NXDOMAIN
- Private zones do not publish to public name servers
- Split-horizon DNS: same domain name can exist in both public and private zones
