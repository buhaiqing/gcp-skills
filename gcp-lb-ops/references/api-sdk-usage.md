# API & SDK — Cloud Load Balancing

## REST API

- **Discovery doc**: `https://compute.googleapis.com/$discovery/rest?version=v1`
- **Base URL**: `https://compute.googleapis.com/compute/v1/`
- **API reference**: [Compute Engine REST API: Forwarding Rules](https://cloud.google.com/compute/docs/reference/rest/v1/forwardingRules)

## Operations Map

| Goal | REST Method & Path | Go SDK Method |
|------|-------------------|---------------|
| List forwarding rules (global) | `GET /projects/{project}/global/forwardingRules` | `ForwardingRulesClient.List()` |
| Create forwarding rule (global) | `POST /projects/{project}/global/forwardingRules` | `ForwardingRulesClient.Insert()` |
| Describe forwarding rule (global) | `GET /projects/{project}/global/forwardingRules/{resource}` | `ForwardingRulesClient.Get()` |
| Delete forwarding rule (global) | `DELETE /projects/{project}/global/forwardingRules/{resource}` | `ForwardingRulesClient.Delete()` |
| List forwarding rules (regional) | `GET /projects/{project}/regions/{region}/forwardingRules` | `ForwardingRulesClient.List()` |
| Create backend service (global) | `POST /projects/{project}/global/backendServices` | `BackendServicesClient.Insert()` |
| Add backend to service | `PATCH /projects/{project}/global/backendServices/{resource}` | `BackendServicesClient.Patch()` |
| Describe backend service | `GET /projects/{project}/global/backendServices/{resource}` | `BackendServicesClient.Get()` |
| Create URL map | `POST /projects/{project}/global/urlMaps` | `UrlMapsClient.Insert()` |
| Update URL map | `PATCH /projects/{project}/global/urlMaps/{resource}` | `UrlMapsClient.Patch()` |
| Create health check | `POST /projects/{project}/global/healthChecks` | `HealthChecksClient.Insert()` |
| List NEGs | `GET /projects/{project}/zones/{zone}/networkEndpointGroups` | `NetworkEndpointGroupsClient.List()` |
| Create NEG | `POST /projects/{project}/zones/{zone}/networkEndpointGroups` | `NetworkEndpointGroupsClient.Insert()` |

## Request / Response Notes

### Forwarding Rule (Create)

**Required fields:**
- `name`: string
- `IPAddress` (optional — auto-allocated if omitted)
- `IPProtocol`: `TCP` / `UDP` / `L3_DEFAULT`
- `loadBalancingScheme`: `EXTERNAL` / `EXTERNAL_MANAGED` / `INTERNAL` / `INTERNAL_MANAGED` / `INTERNAL_SELF_MANAGED`
- `target` (or `backendService`): resource link to target proxy or backend service
- `portRange` (or `ports[]`): port specification

**Response key paths:**
- `$.name`: operation name for polling
- `$.targetLink`: self-link of the forwarding rule
- `$.IPAddress`: assigned IP address

### Backend Service (Create)

**Required fields:**
- `name`: string
- `healthChecks[]`: health check self-links
- `loadBalancingScheme`: matching the forwarding rule scheme
- `protocol`: depends on LB type
- `backends[]` (can be added after creation)

**Response key paths:**
- `$.name`: operation name
- `$.selfLink`: resource self-link

### URL Map (Create)

**Required fields:**
- `name`: string
- `defaultService`: default backend service self-link
- `hostRules[]` (optional): host-based routing
- `pathMatchers[]` (optional): path-based routing

### Health Check (Create)

**Type-specific fields:**
- `httpHealthCheck` / `httpsHealthCheck` / `tcpHealthCheck` / `sslHealthCheck` / `grpcHealthCheck`
- `checkIntervalSec`: default 10
- `timeoutSec`: default 5
- `healthyThreshold`: default 2
- `unhealthyThreshold`: default 3

## Pagination

Forwarding rules, backend services, URL maps, and health checks support pagination via `pageToken` / `maxResults`:
```bash
gcloud compute forwarding-rules list --page-size=100 --format="json"
```

## Async Behavior

Most LB resources (forwarding rules, backend services, URL maps, health checks) are **synchronous** — `gcloud` returns when operation is `DONE`. SSL certificate provisioning is async (5-10 min for managed certificates).