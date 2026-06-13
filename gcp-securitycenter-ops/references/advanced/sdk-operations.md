# SCC SDK-Only Operations

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Custom Modules](#custom-modules)
- [Effective Modules](#effective-modules)
- [Resource Value Configs](#resource-value-configs)
- [Code Snippets](#code-snippets)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

SCC has operations only available via the SDK/REST API, not exposed through `gcloud`. This guide covers custom modules, effective modules, and resource value configs with Python SDK examples.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              SCC SDK-Only Operations Architecture               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Python     │    │  SCC API    │    │  SCC        │        │
│  │  SDK        │───►│  REST       │───►│  Backend    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Custom     │    │  Effective  │    │  Resource   │        │
│  │  Modules    │    │  Modules    │    │  Values     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Install Python SDK
pip install google-cloud-securitycenter

# Enable required APIs
gcloud services enable securitycenter.googleapis.com

# Required IAM roles
# - roles/securitycenter.admin (manage custom modules)
# - roles/securitycenter.findingsEditor (manage findings)
```

## Custom Modules

### Create Custom Module

```python
# Python SDK for custom modules
from google.cloud import securitycenter_v1

def create_custom_module(org_id, module_config):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    custom_module = securitycenter_v1.SecurityCenterModule(
        display_name=module_config["display_name"],
        description=module_config["description"],
        enablement_state="ENABLED",
        module_config=module_config["config"]
    )
    
    response = client.create_security_health_analytics_custom_module(
        request={
            "parent": parent,
            "security_health_analytics_custom_module": custom_module
        }
    )
    
    return response
```

### List Custom Modules

```python
# List all custom modules
def list_custom_modules(org_id):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    modules = client.list_security_health_analytics_custom_modules(
        request={"parent": parent}
    )
    
    return [{"name": m.name, "display_name": m.display_name, "state": m.enablement_state} for m in modules]
```

### Update Custom Module

```python
# Update custom module
def update_custom_module(org_id, module_id, updates):
    client = securitycenter_v1.SecurityCenterClient()
    name = f"organizations/{org_id}/securityHealthAnalyticsCustomModules/{module_id}"
    
    module = securitycenter_v1.SecurityCenterModule(
        name=name,
        **updates
    )
    
    response = client.update_security_health_analytics_custom_module(
        request={
            "security_health_analytics_custom_module": module,
            "update_mask": {"paths": list(updates.keys())}
        }
    )
    
    return response
```

### Delete Custom Module

```python
# Delete custom module
def delete_custom_module(org_id, module_id):
    client = securitycenter_v1.SecurityCenterClient()
    name = f"organizations/{org_id}/securityHealthAnalyticsCustomModules/{module_id}"
    
    client.delete_security_health_analytics_custom_module(
        request={"name": name}
    )
    
    return True
```

## Effective Modules

### List Effective Modules

```python
# List effective modules (custom + built-in)
def list_effective_modules(org_id):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    modules = client.list_effective_security_health_analytics_custom_modules(
        request={"parent": parent}
    )
    
    return [{"name": m.name, "display_name": m.display_name, "state": m.enablement_state} for m in modules]
```

### Describe Effective Module

```python
# Get details of an effective module
def describe_effective_module(org_id, module_id):
    client = securitycenter_v1.SecurityCenterClient()
    name = f"organizations/{org_id}/effectiveSecurityHealthAnalyticsCustomModules/{module_id}"
    
    module = client.get_effective_security_health_analytics_custom_module(
        request={"name": name}
    )
    
    return module
```

## Resource Value Configs

### Create Resource Value Config

```python
# Create resource value configuration
def create_resource_value_config(org_id, config):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    resource_value_config = securitycenter_v1.ResourceValueConfig(
        name=config.get("name"),
        resource_value=config["resource_value"],
        resource_type=config["resource_type"],
        resource_locations=config["resource_locations"],
        pattern=config.get("pattern")
    )
    
    response = client.create_resource_value_config(
        request={
            "parent": parent,
            "resource_value_config": resource_value_config
        }
    )
    
    return response
```

### List Resource Value Configs

```python
# List resource value configurations
def list_resource_value_configs(org_id):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    configs = client.list_resource_value_configs(
        request={"parent": parent}
    )
    
    return [{"name": c.name, "resource_value": c.resource_value, "resource_type": c.resource_type} for c in configs]
```

### Delete Resource Value Config

```python
# Delete resource value configuration
def delete_resource_value_config(org_id, config_id):
    client = securitycenter_v1.SecurityCenterClient()
    name = f"organizations/{org_id}/resourceValueConfigs/{config_id}"
    
    client.delete_resource_value_config(
        request={"name": name}
    )
    
    return True
```

## Code Snippets

### Complete Module Example

```python
# Complete custom module example
from google.cloud import securitycenter_v1

def create_complete_module(org_id):
    client = securitycenter_v1.SecurityCenterClient()
    parent = f"organizations/{org_id}"
    
    module = securitycenter_v1.SecurityHealthAnalyticsCustomModule(
        display_name="Public Bucket Detector",
        description="Detects publicly accessible Cloud Storage buckets",
        enablement_state="ENABLED",
        module_config={
            "custom_output": {
                "name": "resource_name",
                "expression": "resource.name"
            },
            "resource_selector": {
                "resource_types": ["google.cloud.storage.Bucket"]
            },
            "pattern": {
                "expr": {
                    "expression": "resource.iamConfiguration.uniformBucketLevelAccess.enabled == false",
                    "location": "RESOURCE"
                }
            },
            "severity": "HIGH"
        }
    )
    
    response = client.create_security_health_analytics_custom_module(
        request={
            "parent": parent,
            "security_health_analytics_custom_module": module
        }
    )
    
    return response
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Module not creating | Invalid config | Check: module_config schema |
| Module not triggering | Pattern not matching | Verify: resource_selector and pattern |
| Permission denied | Missing IAM role | Add: roles/securitycenter.admin |
| API error | API not enabled | Enable: `gcloud services enable securitycenter.googleapis.com` |

### Verify Module Status

```python
# Verify custom module is enabled
def verify_module_status(org_id, module_id):
    from google.cloud import securitycenter_v1
    
    client = securitycenter_v1.SecurityCenterClient()
    name = f"organizations/{org_id}/securityHealthAnalyticsCustomModules/{module_id}"
    
    module = client.get_security_health_analytics_custom_module(
        request={"name": name}
    )
    
    return {
        "state": module.enablement_state,
        "display_name": module.display_name
    }
```

## Best Practices

1. **Module Design**: Design modules with clear, specific detection patterns
2. **Testing**: Test modules in a sandbox organization before production
3. **Documentation**: Document module purpose and expected findings
4. **Monitoring**: Monitor module performance and finding accuracy
5. **Versioning**: Version modules for rollback capability
6. **Cleanup**: Regularly review and remove unused modules

## See Also

- [SCC Custom Modules](https://cloud.google.com/security-command-center/docs/concepts-custom-modules)
- [SCC API Reference](https://cloud.google.com/security-command-center/docs/reference/rest)
