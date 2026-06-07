# API & SDK — Cloud DNS

## REST API

- **Discovery doc**: `https://dns.googleapis.com/$discovery/rest?version=v1`
- **Base URL**: `https://dns.googleapis.com/dns/v1/`
- **Auth**: OAuth 2.0 Bearer token (via `gcloud auth print-access-token`)

## SDK Operations Map

| Goal | REST Method & Path | Python SDK | Go SDK |
|------|-------------------|------------|--------|
| Create zone | `POST /v1/projects/{project}/managedZones` | `ManagedZonesClient.create_managed_zone()` | `ManagedZonesService.Create()` |
| Get zone | `GET /v1/projects/{project}/managedZones/{zone}` | `ManagedZonesClient.get_managed_zone()` | `ManagedZonesService.Get()` |
| List zones | `GET /v1/projects/{project}/managedZones` | `ManagedZonesClient.list_managed_zones()` | `ManagedZonesService.List()` |
| Update zone | `PATCH /v1/projects/{project}/managedZones/{zone}` | `ManagedZonesClient.update_managed_zone()` | `ManagedZonesService.Patch()` |
| Delete zone | `DELETE /v1/projects/{project}/managedZones/{zone}` | `ManagedZonesClient.delete_managed_zone()` | `ManagedZonesService.Delete()` |
| Create change | `POST /v1/projects/{project}/managedZones/{zone}/changes` | `ChangesClient.create_change()` | `ChangesService.Create()` |
| Get change | `GET /v1/projects/{project}/managedZones/{zone}/changes/{change}` | `ChangesClient.get_change()` | `ChangesService.Get()` |
| List changes | `GET /v1/projects/{project}/managedZones/{zone}/changes` | `ChangesClient.list_changes()` | `ChangesService.List()` |
| List records | `GET /v1/projects/{project}/managedZones/{zone}/rrsets` | `ResourceRecordSetsClient.list_resource_record_sets()` | `ResourceRecordSetsService.List()` |
| List zone ops | `GET /v1/projects/{project}/managedZones/{zone}/operations` | `ManagedZoneOperationsClient.list_managed_zone_operations()` | `ManagedZoneOperationsService.List()` |
| List policies | `GET /v1/projects/{project}/policies` | `PoliciesClient.list_policies()` | `PoliciesService.List()` |

## Request / Response Notes

### Managed Zone

```json
// Create zone request body
{
  "name": "my-zone",
  "dnsName": "example.com.",
  "description": "Example zone",
  "visibility": "public",
  "dnssecConfig": {
    "state": "off",
    "kind": "dns#managedZoneDnsSecConfig"
  }
}

// Private zone request body
{
  "name": "private-zone",
  "dnsName": "internal.example.com.",
  "description": "Private zone",
  "visibility": "private",
  "privateVisibilityConfig": {
    "kind": "dns#managedZonePrivateVisibilityConfig",
    "networks": [
      {
        "kind": "dns#managedZonePrivateVisibilityConfigNetwork",
        "networkUrl": "https://www.googleapis.com/compute/v1/projects/PROJECT_ID/global/networks/NETWORK_NAME"
      }
    ]
  }
}
```

### Change (Record-Set Transaction)

```json
// Create change request body
{
  "additions": [
    {
      "name": "www.example.com.",
      "type": "A",
      "ttl": 300,
      "rrdatas": ["192.0.2.1"]
    }
  ],
  "deletions": []
}
```

### Pagination

- **Request**: `maxResults` (int), `pageToken` (string)
- **Response**: `nextPageToken` in response when more results available

```python
# Python pagination
for zone in client.list_managed_zones(parent=parent, max_results=100):
    process(zone)
```

## Error Response Format

```json
{
  "error": {
    "code": 400,
    "message": "Invalid DNS name",
    "errors": [
      {
        "domain": "global",
        "reason": "invalid",
        "message": "Invalid DNS name format"
      }
    ]
  }
}
```

## Rate Limiting

- DNS API uses token bucket rate limiting
- Exponential backoff recommended for retries
- `Retry-After` header present on 429 responses

## Authentication via REST

```bash
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://dns.googleapis.com/dns/v1/projects/{{env.CLOUDSDK_CORE_PROJECT}}/managedZones?alt=json"
```
