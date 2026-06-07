# Troubleshooting — Cloud Load Balancing

## Common API Error Codes

| gRPC Code / HTTP | Meaning | Agent Action |
|-------------|---------|--------------|
| INVALID_ARGUMENT / 400 | Request failed validation | Align body with REST API; check required fields |
| PERMISSION_DENIED / 403 | Insufficient IAM permissions | Grant roles/compute.loadBalancerAdmin |
| NOT_FOUND / 404 | Resource does not exist | Verify resource name, region, or global flag |
| ALREADY_EXISTS / 409 | Duplicate resource | Use unique name for each resource |
| QUOTA_EXCEEDED / 429 | Quota limit reached | Request increase via Cloud Console |
| INTERNAL / 500 | Server-side error | Retry with backoff; then HALT |
| UNAVAILABLE / 503 | Service temporarily unavailable | Retry with exponential backoff |
| `RESOURCE_NOT_READY` | Backend resource in transition | Retry after 15s |
| `INVALID_FORWARDING_RULE_TARGET` | Target proxy / backend mismatch | Verify target proxy name and scope |
| `CERTIFICATE_PREPARATION` | SSL cert not yet provisioned | Wait 5-10 min; poll status |
| `BACKEND_SERVICE_UNHEALTHY` | All backends unhealthy | Check health check config and backend state |

## Diagnostic Order

1. **Check forwarding rule exists and is correctly targeted:**
   ```bash
   gcloud compute forwarding-rules describe "{{user.forwarding_rule_name}}" \
     --global --format="json" | jq '{name, IPAddress, IPProtocol, portRange, target, loadBalancingScheme}'
   ```

2. **Check backend service configuration:**
   ```bash
   gcloud compute backend-services describe "{{user.backend_service_name}}" \
     --global --format="json" | jq '{name, backends: [.backends[] | {group: (.group|split("/")[-1]), balancingMode, capacityScaler}], healthChecks, sessionAffinity}'
   ```

3. **Check backend health:**
   ```bash
   gcloud compute backend-services get-health "{{user.backend_service_name}}" \
     --global --format="json"
   ```

4. **Check URL map routing (if HTTP LB):**
   ```bash
   gcloud compute url-maps describe "{{user.url_map_name}}" \
     --global --format="json" | jq '{name, defaultService: (.defaultService|split("/")[-1]), hostRules, pathMatchers: [.pathMatchers[] | {name, defaultService: (.defaultService|split("/")[-1])}]}'
   ```

5. **Check SSL certificate status (HTTPS LB):**
   ```bash
   gcloud compute ssl-certificates describe "{{user.certificate_name}}" \
     --global --format="json" | jq '.managed.status'
   ```

6. **Verify target proxy links correctly:**
   ```bash
   gcloud compute target-https-proxies list --global --format="json" | jq '.[] | {name, urlMap: (.urlMap|split("/")[-1]), sslCertificates: [.sslCertificates[] | split("/")[-1]]}'
   ```

7. **Check VPC firewall rules allow health check probes:**
   Health check probes come from `130.211.0.0/22` and `35.191.0.0/16`. Ensure firewalls allow ingress from these ranges to LB backend ports.

## Product-Specific Issues

### "502 Bad Gateway" from LB

| Possible Cause | Check | Resolution |
|---------------|-------|------------|
| All backends unhealthy | `get-health` on backend service | Fix backend instances or health check |
| Backend timeout exceeded | Backend processing > timeoutSec | Increase timeout or optimize backend |
| Health check target not responding | curl to backend health endpoint | Fix health check path/port |
| Backend VM stopped/crashed | gcloud compute instances describe | Start or recreate instance |

### "404 Not Found" from Global HTTPS LB

| Possible Cause | Check | Resolution |
|---------------|-------|------------|
| URL map default service not configured | Describe URL map | Ensure defaultService is set and correct |
| Path matcher has no matching rule | Check path matchers | Add path rule or fallback to default service |
| Host header doesn't match any host rule | Check hostRules | Add host rule or use wildcard |

### SSL Certificate Issues

| Issue | Status Value | Resolution |
|-------|-------------|------------|
| Certificate provisioning | `PROVISIONING` | Wait 5-10 minutes |
| Domain validation failed | `FAILED` + domainStatuses | Check DNS setup (CAA record, A record) |
| Certificate expired | `EXPIRED` | Delete and recreate managed cert |
| Self-managed cert expired | N/A | Upload new cert + key before expiry |

### Health Check Always Unhealthy

1. Verify health check path/port matches backend service application
2. Verify firewall rules allow `130.211.0.0/22` and `35.191.0.0/16` ingress
3. Verify backend instances are running and application is listening on the port
4. Check health check timeout < check interval (timeout must be < interval)
5. Test health endpoint locally on the backend:
   ```bash
   curl -v http://localhost:{{user.port}}/{{user.health_check_path}}
   ```

### Traffic Not Reaching Backend

1. Verify forwarding rule `IPAddress` and `portRange` match expected
2. Verify target proxy -> URL map -> backend service chain connectivity
3. Check if Cloud Armor / security policy is blocking requests
4. Verify session affinity setting (CLIENT_IP may cause uneven distribution)
5. Check if backend capacity is sufficient (maxUtilization reached) → scale out