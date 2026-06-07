# API & SDK — GKE

## REST API
- Discovery doc: https://container.googleapis.com/$discovery/rest?version=v1
- Base URL: https://container.googleapis.com/v1/

## Operations Map

| Goal | REST Method | Go SDK Method |
|------|------------|---------------|
| Create cluster | POST /v1/projects/{p}/zones/{z}/clusters | ClusterManagerClient.CreateCluster() |
| Get cluster | GET /v1/projects/{p}/zones/{z}/clusters/{c} | ClusterManagerClient.GetCluster() |
| List clusters | GET /v1/projects/{p}/zones/{z}/clusters | ClusterManagerClient.ListClusters() |
| Update cluster | PUT /v1/projects/{p}/zones/{z}/clusters/{c} | ClusterManagerClient.UpdateCluster() |
| Delete cluster | DELETE /v1/projects/{p}/zones/{z}/clusters/{c} | ClusterManagerClient.DeleteCluster() |
| Create node pool | POST /v1/projects/{p}/zones/{z}/clusters/{c}/nodePools | ClusterManagerClient.CreateNodePool() |
| Get node pool | GET /v1/projects/{p}/zones/{z}/clusters/{c}/nodePools/{np} | ClusterManagerClient.GetNodePool() |
| List node pools | GET /v1/projects/{p}/zones/{z}/clusters/{c}/nodePools | ClusterManagerClient.ListNodePools() |
| Resize node pool | POST /v1/projects/{p}/zones/{z}/clusters/{c}/nodePools/{np}:setSize | ClusterManagerClient.SetNodePoolSize() |
| Upgrade node pool | POST /v1/projects/{p}/zones/{z}/clusters/{c}/nodePools/{np}:upgrade | ClusterManagerClient.SetNodePoolManagement() |
| Delete node pool | DELETE /v1/projects/{p}/zones/{z}/clusters/{c}/nodePools/{np} | ClusterManagerClient.DeleteNodePool() |
| Get operation | GET /v1/projects/{p}/zones/{z}/operations/{op} | ClusterManagerClient.GetOperation() |

## Python SDK Code Snippets

### Create Standard Cluster

```python
# create_cluster.py (generated dynamically in /tmp/gcp-sdk-workspace)
# REST: POST /v1/projects/{project}/zones/{zone}/clusters
import os
from google.cloud import container_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
location = os.environ.get("CLOUDSDK_CONTAINER_CLUSTER", os.environ.get("CLOUDSDK_COMPUTE_ZONE", "us-central1"))
cluster_name = os.environ.get("GKE_CLUSTER_NAME", "my-cluster")

client = container_v1.ClusterManagerClient()

cluster = container_v1.Cluster()
cluster.name = cluster_name
cluster.initial_node_count = 3

node_config = container_v1.NodeConfig()
node_config.machine_type = "e2-medium"
node_config.disk_size_gb = 100
node_config.disk_type = "pd-balanced"
cluster.node_config = node_config

release_channel = container_v1.ReleaseChannel()
release_channel.channel = container_v1.ReleaseChannel.Channel.REGULAR
cluster.release_channel = release_channel

ip_allocation = container_v1.IPAllocationPolicy()
ip_allocation.use_ip_aliases = True
cluster.ip_allocation_policy = ip_allocation

workload_identity = container_v1.WorkloadIdentityConfig()
workload_identity.workload_pool = f"{project}.svc.id.goog"
cluster.workload_identity_config = workload_identity

request = container_v1.CreateClusterRequest()
request.project_id = project
request.zone = location
request.cluster = cluster

operation = client.create_cluster(request=request)
operation.result(timeout=600)
print(f"Created cluster: {cluster_name}")
```

Execute:
```bash
pip install --quiet --user google-cloud-container
python3 create_cluster.py
```

### Describe Cluster

```python
# describe_cluster.py
import os
from google.cloud import container_v1
client = container_v1.ClusterManagerClient()
cluster = client.get_cluster(
    project_id=os.environ["CLOUDSDK_CORE_PROJECT"],
    zone=os.environ.get("CLOUDSDK_CONTAINER_CLUSTER", "us-central1"),
    cluster_id="{{user.cluster_name}}")
print(f"Name: {cluster.name}, Status: {cluster.status}, Endpoint: {cluster.endpoint}")
```

### Delete Cluster

```python
# delete_cluster.py
import os
from google.cloud import container_v1
client = container_v1.ClusterManagerClient()
operation = client.delete_cluster(
    project_id=os.environ["CLOUDSDK_CORE_PROJECT"],
    zone=os.environ.get("CLOUDSDK_CONTAINER_CLUSTER", "us-central1"),
    cluster_id="{{user.cluster_name}}")
operation.result(timeout=600)
print(f"Deleted cluster: {{user.cluster_name}}")
```

### Create Node Pool

```python
# create_node_pool.py
import os
from google.cloud import container_v1
client = container_v1.ClusterManagerClient()
pool = container_v1.NodePool()
pool.name = "{{user.node_pool_name}}"
pool.initial_node_count = 3
pool.config = container_v1.NodeConfig()
pool.config.machine_type = "e2-medium"
pool.config.disk_size_gb = 100
pool.config.disk_type = "pd-balanced"
autoscaling = container_v1.NodePoolAutoscaling()
autoscaling.enabled = True
autoscaling.min_node_count = 1
autoscaling.max_node_count = 10
pool.autoscaling = autoscaling
request = container_v1.CreateNodePoolRequest(
    project_id=os.environ["CLOUDSDK_CORE_PROJECT"],
    zone=os.environ.get("CLOUDSDK_CONTAINER_CLUSTER", "us-central1"),
    cluster_id="{{user.cluster_name}}",
    node_pool=pool)
operation = client.create_node_pool(request=request)
operation.result(timeout=600)
print(f"Created node pool: {{user.node_pool_name}}")
```

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create cluster | $.name | Operation name |
| Describe cluster | $.{name,status,endpoint,location,currentMasterVersion,nodePools[]} | Cluster details |
| List clusters | $.clusters[].{name,status,location,currentMasterVersion} | Cluster list |
| Create node pool | $.name | Operation name |
| Describe node pool | $.{name,status,config.machineType,initialNodeCount,currentNodeCount} | Node pool details |
| Get operation | $.{status,detail,error} | Operation status |
| Get credentials | $.masterAuth.{clusterCaCertificate} | CA cert for kubectl |
| Server config | $.channels[].{channel,validVersions[],defaultVersion} | Version/channel info |