# API & SDK — Memorystore for Redis

## REST API
- Discovery doc: https://redis.googleapis.com/$discovery/rest?version=v1
- Base URL: https://redis.googleapis.com/v1/

## Operations Map

| Goal | REST Method | Go SDK Method |
|------|------------|---------------|
| Create instance | POST projects/{p}/locations/{l}/instances | CloudRedisClient.CreateInstance |
| Get instance | GET projects/{p}/locations/{l}/instances/{i} | CloudRedisClient.GetInstance |
| List instances | GET projects/{p}/locations/{l}/instances | CloudRedisClient.ListInstances |
| Update instance | PATCH projects/{p}/locations/{l}/instances/{i} | CloudRedisClient.UpdateInstance |
| Delete instance | DELETE projects/{p}/locations/{l}/instances/{i} | CloudRedisClient.DeleteInstance |
| Export instance | POST {name}:export | CloudRedisClient.ExportInstance |
| Import instance | POST {name}:import | CloudRedisClient.ImportInstance |
| Failover | POST {name}:failover | CloudRedisClient.FailoverInstance |
| Upgrade Redis | POST {name}:upgrade | CloudRedisClient.UpgradeInstance |

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create instance | $.{name,host,port,state} | Instance details |
| Describe instance | $.{name,host,port,state,memorySizeGb,tier,redisVersion} | Full config |
| List instances | $.instances[].{name,host,state,memorySizeGb,tier} | Instance list |
| Update instance | $.{name,state,memorySizeGb} | Updated details |
| Export/Import | $.{name,state} | Operation details |