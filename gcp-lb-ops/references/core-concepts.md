# Core Concepts — Cloud Load Balancing

## Architecture

Google Cloud Load Balancing is a fully distributed, software-defined load balancing service. Unlike hardware-based LB solutions, GCP LB is not a device you provision — it's a set of configurable forwarding and routing resources that operate at Google's edge PoPs or within your VPC.

### Six Load Balancer Types

| Type | Scheme | Traffic | Scope | Use Case |
|------|--------|---------|-------|----------|
| External Application LB | EXTERNAL_MANAGED | HTTP(S) | Global (anycast IP) | Public web apps, APIs |
| External Proxy Network LB | EXTERNAL_MANAGED | TCP/SSL | Regional | Non-HTTP TCP/SSL, IoT |
| External Passthrough Network LB | EXTERNAL | TCP/UDP | Regional | Legacy TCP/UDP apps |
| Internal Application LB | INTERNAL_MANAGED | HTTP(S) | Regional | Internal microservices (HTTP) |
| Internal Proxy Network LB | INTERNAL_MANAGED | TCP/SSL | Regional | Internal microservices (TCP) |
| Internal Passthrough Network LB | INTERNAL | TCP/UDP | Regional | Internal VPC apps |

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Forwarding Rule** | Entry point: IP + port → target | Global or Regional |
| **Target Proxy** | Terminates traffic and references URL map / SSL cert | Global or Regional |
| **URL Map** | Host and path routing rules (HTTP LB only) | Global or Regional |
| **Backend Service** | Traffic distribution policy, health checks, backends | Global or Regional |
| **Backend Bucket** | Like Backend Service but for Cloud Storage bucket backends | Global |
| **Health Check** | Probes backend health (HTTP/HTTPS/TCP/SSL/gRPC) | Global or Regional |
| **NEG** | Network Endpoint Group: granular endpoint collection | Zonal, Regional, Global |
| **SSL Certificate** | TLS termination (managed or self-managed) | Global or Regional |
| **SSL Policy** | TLS version and cipher constraints | Global |

### Traffic Flow (External HTTPS LB Example)

```
Client → Google Edge PoP → Forwarding Rule (IP:443)
                                       ↓
                           Target HTTPS Proxy (SSL termination)
                                       ↓
                                  URL Map (host/path routing)
                                       ↓
                               Backend Service (health, scaling)
                                       ↓
                            MIG / NEG / Serverless backend
```

## Quotas and Limits

| Resource | Default Quota (per project) | Can Increase? |
|----------|---------------------------|---------------|
| Forwarding rules (global) | 5 | Yes |
| Forwarding rules (regional, EXTERNAL) | 15 | Yes |
| Forwarding rules (regional, INTERNAL) | 25 | Yes |
| Backend services (global) | 10 | Yes |
| Backend services (regional) | 50 | Yes |
| URL maps | 10 | Yes |
| Target proxies (each type) | 10 | Yes |
| Health checks | 50 | Yes |
| SSL certificates | 20 | Yes |
| NEGs (per zone) | 100 | Yes |
| Backends per backend service | 50 | Yes |

Check current quotas:
```bash
gcloud compute regions describe "{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.quotas[] | select(.metric | test("forwarding|backend|target")) | {metric, limit, usage}'
```

## Regions and Zones

- **Global LB (External Application/Proxy)**: Single anycast IP (`0.0.0.0`); backends can be in any region
- **Regional LB**: Resource tied to one region; backends must be in same region
- **Internal LB**: Regional, accessible only within the same VPC network
- **Cross-region**: Global LB supports multi-region backend services for failover

## Dependencies

| Depend On | Reason |
|-----------|--------|
| VPC / Subnet | Internal LB requires a subnet with purpose `INTERNAL_LOAD_BALANCING` or `PRIVATE_SERVICE_CONNECT` |
| GCE Instance Groups / NEGs | Backends must exist before adding to backend service |
| SSL Certificate (HTTPS LB) | Required before creating target HTTPS proxy |
| Static IP address | Optional but recommended for production; prevents IP changes on recreate |
| Cloud DNS | A/AAAA record pointing domain to LB IP address |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Single backend fails | Traffic fails over to healthy backends | Multiple backends + auto-healing |
| All backends unhealthy | 502 Bad Gateway from LB | Alarm on zero healthy backends; redundant backend pools |
| Region goes down (regional LB) | Service unavailable until redeploy | Use global LB for multi-region coverage |
| SSL certificate expires | HTTPS LB returns certificate error | Managed certificates auto-renew; set alert on expiration |
| Quota exhausted | Cannot create new forwarding rules | Monitor usage; set budget alerts |