# API & SDK — Cloud Logging

## REST API
- Discovery doc: https://logging.googleapis.com/$discovery/rest?version=v2
- Base URL: https://logging.googleapis.com/v2/

## Operations Map

| Goal | REST Method | Go SDK Method |
|------|------------|---------------|
| List log entries | POST entries.list | LoggingServiceV2Client.ListLogEntries |
| Create log bucket | POST parent/buckets | ConfigClientV2.CreateBucket |
| Get log bucket | GET parent/buckets/{b} | ConfigClientV2.GetBucket |
| Update log bucket | PATCH parent/buckets/{b} | ConfigClientV2.UpdateBucket |
| Delete log bucket | DELETE parent/buckets/{b} | ConfigClientV2.DeleteBucket |
| Create log view | POST parent/buckets/{b}/views | ConfigClientV2.CreateView |
| Delete log view | DELETE parent/buckets/{b}/views/{v} | ConfigClientV2.DeleteView |
| Create sink | POST projects/{p}/sinks | ConfigClientV2.CreateSink |
| Get sink | GET projects/{p}/sinks/{s} | ConfigClientV2.GetSink |
| Update sink | PUT projects/{p}/sinks/{s} | ConfigClientV2.UpdateSink |
| Delete sink | DELETE projects/{p}/sinks/{s} | ConfigClientV2.DeleteSink |
| Create metric | POST projects/{p}/metrics | MetricsServiceV2Client.CreateLogMetric |
| Get metric | GET projects/{p}/metrics/{m} | MetricsServiceV2Client.GetLogMetric |
| Delete metric | DELETE projects/{p}/metrics/{m} | MetricsServiceV2Client.DeleteLogMetric |
| Create exclusion | POST projects/{p}/exclusions | ConfigClientV2.CreateExclusion |

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| List log entries | $.entries[].{logName,timestamp,severity,resource} | Log entry list |
| Create sink | $.{name,destination,writerIdentity} | Sink details |
| Describe sink | $.{name,destination,filter,writerIdentity} | Sink configuration |
| Create bucket | $.{name,retentionDays,lifecycleState} | Bucket details |
| Describe bucket | $.{name,retentionDays,lifecycleState,locked} | Bucket config |
| Create metric | $.{name,filter,description} | Metric details |
| Describe metric | $.{name,filter,description,metricDescriptor} | Metric config |