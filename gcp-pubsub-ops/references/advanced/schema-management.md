# Schema Management — Google Cloud Pub/Sub

> Provides messaging administrators with a complete guide to Cloud Pub/Sub schema management — schema CRUD operations, Avro/Protocol Buffer examples, revision history, and compatibility checking.

## Table of Contents

1. [Overview](#overview)
2. [Schema Types](#schema-types)
3. [Schema CRUD Operations](#schema-crud-operations)
4. [Attaching Schema to Topic](#attaching-schema-to-topic)
5. [Schema Revision History](#schema-revision-history)
6. [Compatibility Checking](#compatibility-checking)
7. [Avro Schema Examples](#avro-schema-examples)
8. [Protocol Buffer Examples](#protocol-buffer-examples)
9. [Troubleshooting](#troubleshooting)
10. [See Also](#see-also)

## Overview

Pub/Sub schemas define the structure of messages published to topics. Schemas support **Avro** and **Protocol Buffer** (Protobuf) formats. Using schemas enables:

- **Message validation** — Pub/Sub validates messages against the schema before accepting
- **Schema evolution** — Schemas can be updated with backward/forward compatibility
- **Code generation** — Generate publisher/subscriber code from schema definitions
- **Documentation** — Self-documenting message formats

### Schema Capabilities

| Capability | Description |
|------------|-------------|
| Create Schema | Define new schema with Avro or Protobuf |
| Describe Schema | View schema definition and metadata |
| List Schemas | List all schemas in project |
| Delete Schema | Remove schema (no attached topics) |
| Update Schema | Create new revision with compatible changes |
| Compatibility Check | Verify schema changes are backward/forward compatible |
| Topic Attachment | Attach schema to topic for validation |

## Schema Types

### Avro

Avro schemas use JSON format and support:
- Primitive types: null, boolean, int, long, float, double, bytes, string
- Complex types: record, enum, array, map, union, fixed
- Named types: record, enum, fixed

### Protocol Buffer

Protobuf schemas use `.proto` format and support:
- Scalar types: double, float, int32, int64, uint32, uint64, sint32, sint64, fixed32, fixed64, sfixed32, sfixed64, bool, string, bytes
- Complex types: message, enum, oneof, map, repeated
- Packages and imports

## Schema CRUD Operations

### Create Schema

**CLI**:
```bash
gcloud pubsub schemas create "{{user.schema_id}}" \
  --type=AVRO \
  --definition='{"type": "record", "name": "Test", "fields": [{"name": "message", "type": "string"}]}' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**CLI (from file)**:
```bash
gcloud pubsub schemas create "{{user.schema_id}}" \
  --type=AVRO \
  --definition-file=./schema.avsc \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Validate**: `gcloud pubsub schemas describe "{{user.schema_id}}" --format="json" | jq '{name, type, definition}'`

### Describe Schema

**CLI**:
```bash
gcloud pubsub schemas describe "{{user.schema_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Extract fields**:
```bash
jq '{name, type, definition, revisionId, createTime}'
```

### List Schemas

**CLI**:
```bash
gcloud pubsub schemas list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(name,type,revisionId)"
```

**JSON output**:
```bash
gcloud pubsub schemas list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | \
  jq '.[] | {name, type, revisionId}'
```

### Delete Schema

**Pre-flight (Safety Gate)**:
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| No attached topics | `gcloud pubsub topics list --filter="schema:{{user.schema_id}}"` | Empty | HALT — detach schema first |

**CLI**:
```bash
gcloud pubsub schemas delete "{{user.schema_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet
```

**Validate**: `gcloud pubsub schemas describe "{{user.schema_id}}" --quiet 2>&1 || echo "✅ Schema deleted"`

## Attaching Schema to Topic

### Create Topic with Schema

**CLI**:
```bash
gcloud pubsub topics create "{{user.topic_id}}" \
  --schema="{{user.schema_id}}" \
  --message-transport-body-field=message \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Validate**: `gcloud pubsub topics describe "{{user.topic_id}}" --format="json" | jq '.schemaSettings'`

### Update Topic Schema

**Pre-flight**: Topic exists and has existing schema.

**CLI**:
```bash
gcloud pubsub topics update "{{user.topic_id}}" \
  --schema="{{user.schema_id}}" \
  --message-transport-body-field=message \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Detach Schema from Topic

**CLI**:
```bash
gcloud pubsub topics update "{{user.topic_id}}" \
  --clear-schema \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Validate**: `gcloud pubsub topics describe "{{user.topic_id}}" --format="json" | jq '.schemaSettings == null'`

## Schema Revision History

### View Schema Revisions

**CLI**:
```bash
gcloud pubsub schemas describe "{{user.schema_id}}" \
  --schema-view=FULL \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Create Schema Revision

**Pre-flight**: Schema exists. New definition must be compatible with previous revision.

**CLI**:
```bash
gcloud pubsub schemas create "{{user.schema_id}}" \
  --type=AVRO \
  --definition='{"type": "record", "name": "Test", "fields": [{"name": "message", "type": "string"}, {"name": "timestamp", "type": "long"}]}' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Validate**: `gcloud pubsub schemas describe "{{user.schema_id}}" --schema-view=FULL --format="json" | jq '.revisionCreateTime'`

## Compatibility Checking

### Check Compatibility Before Update

**CLI**:
```bash
gcloud pubsub schemas test-compatibility "{{user.schema_id}}" \
  --type=AVRO \
  --definition='{"type": "record", "name": "Test", "fields": [{"name": "message", "type": "string"}, {"name": "new_field", "type": "string"}]}' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Expected output**: `{"compatibility":"COMPATIBLE"}` or `{"compatibility":"INCOMPATIBLE","errors":[...]}`

### Compatibility Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `COMPATIBILITY_UNSPECIFIED` | No compatibility check | Initial schema |
| `COMPATIBILITY_BACKWARD` | New schema can read old data | Adding optional fields |
| `COMPATIBILITY_BACKWARD_TRANSITIVE` | New schema can read any old data | Adding fields anywhere |
| `COMPATIBILITY_FORWARD` | Old schema can read new data | Removing fields |
| `COMPATIBILITY_FORWARD_TRANSITIVE` | Any old schema can read new data | Removing fields anywhere |
| `COMPATIBILITY_FULL` | Backward + Forward | Bidirectional |
| `COMPATIBILITY_FULL_TRANSITIVE` | Bidirectional transitive | Full compatibility |

### Set Schema Compatibility Mode

**CLI**:
```bash
gcloud pubsub schemas update "{{user.schema_id}}" \
  --compatibility=BACKWARD \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

## Avro Schema Examples

### Simple Record

```json
{
  "type": "record",
  "name": "UserEvent",
  "namespace": "com.example",
  "fields": [
    {"name": "user_id", "type": "string"},
    {"name": "action", "type": "string"},
    {"name": "timestamp", "type": "long"}
  ]
}
```

### Record with Nested Type

```json
{
  "type": "record",
  "name": "OrderEvent",
  "namespace": "com.example",
  "fields": [
    {"name": "order_id", "type": "string"},
    {"name": "customer", "type": {"type": "record", "name": "Customer", "fields": [
      {"name": "customer_id", "type": "string"},
      {"name": "name", "type": "string"}
    ]}},
    {"name": "items", "type": {"type": "array", "items": {"type": "record", "name": "Item", "fields": [
      {"name": "sku", "type": "string"},
      {"name": "quantity", "type": "int"}
    ]}}},
    {"name": "total", "type": "double"}
  ]
}
```

### Record with Enum

```json
{
  "type": "record",
  "name": "PaymentEvent",
  "namespace": "com.example",
  "fields": [
    {"name": "payment_id", "type": "string"},
    {"name": "status", "type": {"type": "enum", "name": "PaymentStatus", "symbols": ["PENDING", "COMPLETED", "FAILED"]}},
    {"name": "amount", "type": "double"}
  ]
}
```

### Record with Map

```json
{
  "type": "record",
  "name": "ConfigEvent",
  "namespace": "com.example",
  "fields": [
    {"name": "config_id", "type": "string"},
    {"name": "settings", "type": {"type": "map", "values": "string"}}
  ]
}
```

## Protocol Buffer Examples

### Simple Message

```protobuf
syntax = "proto3";

package com.example;

message UserEvent {
  string user_id = 1;
  string action = 2;
  int64 timestamp = 3;
}
```

### Message with Nested Types

```protobuf
syntax = "proto3";

package com.example;

message OrderEvent {
  string order_id = 1;
  Customer customer = 2;
  repeated Item items = 3;
  double total = 4;

  message Customer {
    string customer_id = 1;
    string name = 2;
  }

  message Item {
    string sku = 1;
    int32 quantity = 2;
  }
}
```

### Message with Enum

```protobuf
syntax = "proto3";

package com.example;

message PaymentEvent {
  string payment_id = 1;
  PaymentStatus status = 2;
  double amount = 3;

  enum PaymentStatus {
    PENDING = 0;
    COMPLETED = 1;
    FAILED = 2;
  }
}
```

### Message with Map

```protobuf
syntax = "proto3";

package com.example;

message ConfigEvent {
  string config_id = 1;
  map<string, string> settings = 2;
}
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Schema validation failed | Message doesn't match schema | Fix message format or update schema |
| Incompatible schema revision | Breaking change to schema | Ensure backward/forward compatibility |
| Schema not found | Wrong schema ID or project | Verify schema exists with `gcloud pubsub schemas list` |
| Topic schema mismatch | Topic expects different schema | Detach and reattach correct schema |
| Cannot delete schema | Schema has attached topics | Detach schema from all topics first |

### Debug Commands

```bash
# List all schemas
gcloud pubsub schemas list --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Describe schema details
gcloud pubsub schemas describe "{{user.schema_id}}" --schema-view=FULL --format="json"

# Check topic schema settings
gcloud pubsub topics describe "{{user.topic_id}}" --format="json" | jq '.schemaSettings'

# Find topics using a schema
gcloud pubsub topics list --filter="schema={{user.schema_id}}" --format="table(name,schema)"

# Test compatibility
gcloud pubsub schemas test-compatibility "{{user.schema_id}}" --type=AVRO --definition='<new_def>'
```

## See Also

- [Pub/Sub Core Concepts](../core-concepts.md)
- [Pub/Sub Monitoring](../monitoring.md)
- [Pub/Sub Troubleshooting](../troubleshooting.md)
- [Google Cloud Pub/Sub Schema Documentation](https://cloud.google.com/pubsub/docs/schema)
